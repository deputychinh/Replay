import json

from aws_cdk import Duration, Stack
from aws_cdk import aws_applicationautoscaling as appscaling
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from relay_infra.config import StageConfig, resource_name, ssm_name
from relay_infra.data_stack import DataStack

API_PORT = 8000
ORIGIN_HEADER = "X-Origin-Verify"


class ServicesStack(Stack):
    """ECS Fargate: the API behind an ALB (with WebSockets) and the SQS worker. One image, two commands."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        config: StageConfig,
        vpc: ec2.IVpc,
        data: DataStack,
        image_tag: str,
        app_url: str,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, id, **kwargs)
        self.repository = ecr.Repository(
            self,
            "Repository",
            repository_name=resource_name(config.name, "backend"),
            image_scan_on_push=True,
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=30)],
        )
        image = ecs.ContainerImage.from_ecr_repository(self.repository, image_tag)
        cluster = ecs.Cluster(self, "Cluster", vpc=vpc, container_insights_v2=ecs.ContainerInsights.ENABLED)
        app_subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)

        # Tasks get their own group; only it may reach Postgres and Redis.
        tasks_sg = ec2.SecurityGroup(self, "TasksSg", vpc=vpc, description="Relay API and worker tasks")
        # The rules live in this stack (not in DataStack) so the dependency only goes Services → Data.
        for rule_id, target, port in [("DbFromTasks", data.db_sg, 5432), ("RedisFromTasks", data.redis_sg, 6379)]:
            ec2.CfnSecurityGroupIngress(
                self,
                rule_id,
                group_id=target.security_group_id,
                ip_protocol="tcp",
                from_port=port,
                to_port=port,
                source_security_group_id=tasks_sg.security_group_id,
            )

        db_secret = data.database.secret
        assert db_secret is not None
        environment = {
            "RELAY_ENV": config.name,
            "RELAY_DB_HOST": data.database.db_instance_endpoint_address,
            "RELAY_DB_PORT": data.database.db_instance_endpoint_port,
            "RELAY_REDIS_URL": f"redis://{data.redis.attr_primary_end_point_address}:{data.redis.attr_primary_end_point_port}/0",
            "RELAY_QUEUE_URL": data.queue.queue_url,
            "RELAY_FILES_BUCKET": data.files.bucket_name,
            "RELAY_AWS_REGION": self.region,
            "RELAY_AWS_ENDPOINT_URL": "",
            "RELAY_AWS_PUBLIC_ENDPOINT_URL": "",
            "RELAY_EMAIL_BACKEND": "ses",
            "RELAY_APP_URL": app_url,
            "RELAY_CORS_ORIGINS": json.dumps([app_url]),
        }
        secrets = {
            "RELAY_DB_PASSWORD": ecs.Secret.from_secrets_manager(db_secret, "password"),
            "RELAY_DB_USER": ecs.Secret.from_secrets_manager(db_secret, "username"),
            "RELAY_JWT_SECRET": ecs.Secret.from_secrets_manager(data.jwt_secret),
        }

        def task(name: str) -> ecs.FargateTaskDefinition:
            definition = ecs.FargateTaskDefinition(
                self,
                f"{name}Task",
                cpu=config.task_cpu,
                memory_limit_mib=config.task_memory,
                runtime_platform=ecs.RuntimePlatform(cpu_architecture=ecs.CpuArchitecture.X86_64),
            )
            data.queue.grant_send_messages(definition.task_role)
            data.files.grant_read_write(definition.task_role)
            definition.task_role.add_to_principal_policy(
                iam.PolicyStatement(actions=["ses:SendEmail", "ses:SendRawEmail"], resources=["*"])
            )
            return definition

        def container(
            definition: ecs.FargateTaskDefinition, name: str, command: list[str], essential: bool = True
        ) -> ecs.ContainerDefinition:
            return definition.add_container(
                name,
                image=image,
                command=command,
                environment=environment,
                secrets=secrets,
                essential=essential,
                logging=ecs.LogDrivers.aws_logs(stream_prefix=name, log_retention=logs.RetentionDays.ONE_MONTH),
            )

        # API: a short-lived init container runs migrations (advisory-locked in alembic/env.py) before the API starts.
        api_task = task("Api")
        migrate = container(api_task, "migrate", ["alembic", "upgrade", "head"], essential=False)
        api = container(
            api_task,
            "api",
            ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(API_PORT), "--proxy-headers"],
        )
        api.add_port_mappings(ecs.PortMapping(container_port=API_PORT))
        api.add_container_dependencies(
            ecs.ContainerDependency(container=migrate, condition=ecs.ContainerDependencyCondition.SUCCESS)
        )

        self.api_service = ecs.FargateService(
            self,
            "ApiService",
            cluster=cluster,
            task_definition=api_task,
            desired_count=config.api_min,
            vpc_subnets=app_subnets,
            security_groups=[tasks_sg],
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            min_healthy_percent=100,
            max_healthy_percent=200,
        )
        self.alb = elbv2.ApplicationLoadBalancer(
            self, "Alb", vpc=vpc, internet_facing=True, idle_timeout=Duration.seconds(300)
        )
        listener = self.alb.add_listener(
            "Http",
            port=80,
            open=True,
            default_action=elbv2.ListenerAction.fixed_response(403, message_body="Forbidden"),
        )
        self.target_group = listener.add_targets(
            "Api",
            port=API_PORT,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[self.api_service],
            priority=1,
            conditions=[
                elbv2.ListenerCondition.http_header(ORIGIN_HEADER, [data.origin_secret.secret_value.unsafe_unwrap()])
            ],
            health_check=elbv2.HealthCheck(path="/ready", healthy_http_codes="200", interval=Duration.seconds(15)),
            deregistration_delay=Duration.seconds(30),
        )
        api_scaling = self.api_service.auto_scale_task_count(min_capacity=config.api_min, max_capacity=config.api_max)
        api_scaling.scale_on_cpu_utilization("Cpu", target_utilization_percent=60)
        api_scaling.scale_on_request_count("Requests", requests_per_target=600, target_group=self.target_group)

        # Worker: scales on the number of waiting jobs.
        worker_task = task("Worker")
        data.queue.grant_consume_messages(worker_task.task_role)
        container(worker_task, "worker", ["python", "-m", "app.worker"])
        self.worker_service = ecs.FargateService(
            self,
            "WorkerService",
            cluster=cluster,
            task_definition=worker_task,
            desired_count=config.worker_min,
            vpc_subnets=app_subnets,
            security_groups=[tasks_sg],
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            min_healthy_percent=100,
        )
        worker_scaling = self.worker_service.auto_scale_task_count(
            min_capacity=config.worker_min, max_capacity=config.worker_max
        )
        worker_scaling.scale_on_metric(
            "QueueDepth",
            metric=data.queue.metric_approximate_number_of_messages_visible(period=Duration.minutes(1)),
            scaling_steps=[
                appscaling.ScalingInterval(upper=10, change=0),
                appscaling.ScalingInterval(lower=100, change=+1),
                appscaling.ScalingInterval(lower=1000, change=+2),
            ],
            adjustment_type=appscaling.AdjustmentType.CHANGE_IN_CAPACITY,
        )

        ssm.StringParameter(
            self,
            "EcrRepoParam",
            parameter_name=ssm_name(config.name, "ecr-repo"),
            string_value=self.repository.repository_uri,
        )

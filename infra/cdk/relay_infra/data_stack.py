from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticache as elasticache
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_rds as rds
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_secretsmanager as secrets
from aws_cdk import aws_sqs as sqs
from constructs import Construct

from relay_infra.config import StageConfig, resource_name

QUEUE_VISIBILITY = Duration.seconds(60)  # longer than the slowest job (CSV export)
MAX_RECEIVES = 5  # then the job moves to the dead-letter queue (alarm)


def scheduled_job(job_type: str) -> events.RuleTargetInput:
    """Same shape as backend/app/jobs/queue.py → job_body(). The key carries the schedule time,
    so a duplicate delivery of the same tick is skipped by the worker's idempotency check."""
    return events.RuleTargetInput.from_object(
        {"type": job_type, "payload": {}, "key": f"{job_type}:{events.EventField.time}"}
    )


class DataStack(Stack):
    """Postgres, Redis, the job queue, the files bucket and the app secrets. Nothing here is public."""

    def __init__(self, scope: Construct, id: str, *, config: StageConfig, vpc: ec2.IVpc, **kwargs: object) -> None:
        super().__init__(scope, id, **kwargs)
        removal = RemovalPolicy.RETAIN if config.removal_protection else RemovalPolicy.DESTROY
        data_subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)

        # No ingress here: ServicesStack opens these ports to its own task security group,
        # so the dependency only goes Services → Data.
        self.db_sg = db_sg = ec2.SecurityGroup(self, "DbSg", vpc=vpc, allow_all_outbound=False)
        self.redis_sg = redis_sg = ec2.SecurityGroup(self, "RedisSg", vpc=vpc, allow_all_outbound=False)

        self.database = rds.DatabaseInstance(
            self,
            "Postgres",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_16),
            instance_type=ec2.InstanceType(config.db_instance),
            vpc=vpc,
            vpc_subnets=data_subnets,
            security_groups=[db_sg],
            credentials=rds.Credentials.from_generated_secret("relay"),
            database_name="relay",
            multi_az=config.db_multi_az,
            storage_encrypted=True,
            allocated_storage=20,
            max_allocated_storage=200,
            backup_retention=Duration.days(config.db_backup_days),
            deletion_protection=config.removal_protection,
            removal_policy=removal,
            publicly_accessible=False,
            enable_performance_insights=True,
        )

        subnet_group = elasticache.CfnSubnetGroup(
            self,
            "RedisSubnets",
            description="Relay Redis",
            subnet_ids=vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED).subnet_ids,
        )
        self.redis = elasticache.CfnReplicationGroup(
            self,
            "Redis",
            replication_group_description="Relay cache, rate limits and real-time pub/sub",
            engine="redis",
            engine_version="7.1",
            cache_node_type=config.redis_node,
            num_cache_clusters=2 if config.db_multi_az else 1,
            automatic_failover_enabled=config.db_multi_az,
            cache_subnet_group_name=subnet_group.ref,
            security_group_ids=[redis_sg.security_group_id],
            at_rest_encryption_enabled=True,
        )

        self.dead_letters = sqs.Queue(
            self,
            "JobsDlq",
            queue_name=resource_name(config.name, "jobs-dlq"),
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
        )
        self.queue = sqs.Queue(
            self,
            "Jobs",
            queue_name=resource_name(config.name, "jobs"),
            visibility_timeout=QUEUE_VISIBILITY,
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            dead_letter_queue=sqs.DeadLetterQueue(queue=self.dead_letters, max_receive_count=MAX_RECEIVES),
        )

        # Schedules (the worker's local `--schedule` loop, done by EventBridge in AWS).
        for rule_id, schedule, job_type in [
            ("SlaScan", events.Schedule.rate(Duration.minutes(1)), "sla_scan"),
            ("AutoClose", events.Schedule.rate(Duration.hours(1)), "auto_close"),
        ]:
            events.Rule(
                self,
                rule_id,
                schedule=schedule,
                targets=[targets.SqsQueue(self.queue, message=scheduled_job(job_type))],
            )

        self.files = s3.Bucket(
            self,
            "Files",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=config.removal_protection,
            removal_policy=removal,
            auto_delete_objects=not config.removal_protection,
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    max_age=3000,
                )
            ],
            lifecycle_rules=[s3.LifecycleRule(prefix="exports/", expiration=Duration.days(7))],
        )

        # CloudFront sends this header to the ALB; the ALB refuses requests without it,
        # so the API cannot be reached by going around CloudFront (and its WAF / headers).
        self.origin_secret = secrets.Secret(
            self,
            "OriginVerify",
            description="Shared header value between CloudFront and the ALB",
            generate_secret_string=secrets.SecretStringGenerator(password_length=32, exclude_punctuation=True),
        )

        self.jwt_secret = secrets.Secret(
            self,
            "JwtSecret",
            description="Relay access-token signing key",
            generate_secret_string=secrets.SecretStringGenerator(password_length=48, exclude_punctuation=True),
        )

from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

from relay_infra.config import StageConfig


class NetworkStack(Stack):
    """VPC over two AZs: public (ALB, NAT), private app subnets (ECS), isolated data subnets (RDS, Redis)."""

    def __init__(self, scope: Construct, id: str, *, config: StageConfig, **kwargs: object) -> None:
        super().__init__(scope, id, **kwargs)
        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=config.nat_gateways,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
                ec2.SubnetConfiguration(name="app", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=22),
                ec2.SubnetConfiguration(name="data", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24),
            ],
        )
        # S3 traffic stays on the AWS network (cheaper than NAT, never public).
        self.vpc.add_gateway_endpoint("S3", service=ec2.GatewayVpcEndpointAwsService.S3)

from aws_cdk import Duration, Stack
from aws_cdk import aws_iam as iam
from constructs import Construct

from relay_infra.config import StageConfig


class CiStack(Stack):
    """GitHub Actions deploys with short-lived OIDC credentials: no AWS keys stored in GitHub."""

    def __init__(self, scope: Construct, id: str, *, config: StageConfig, github_repo: str, **kwargs: object) -> None:
        super().__init__(scope, id, **kwargs)
        provider = iam.OpenIdConnectProvider(
            self, "GitHub", url="https://token.actions.githubusercontent.com", client_ids=["sts.amazonaws.com"]
        )
        # main deploys staging; tags (and the protected `production` environment) deploy prod.
        subject = (
            f"repo:{github_repo}:ref:refs/heads/main"
            if config.name == "staging"
            else f"repo:{github_repo}:environment:production"
        )
        self.role = iam.Role(
            self,
            "DeployRole",
            role_name=f"relay-deploy-{config.name}",
            max_session_duration=Duration.hours(1),
            assumed_by=iam.WebIdentityPrincipal(
                provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                        "token.actions.githubusercontent.com:sub": subject,
                    },
                },
            ),
        )
        # CDK deploys through its bootstrap roles; the workflow also pushes images and syncs the web bucket.
        self.role.add_to_policy(
            iam.PolicyStatement(actions=["sts:AssumeRole"], resources=[f"arn:aws:iam::{self.account}:role/cdk-*"])
        )
        self.role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:InitiateLayerUpload",
                    "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload",
                    "ecr:PutImage",
                    "ssm:GetParameter",
                    "s3:PutObject",
                    "s3:ListBucket",
                    "s3:DeleteObject",
                    "cloudfront:CreateInvalidation",
                ],
                resources=["*"],
            )
        )

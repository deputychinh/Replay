"""Assertions on the synthesized CloudFormation: the security and reliability rules from docs/plan.md §15."""

import os

import pytest
from aws_cdk import App
from aws_cdk.assertions import Match, Template

from relay_infra.app_builder import build

os.environ.setdefault("JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION", "1")


@pytest.fixture(scope="module", params=["staging", "prod"])
def stacks(request: pytest.FixtureRequest) -> dict[str, Template]:
    app = App(context={"stage": request.param, "imageTag": "test"})
    built = build(app)
    return {name: Template.from_stack(stack) for name, stack in built.items()}  # type: ignore[arg-type]


def test_database_is_private_and_encrypted(stacks: dict[str, Template]) -> None:
    stacks["data"].has_resource_properties(
        "AWS::RDS::DBInstance",
        {
            "PubliclyAccessible": False,
            "StorageEncrypted": True,
            "Engine": "postgres",
        },
    )


def test_buckets_block_public_access(stacks: dict[str, Template]) -> None:
    for name in ("data", "frontend"):
        stacks[name].has_resource_properties(
            "AWS::S3::Bucket",
            {
                "PublicAccessBlockConfiguration": {
                    "BlockPublicAcls": True,
                    "BlockPublicPolicy": True,
                    "IgnorePublicAcls": True,
                    "RestrictPublicBuckets": True,
                },
            },
        )


def test_jobs_queue_has_a_dead_letter_queue(stacks: dict[str, Template]) -> None:
    stacks["data"].has_resource_properties(
        "AWS::SQS::Queue",
        {
            "RedrivePolicy": {"maxReceiveCount": 5, "deadLetterTargetArn": Match.any_value()},
        },
    )


def test_api_health_check_and_origin_lock(stacks: dict[str, Template]) -> None:
    services = stacks["services"]
    services.has_resource_properties("AWS::ElasticLoadBalancingV2::TargetGroup", {"HealthCheckPath": "/ready"})
    services.has_resource_properties(
        "AWS::ElasticLoadBalancingV2::Listener",
        {
            "DefaultActions": [Match.object_like({"Type": "fixed-response"})],
        },
    )
    services.has_resource_properties(
        "AWS::ElasticLoadBalancingV2::ListenerRule",
        {
            "Conditions": Match.array_with([Match.object_like({"Field": "http-header"})]),
        },
    )


def test_migrations_run_before_the_api(stacks: dict[str, Template]) -> None:
    stacks["services"].has_resource_properties(
        "AWS::ECS::TaskDefinition",
        {
            "ContainerDefinitions": Match.array_with(
                [
                    Match.object_like(
                        {"Name": "migrate", "Essential": False, "Command": ["alembic", "upgrade", "head"]}
                    ),
                    Match.object_like(
                        {"Name": "api", "DependsOn": [{"Condition": "SUCCESS", "ContainerName": "migrate"}]}
                    ),
                ]
            ),
        },
    )


def test_schedules_send_jobs_to_the_queue(stacks: dict[str, Template]) -> None:
    stacks["data"].resource_count_is("AWS::Events::Rule", 2)
    stacks["data"].has_resource_properties("AWS::Events::Rule", {"ScheduleExpression": "rate(1 minute)"})


def test_cloudfront_routes_api_and_spa(stacks: dict[str, Template]) -> None:
    stacks["frontend"].has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": Match.object_like(
                {
                    "CacheBehaviors": [Match.object_like({"PathPattern": "/api/*"})],
                    "CustomErrorResponses": Match.array_with(
                        [Match.object_like({"ErrorCode": 404, "ResponsePagePath": "/index.html"})]
                    ),
                }
            ),
        },
    )


def test_alarms_cover_the_failure_modes(stacks: dict[str, Template]) -> None:
    stacks["observability"].resource_count_is("AWS::CloudWatch::Alarm", 6)
    stacks["observability"].resource_count_is("AWS::Budgets::Budget", 1)


def test_deploy_role_trusts_only_this_repository(stacks: dict[str, Template]) -> None:
    stacks["ci"].has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    Match.object_like(
                        {
                            "Condition": {
                                "StringEquals": Match.object_like(
                                    {
                                        "token.actions.githubusercontent.com:sub": Match.string_like_regexp(
                                            "repo:deputychinh/Replay:.*"
                                        )
                                    }
                                )
                            },
                        }
                    )
                ]
            },
        },
    )

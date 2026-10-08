"""Wire the stacks for one stage. Used by app.py and by the tests."""

from aws_cdk import App, Environment, Tags

from relay_infra.ci_stack import CiStack
from relay_infra.config import STAGES
from relay_infra.data_stack import DataStack
from relay_infra.frontend_stack import FrontendStack
from relay_infra.network_stack import NetworkStack
from relay_infra.observability_stack import ObservabilityStack
from relay_infra.services_stack import ServicesStack

REGION = "us-east-1"  # U.S. users and team; CloudFront certificates must live here too


def build(app: App) -> dict[str, object]:
    stage = app.node.try_get_context("stage") or "staging"
    config = STAGES[stage]
    env = Environment(account=app.node.try_get_context("account"), region=REGION)
    image_tag = app.node.try_get_context("imageTag") or "latest"
    app_url = app.node.try_get_context("appUrl") or f"https://{stage}.relay.example.com"
    prefix = f"Relay-{stage}"

    network = NetworkStack(app, f"{prefix}-Network", config=config, env=env)
    data = DataStack(app, f"{prefix}-Data", config=config, vpc=network.vpc, env=env)
    services = ServicesStack(
        app,
        f"{prefix}-Services",
        config=config,
        vpc=network.vpc,
        data=data,
        image_tag=image_tag,
        app_url=app_url,
        env=env,
    )
    frontend = FrontendStack(
        app,
        f"{prefix}-Frontend",
        config=config,
        alb=services.alb,
        origin_secret=data.origin_secret.secret_value.unsafe_unwrap(),
        env=env,
    )
    observability = ObservabilityStack(
        app,
        f"{prefix}-Observability",
        config=config,
        data=data,
        services=services,
        alert_email=app.node.try_get_context("alertEmail"),
        env=env,
    )
    ci = CiStack(
        app,
        f"{prefix}-Ci",
        config=config,
        github_repo=app.node.try_get_context("githubRepo") or "deputychinh/Replay",
        env=env,
    )

    for stack in (network, data, services, frontend, observability, ci):
        Tags.of(stack).add("project", "relay")
        Tags.of(stack).add("stage", stage)
    return {
        "network": network,
        "data": data,
        "services": services,
        "frontend": frontend,
        "observability": observability,
        "ci": ci,
    }

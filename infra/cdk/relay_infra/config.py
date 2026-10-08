"""Everything that differs between staging and production, in one place."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StageConfig:
    name: str
    nat_gateways: int
    db_instance: str
    db_multi_az: bool
    db_backup_days: int
    redis_node: str
    api_min: int
    api_max: int
    worker_min: int
    worker_max: int
    task_cpu: int
    task_memory: int
    monthly_budget_usd: int
    removal_protection: bool


STAGES = {
    "staging": StageConfig(
        "staging",
        nat_gateways=1,
        db_instance="t4g.micro",
        db_multi_az=False,
        db_backup_days=3,
        redis_node="cache.t4g.micro",
        api_min=1,
        api_max=3,
        worker_min=1,
        worker_max=2,
        task_cpu=256,
        task_memory=512,
        monthly_budget_usd=150,
        removal_protection=False,
    ),
    "prod": StageConfig(
        "prod",
        nat_gateways=2,
        db_instance="t4g.medium",
        db_multi_az=True,
        db_backup_days=14,
        redis_node="cache.t4g.small",
        api_min=2,
        api_max=6,
        worker_min=1,
        worker_max=4,
        task_cpu=512,
        task_memory=1024,
        monthly_budget_usd=600,
        removal_protection=True,
    ),
}


# Names shared with backend/app (queue, bucket) and the deploy workflow (SSM parameters).
def resource_name(stage: str, base: str) -> str:
    return f"relay-{base}-{stage}"


def ssm_name(stage: str, key: str) -> str:
    return f"/relay/{stage}/{key}"

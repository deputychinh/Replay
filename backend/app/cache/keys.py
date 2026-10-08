"""Every Redis key is built here — no key strings anywhere else (DS-07)."""

import uuid


def dashboard(org_id: uuid.UUID) -> str:
    return f"relay:dashboard:{org_id}"


def rate_limit(scope: str, identity: str, window_start: int) -> str:
    return f"relay:rl:{scope}:{identity}:{window_start}"


def round_robin_lock(team_id: uuid.UUID) -> str:
    return f"relay:lock:rr:{team_id}"

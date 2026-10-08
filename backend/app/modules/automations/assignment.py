"""Who gets the next ticket (Strategy pattern: swap RoundRobin for LeastLoaded later)."""

import uuid
from typing import Protocol


class AssignmentStrategy(Protocol):
    def pick(self, agents: list[uuid.UUID], last: uuid.UUID | None) -> uuid.UUID | None: ...


class RoundRobin:
    def pick(self, agents: list[uuid.UUID], last: uuid.UUID | None) -> uuid.UUID | None:
        """The agent after `last` in a stable order; the first one if `last` left the team."""
        if not agents:
            return None
        if last not in agents:
            return agents[0]
        return agents[(agents.index(last) + 1) % len(agents)]

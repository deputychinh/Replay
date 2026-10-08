"""One transaction per use case. Side effects (real-time events, queued jobs)
run only after the commit succeeds, so nobody sees data that was rolled back."""

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

AfterCommit = Callable[[], Awaitable[None]]


class UnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._after_commit: list[AfterCommit] = []

    def after_commit(self, action: AfterCommit) -> None:
        self._after_commit.append(action)

    async def commit(self) -> None:
        await self.session.commit()
        actions, self._after_commit = self._after_commit, []
        for action in actions:
            await action()

    async def rollback(self) -> None:
        self._after_commit.clear()
        await self.session.rollback()

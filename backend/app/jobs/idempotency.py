from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.models import ProcessedJob


async def claim(session: AsyncSession, key: str) -> bool:
    """Record the key in the job's own transaction. False means it already ran: skip it."""
    result = await session.execute(insert(ProcessedJob).values(key=key).on_conflict_do_nothing().returning(ProcessedJob.key))
    return result.scalar_one_or_none() is not None


async def was_processed(session: AsyncSession, key: str) -> bool:
    return await session.scalar(select(ProcessedJob.key).where(ProcessedJob.key == key)) is not None

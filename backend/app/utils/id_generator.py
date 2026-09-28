"""
Generates system-assigned, sequential, uniquely-formatted IDs like
'PT-000042' or 'DOC-000007' — instead of letting a human type one in,
which is exactly how you end up with duplicates and inconsistent formats.
"""
from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.id_counter import IdCounter


async def next_sequential_id(db: AsyncSession, counter_name: str, prefix: str, width: int = 6) -> str:
    """
    Atomically increments a named counter and returns a formatted ID.

    Safe under concurrent requests: the UPDATE ... RETURNING below causes
    Postgres to row-lock the counter for the duration of the transaction,
    so two simultaneous calls can never be handed the same number — no
    separate locking logic needed on top of it.

    Does not commit — call this within the same transaction as the row
    you're creating, so the counter only advances if that row actually
    gets saved.
    """
    # Ensure the counter row exists (first call for a given name only).
    insert_stmt = pg_insert(IdCounter).values(name=counter_name, value=0)
    insert_stmt = insert_stmt.on_conflict_do_nothing(index_elements=["name"])
    await db.execute(insert_stmt)

    result = await db.execute(
        update(IdCounter)
        .where(IdCounter.name == counter_name)
        .values(value=IdCounter.value + 1)
        .returning(IdCounter.value)
    )
    new_value = result.scalar_one()
    return f"{prefix}-{new_value:0{width}d}"
"""
Shared logic for creating a staff account, so the two places that can do
it (POST /api/auth/register and POST /api/admin/users — both admin-only)
can't drift out of sync on how staff_id gets assigned.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.models.user import ROLE_ID_PREFIX, User, UserRegister
from app.utils.id_generator import next_sequential_id


class EmailAlreadyExists(Exception):
    pass


async def create_staff_account(db: AsyncSession, payload: UserRegister) -> User:
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise EmailAlreadyExists(payload.email)

    staff_id = await next_sequential_id(
        db,
        counter_name=f"staff_{payload.role.value}",
        prefix=ROLE_ID_PREFIX[payload.role],
    )

    user = User(
        staff_id=staff_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
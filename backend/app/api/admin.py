"""
Admin-only account management.

Deliberately scoped to *account* administration (who can log in, as what
role) rather than exposing raw database access over HTTP — letting an
API endpoint run arbitrary queries against Postgres would be a serious
security hole (SQL injection surface, no query-level audit trail, easy
to accidentally expose patient data). If you genuinely need ad-hoc
database inspection, that's what `docker exec -it medgraph-postgres
psql -U medgraph -d medgraph` is for — a deliberate, logged-in-as-you,
outside-the-app action, not something any authenticated admin session
can trigger by hitting a URL.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_roles
from app.database.postgres import get_db
from app.models.user import User, UserOut, UserRegister, UserRole, UserUpdate
from app.services.user_service import EmailAlreadyExists, create_staff_account

router = APIRouter()


@router.get("/users", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
):
    result = await db.scalars(select(User).order_by(User.role, User.email))
    return result.all()


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
):
    try:
        return await create_staff_account(db, payload)
    except EmailAlreadyExists:
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists")


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
):
    """Deactivate/reactivate an account, or change its role."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    if user.id == admin.id and payload.is_active is False:
        raise HTTPException(400, "You can't deactivate your own account")

    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role is not None:
        user.role = payload.role

    await db.commit()
    await db.refresh(user)
    return user
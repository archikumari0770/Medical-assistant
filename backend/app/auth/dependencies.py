"""
FastAPI dependencies for authentication and role-based access control.

Usage in a route:

    @router.get("/some-doctor-only-thing")
    async def handler(user: User = Depends(require_roles(UserRole.doctor))):
        ...

require_roles returns a dependency that both authenticates (valid JWT ->
active user) and authorizes (user.role is one of the given roles) in one
step, so a route can't accidentally skip the role check after auth.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_access_token
from app.database.postgres import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise _CREDENTIALS_ERROR

    try:
        user_id = uuid.UUID(payload.sub)
    except ValueError:
        raise _CREDENTIALS_ERROR

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR

    return user


def require_roles(*allowed_roles: UserRole):
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' is not permitted to access this resource.",
            )
        return user

    return dependency

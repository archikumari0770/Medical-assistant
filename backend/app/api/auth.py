from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_roles
from app.auth.security import create_access_token, verify_password
from app.database.postgres import get_db
from app.models.user import Token, User, UserOut, UserRegister, UserRole
from app.services.user_service import EmailAlreadyExists, create_staff_account

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=201)
async def register(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
):
    """
    Creates a new staff account (any role, including another admin).
    Only an authenticated admin can call this — there is no public or
    shared-secret registration path. The very first admin account is
    created directly against the database by scripts/seed_users.py,
    which bypasses the API entirely (it's a one-time bootstrap step you
    run yourself, not something reachable over HTTP).
    """
    try:
        return await create_staff_account(db, payload)
    except EmailAlreadyExists:
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists")


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """
    OAuth2-compatible login: expects form fields 'username' (the email)
    and 'password'. Returns a JWT carrying the user's id and role.
    """
    user = await db.scalar(select(User).where(User.email == form_data.username))
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated")

    token = create_access_token(user_id=str(user.id), role=user.role)
    return Token(access_token=token, role=user.role, full_name=user.full_name, staff_id=user.staff_id)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
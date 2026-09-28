"""
User accounts and role definitions.

Three roles, each with a distinct area of the app (enforced in
app/auth/dependencies.py's require_roles, not just hidden in the UI):

  - doctor        full patient chart, symptom analysis, prescribing
  - receptionist  patient registration/demographics only
  - lab           lab result entry/viewing only

There is no public self-registration: new accounts are created via
scripts/seed_users.py or POST /api/auth/register, which requires the
ADMIN_SETUP_KEY shared secret (see app/config.py) precisely so that
role assignment can't be self-served by anyone who finds the API.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.postgres import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    doctor = "doctor"
    receptionist = "receptionist"
    lab = "lab"


# Prefix used when generating a staff_id for each role — see
# app/utils/id_generator.py and app/services/user_service.py.
ROLE_ID_PREFIX = {
    UserRole.admin: "ADM",
    UserRole.doctor: "DOC",
    UserRole.receptionist: "REC",
    UserRole.lab: "LAB",
}


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(256))
    full_name: Mapped[str] = mapped_column(String(256))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ----------------------------------------------------------- Schemas ----

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: UserRole


class UserUpdate(BaseModel):
    is_active: bool | None = None
    role: UserRole | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    staff_id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    full_name: str
    staff_id: str


class TokenPayload(BaseModel):
    sub: str  # user id
    role: UserRole
    exp: int
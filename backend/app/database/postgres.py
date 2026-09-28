"""
PostgreSQL connection layer (async SQLAlchemy).

Stores structured patient records: demographics, encounters, medications,
lab results — anything relational and transactional.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.postgres_dsn,
    echo=settings.app_env == "development",
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models (see app/models/)."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a scoped DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_postgres() -> None:
    """Create tables at startup if they don't exist (dev convenience only —
    use Alembic migrations for real schema management)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

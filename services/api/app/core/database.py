# =============================================================================
# SOVRN API - Database Configuration
# =============================================================================
"""
SQLAlchemy async database setup with pgvector support.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


# Create async engine
# Use NullPool for production to avoid connection issues with pgbouncer
_engine_kwargs = {
    "echo": settings.DEBUG,
}

if settings.is_production:
    # Production: use NullPool (no connection pooling, good for pgbouncer)
    _engine_kwargs["poolclass"] = NullPool
else:
    # Development: use connection pooling
    _engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    _engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    _engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT

engine = create_async_engine(
    str(settings.DATABASE_URL).replace("postgresql://", "postgresql+asyncpg://"),
    **_engine_kwargs,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

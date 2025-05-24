"""Database session management."""
from typing import Generator, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session as SyncSession
from sqlalchemy.pool import NullPool

from ....config.settings import settings

# Create database engines
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite setup
    SYNC_DATABASE_URL = settings.DATABASE_URL
    ASYNC_DATABASE_URL = settings.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
    
    # For SQLite, we need to set check_same_thread to False
    engine_kwargs = {"connect_args": {"check_same_thread": False}}
    async_engine_kwargs = {}
else:
    # PostgreSQL or other databases
    SYNC_DATABASE_URL = settings.DATABASE_URL
    ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    engine_kwargs = {}
    async_engine_kwargs = {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_pre_ping": settings.DB_POOL_PRE_PING,
        "echo": settings.SQL_ECHO,
    }

# Create sync engine and session factory
sync_engine = create_engine(SYNC_DATABASE_URL, **engine_kwargs)
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
    class_=SyncSession
)

# Create async engine and session factory
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    **async_engine_kwargs
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Dependency to get DB session for FastAPI
def get_db() -> Generator:
    """Get a database session."""
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        # Ensure the session is closed after the request is complete
        db.close()

# Context manager for async database sessions
@contextmanager
def get_session() -> Generator[AsyncSession, None, None]:
    """Get a database session with a context manager."""
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        session.close()

# For use in synchronous contexts
def get_sync_session() -> Generator[SyncSession, None, None]:
    """Get a synchronous database session."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

# For use in async contexts
async def get_async_session() -> AsyncSession:
    """Get an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# For use in dependency injection
async def get_db_session() -> AsyncSession:
    """Get a database session for dependency injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# For use in FastAPI dependency injection
async def get_db_dependency() -> Generator[AsyncSession, None, None]:
    """Get a database session for FastAPI dependency injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

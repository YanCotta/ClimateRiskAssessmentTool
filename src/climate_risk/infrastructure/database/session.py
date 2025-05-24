"""Database session management."""
import logging
from typing import Generator, Optional, AsyncGenerator, Any
from contextlib import asynccontextmanager, contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import sessionmaker, Session as SyncSession, declarative_base
from sqlalchemy.pool import NullPool

from ....config.settings import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create database URLs
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite setup
    SYNC_DATABASE_URL = settings.DATABASE_URL
    ASYNC_DATABASE_URL = settings.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
    
    # For SQLite, we need to set check_same_thread to False
    engine_kwargs = {
        "connect_args": {"check_same_thread": False},
        "echo": settings.SQL_ECHO,
    }
    async_engine_kwargs = {
        "echo": settings.SQL_ECHO,
    }
else:
    # PostgreSQL or other databases
    SYNC_DATABASE_URL = settings.DATABASE_URL
    ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )
    engine_kwargs = {
        "pool_pre_ping": settings.DB_POOL_PRE_PING,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "echo": settings.SQL_ECHO,
    }
    async_engine_kwargs = {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_pre_ping": settings.DB_POOL_PRE_PING,
        "echo": settings.SQL_ECHO,
    }

# Initialize database engines and session factories
sync_engine: Optional[Any] = None
async_engine: Optional[AsyncEngine] = None
SyncSessionLocal: Optional[sessionmaker] = None
AsyncSessionLocal: Optional[async_sessionmaker] = None

def init_engines() -> None:
    """Initialize database engines and session factories."""
    global sync_engine, async_engine, SyncSessionLocal, AsyncSessionLocal
    
    if sync_engine is None:
        logger.info(f"Initializing database engine for {SYNC_DATABASE_URL}")
        sync_engine = create_engine(SYNC_DATABASE_URL, **engine_kwargs)
        
        # Create sync session factory
        SyncSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=sync_engine,
            class_=SyncSession,
            expire_on_commit=False,
        )
    
    if async_engine is None:
        logger.info(f"Initializing async database engine for {ASYNC_DATABASE_URL}")
        async_engine = create_async_engine(ASYNC_DATABASE_URL, **async_engine_kwargs)
        
        # Create async session factory
        AsyncSessionLocal = async_sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

# Initialize engines on import
init_engines()

# Database initialization
async def init_db() -> None:
    """Initialize database tables."""
    from ..database.models import Base
    
    logger.info("Initializing database...")
    
    # Create tables if they don't exist
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialization completed")

# Dependency to get DB session for FastAPI
@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for FastAPI dependency injection."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Database session factory not initialized")
    
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        await session.close()

# Context manager for async database sessions
@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session with a context manager."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Database session factory not initialized")
    
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        await session.close()

# For use in synchronous contexts
@contextmanager
def get_sync_session() -> Generator[SyncSession, None, None]:
    """Get a synchronous database session."""
    if SyncSessionLocal is None:
        raise RuntimeError("Synchronous database session factory not initialized")
    
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        session.close()

# For use in async contexts with dependency injection
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    async with get_session() as session:
        yield session

# For use in FastAPI dependency injection
@asynccontextmanager
async def get_db_dependency() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for FastAPI dependency injection."""
    async with get_session() as session:
        yield session

# Health check function
async def check_db_health() -> bool:
    """Check if the database is healthy."""
    try:
        async with get_session() as session:
            # Simple query to check database connectivity
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

# Alias for backward compatibility
get_db_dependency = get_db

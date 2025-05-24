"""Database initialization and migration utilities."""
import asyncio
from typing import Optional, List
import logging
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ....config.settings import settings
from . import Base, async_engine, sync_engine

logger = logging.getLogger(__name__)

def run_migrations(script_location: str, dsn: str) -> None:
    """Run database migrations with Alembic.
    
    Args:
        script_location: Path to the migrations directory
        dsn: Database connection string
    """
    logger.info("Running database migrations...")
    
    # Configure Alembic
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", script_location)
    alembic_cfg.set_main_option("sqlalchemy.url", dsn)
    
    # Run migrations
    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations completed successfully")

async def init_db() -> None:
    """Initialize the database by creating all tables."""
    logger.info("Initializing database...")
    
    # Create all tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialization completed")

async def reset_db() -> None:
    """Reset the database by dropping and recreating all tables."""
    logger.warning("Resetting database...")
    
    # Drop all tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    # Recreate all tables
    await init_db()
    
    logger.info("Database reset completed")

def check_db_connection() -> bool:
    """Check if the database is accessible.
    
    Returns:
        bool: True if the database is accessible, False otherwise
    """
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

async def async_check_db_connection() -> bool:
    """Asynchronously check if the database is accessible.
    
    Returns:
        bool: True if the database is accessible, False otherwise
    """
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def get_migration_scripts(migration_dir: str) -> List[str]:
    """Get a list of migration script filenames.
    
    Args:
        migration_dir: Path to the migrations directory
        
    Returns:
        List of migration script filenames in order
    """
    migration_path = Path(migration_dir) / "versions"
    if not migration_path.exists():
        return []
    
    # Get all Python files in the versions directory
    migration_files = [f.name for f in migration_path.glob("*.py") if f.name != "__init__.py"]
    
    # Sort migrations by their numeric prefix
    migration_files.sort()
    
    return migration_files

async def migrate_db() -> None:
    """Run database migrations."""
    logger.info("Running database migrations...")
    
    # For now, we'll just create all tables
    # In a real application, you would use Alembic for migrations
    await init_db()
    
    logger.info("Database migrations completed")

async def main() -> None:
    """Main function for database initialization."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database management utility")
    parser.add_argument(
        "--init", 
        action="store_true", 
        help="Initialize the database (create tables)"
    )
    parser.add_argument(
        "--reset", 
        action="store_true", 
        help="Reset the database (drop and recreate all tables)"
    )
    parser.add_argument(
        "--migrate", 
        action="store_true", 
        help="Run database migrations"
    )
    parser.add_argument(
        "--check", 
        action="store_true", 
        help="Check database connection"
    )
    
    args = parser.parse_args()
    
    if args.init:
        await init_db()
    elif args.reset:
        await reset_db()
    elif args.migrate:
        await migrate_db()
    elif args.check:
        is_connected = await async_check_db_connection()
        print(f"Database connection: {'OK' if is_connected else 'FAILED'}")
    else:
        parser.print_help()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

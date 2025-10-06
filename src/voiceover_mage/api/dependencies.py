# ABOUTME: FastAPI dependency injection providers
# ABOUTME: Handles database session lifecycle and shared service instances

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from voiceover_mage.config import get_config
from voiceover_mage.persistence.manager import DatabaseManager

# Global database manager instance
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Get or create the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        config = get_config()
        database_url = config.database_url or "sqlite+aiosqlite:///./data/voiceover_mage.db"
        _db_manager = DatabaseManager(database_url=database_url)
    return _db_manager


async def get_db_session(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> AsyncGenerator[AsyncSession]:
    """Provide a database session for request handling.

    Yields:
        Database session that auto-commits on success, rolls back on error
    """
    async with db_manager.session() as session:
        yield session


@asynccontextmanager
async def lifespan_context():
    """FastAPI lifespan context for startup/shutdown handling."""
    # Startup: Initialize database tables
    db_manager = get_db_manager()
    await db_manager.create_tables()

    yield

    # Shutdown: Close database connections
    if _db_manager:
        await _db_manager.close()

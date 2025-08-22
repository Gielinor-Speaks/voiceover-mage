# ABOUTME: Database manager for async SQLite operations using SQLAlchemy async components
# ABOUTME: Handles persistence and caching of NPC extraction data

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from voiceover_mage.npc.persistence import NPCRawExtraction


class DatabaseManager:
    """Manages async database operations for NPC data persistence."""

    def __init__(self, database_url: str = "sqlite+aiosqlite:///./npc_data.db"):
        """Initialize the database manager.

        Args:
            database_url: SQLAlchemy async database URL (e.g. sqlite+aiosqlite:///./db.db)
        """
        self.database_url = database_url
        self.engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL query logging
        )

        # Create async session factory using async_sessionmaker
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Allow access to attributes after commit
        )

    async def create_tables(self) -> None:
        """Create all database tables if they don't exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def get_cached_extraction(self, npc_id: int) -> NPCRawExtraction | None:
        """Get a cached extraction by NPC ID.

        Args:
            npc_id: The NPC ID to look up

        Returns:
            The cached extraction or None if not found
        """
        async with self.async_session() as session:
            statement = select(NPCRawExtraction).where(NPCRawExtraction.npc_id == npc_id)
            result = await session.exec(statement)
            return result.first()

    async def save_extraction(self, extraction: NPCRawExtraction) -> NPCRawExtraction:
        """Save an extraction to the database.

        For caching purposes, if an extraction with the same npc_id already exists,
        this will return the existing one without updating it.

        Args:
            extraction: The extraction to save

        Returns:
            The saved extraction (or existing one if cached)
        """
        # Check if already exists (for caching)
        existing = await self.get_cached_extraction(extraction.npc_id)
        if existing:
            return existing

        async with self.async_session() as session:
            session.add(extraction)
            await session.commit()
            await session.refresh(extraction)
            return extraction

    async def clear_cache(self) -> None:
        """Clear all cached extractions from the database."""
        async with self.async_session() as session:
            # Use SQLAlchemy's delete statement for bulk delete
            from sqlalchemy import delete

            statement = delete(NPCRawExtraction)
            # Note: Use execute() for DELETE statements (exec() is only for SELECT)
            # We are using the connection's execute method to perform the bulk delete
            # as a workaround for SQLModel's overload not working with non-SELECT statements
            # SEE: https://github.com/fastapi/sqlmodel/issues/909#issuecomment-2372031146
            await (await session.connection()).execute(statement)
            await session.commit()

    async def close(self) -> None:
        """Close the database connection."""
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        """Get an async database session.

        Usage:
            async with db.session() as session:
                # Use session here
        """
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

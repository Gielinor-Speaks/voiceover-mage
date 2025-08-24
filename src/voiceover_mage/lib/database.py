# ABOUTME: Database manager for async SQLite operations using SQLAlchemy async components
# ABOUTME: Handles persistence and caching of NPC extraction data

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from voiceover_mage.npc.models import NPCExtraction, NPCRawExtractionData, ExtractionStage


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

    async def get_cached_extraction(self, npc_id: int) -> NPCExtraction | None:
        """Get a cached extraction by NPC ID.

        Args:
            npc_id: The NPC ID to look up

        Returns:
            The cached extraction or None if not found
        """
        async with self.async_session() as session:
            statement = select(NPCExtraction).where(NPCExtraction.npc_id == npc_id)
            result = await session.exec(statement)
            return result.first()

    async def save_extraction(self, extraction: NPCExtraction) -> NPCExtraction:
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

            statement = delete(NPCExtraction)
            # Note: Use execute() for DELETE statements (exec() is only for SELECT)
            # We are using the connection's execute method to perform the bulk delete
            # as a workaround for SQLModel's overload not working with non-SELECT statements
            # SEE: https://github.com/fastapi/sqlmodel/issues/909#issuecomment-2372031146
            await (await session.connection()).execute(statement)
            await session.commit()

    async def close(self) -> None:
        """Close the database connection."""
        await self.engine.dispose()

    async def save_raw_data(self, npc_id: int, npc_name: str, raw_data: dict, npc_variant: str | None = None) -> NPCExtraction:
        """Save raw extraction data, creating new record if needed."""
        existing = await self.get_cached_extraction(npc_id)
        
        if existing:
            existing.raw_data = raw_data
            existing.add_stage(ExtractionStage.RAW)
        else:
            existing = NPCExtraction(
                npc_id=npc_id,
                npc_name=npc_name,
                npc_variant=npc_variant,
                raw_data=raw_data,
                completed_stages=[ExtractionStage.RAW]
            )
        
        return await self.save_extraction(existing)

    async def update_stage_data(self, npc_id: int, stage: ExtractionStage, data: dict) -> NPCExtraction | None:
        """Update a specific pipeline stage with data."""
        extraction = await self.get_cached_extraction(npc_id)
        if not extraction:
            return None
            
        if stage == ExtractionStage.TEXT:
            extraction.text_analysis = data
        elif stage == ExtractionStage.VISUAL:
            extraction.visual_analysis = data  
        elif stage == ExtractionStage.PROFILE:
            extraction.character_profile = data
            
        extraction.add_stage(stage)
        return await self.save_extraction(extraction)

    async def get_incomplete_extractions(self, missing_stage: ExtractionStage) -> list[NPCExtraction]:
        """Get all extractions missing a specific pipeline stage."""
        async with self.async_session() as session:
            statement = select(NPCExtraction)
            result = await session.exec(statement)
            extractions = result.all()
            
            return [ext for ext in extractions if not ext.has_stage(missing_stage)]

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

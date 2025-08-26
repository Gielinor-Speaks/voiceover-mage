# ABOUTME: Database manager for persistence layer - async operations and caching
# ABOUTME: Coordinates database connections, transactions, and checkpoint management

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from voiceover_mage.core.models import ExtractionStage, NPCWikiSourcedData
from voiceover_mage.extraction.analysis.image import NPCVisualCharacteristics
from voiceover_mage.extraction.analysis.synthesizer import NPCDetails
from voiceover_mage.extraction.analysis.text import NPCTextCharacteristics
from voiceover_mage.persistence.models import NPCData as NPCExtraction
from voiceover_mage.utils.logging import get_logger


class DatabaseManager:
    """Manages async database operations for NPC data persistence."""

    def __init__(self, database_url: str = "sqlite+aiosqlite:///./data/voiceover_mage.db"):
        """Initialize the database manager.

        Args:
            database_url: SQLAlchemy async database URL (e.g. sqlite+aiosqlite:///./db.db)
        """
        self.database_url = database_url
        self.logger = get_logger(__name__)
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
        """Save or update an extraction in the database.

        Args:
            extraction: The extraction to save or update

        Returns:
            The saved/updated extraction
        """
        async with self.async_session() as session:
            # Check if this is an existing extraction (has an ID)
            if extraction.id is not None:
                # This is an update - merge the changes
                session.add(extraction)
            else:
                # This is a new extraction - check if one exists with same npc_id
                existing = await self.get_cached_extraction(extraction.npc_id)
                if existing:
                    # Update the existing one
                    for field_name in extraction.model_fields:
                        if hasattr(extraction, field_name):
                            new_value = getattr(extraction, field_name)
                            if field_name == "completed_stages":
                                # Merge stages instead of overwriting
                                existing_stages = set(existing.completed_stages or [])
                                new_stages = set(new_value or [])
                                merged_stages = list(existing_stages | new_stages)
                                setattr(existing, field_name, merged_stages)
                            else:
                                setattr(existing, field_name, new_value)
                    session.add(existing)
                    extraction = existing
                else:
                    # Add new extraction
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
            conn = await session.connection()
            await conn.execute(statement)
            await session.commit()

    async def close(self) -> None:
        """Close the database connection."""
        await self.engine.dispose()

    async def save_raw_data(
        self,
        npc_id: int,
        npc_name: str,
        raw_data: NPCWikiSourcedData,
        npc_variant: str | None = None,
        wiki_url: str = "",
        raw_markdown: str = "",
    ) -> NPCExtraction:
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
                wiki_url=wiki_url,
                raw_markdown=raw_markdown,
                raw_data=raw_data,
                completed_stages=[ExtractionStage.RAW],
            )

        return await self.save_extraction(existing)

    async def update_stage_data(
        self, npc_id: int, stage: ExtractionStage, data: NPCTextCharacteristics | NPCVisualCharacteristics | NPCDetails
    ) -> NPCExtraction | None:
        """Update a specific pipeline stage with data."""
        extraction = await self.get_cached_extraction(npc_id)
        if not extraction:
            return None

        if stage == ExtractionStage.TEXT:
            if isinstance(data, NPCTextCharacteristics):
                extraction.text_analysis = data
                extraction.add_stage(stage)
        elif stage == ExtractionStage.VISUAL:
            if isinstance(data, NPCVisualCharacteristics):
                extraction.visual_analysis = data
                extraction.add_stage(stage)
        elif stage == ExtractionStage.PROFILE and isinstance(data, NPCDetails):
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

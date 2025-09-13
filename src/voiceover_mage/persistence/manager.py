# ABOUTME: Database manager for persistence layer - async operations and caching
# ABOUTME: Coordinates database connections, transactions, and checkpoint management

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import and_, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from voiceover_mage.core.models import ExtractionStage, NPCWikiSourcedData
from voiceover_mage.extraction.analysis.image import NPCVisualCharacteristics
from voiceover_mage.extraction.analysis.synthesizer import NPCDetails
from voiceover_mage.extraction.analysis.text import NPCTextCharacteristics
from voiceover_mage.persistence.models import NPCData as NPCExtraction
from voiceover_mage.persistence.models import VoiceSample
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
            statement = select(NPCExtraction).where(NPCExtraction.id == npc_id)
            result = await session.exec(statement)
            return result.first()

    async def save_extraction(self, extraction: NPCExtraction) -> NPCExtraction:
        """Insert or update an extraction by primary key, with simple field assignment.

        - Merges `completed_stages` instead of overwriting.
        - Updates other fields directly.
        """
        async with self.async_session() as session:
            # Look up existing by primary key
            existing = await session.get(NPCExtraction, extraction.id)

            if existing:
                data = extraction.model_dump()

                # Merge completed stages
                if "completed_stages" in data and data["completed_stages"] is not None:
                    merged = list({*(existing.completed_stages or []), *(data["completed_stages"] or [])})
                    existing.completed_stages = merged

                # Assign remaining fields (skip id and completed_stages handled above)
                for field, value in data.items():
                    if field in {"id", "completed_stages"}:
                        continue
                    setattr(existing, field, value)

                session.add(existing)
                await session.commit()
                await session.refresh(existing)
                return existing
            else:
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

    # --------------------
    # Voice sample methods
    # --------------------

    async def save_voice_sample(
        self,
        *,
        npc_id: int,
        voice_prompt: str,
        sample_text: str,
        audio_bytes: bytes,
        provider: str,
        generator: str,
        is_representative: bool = False,
        provider_metadata: dict | None = None,
    ) -> VoiceSample:
        """Persist a new voice sample for an NPC.

        If is_representative is True, demotes all other samples for this NPC first.
        """
        async with self.async_session() as session:
            if is_representative:
                # Demote all existing representative samples for this NPC
                await session.exec(
                    update(VoiceSample)
                    .where(
                        and_(
                            VoiceSample.__table__.c.npc_id == npc_id,
                            VoiceSample.__table__.c.is_representative.is_(True),
                        )
                    )
                    .values(is_representative=False)
                )

            sample = VoiceSample(
                npc_id=npc_id,
                voice_prompt=voice_prompt,
                sample_text=sample_text,
                audio_bytes=audio_bytes,
                provider=provider,
                generator=generator,
                is_representative=is_representative,
                provider_metadata=provider_metadata or {},
            )
            session.add(sample)
            await session.commit()
            await session.refresh(sample)
            return sample

    async def list_voice_samples(self, npc_id: int) -> list[VoiceSample]:
        """Return all voice samples for an NPC, newest first."""
        async with self.async_session() as session:
            statement = (
                select(VoiceSample)
                .where(VoiceSample.npc_id == npc_id)
                .order_by(VoiceSample.__table__.c.created_at.desc())
            )
            result = await session.exec(statement)
            return list(result.all())

    async def set_representative_sample(self, npc_id: int, sample_id: int) -> VoiceSample | None:
        """Mark a specific sample as representative, demoting others for that NPC."""
        async with self.async_session() as session:
            # Ensure the sample exists and belongs to the NPC
            stmt = select(VoiceSample).where(VoiceSample.id == sample_id, VoiceSample.npc_id == npc_id)
            result = await session.exec(stmt)
            sample = result.first()
            if not sample:
                return None

            # Demote all others
            await session.exec(
                update(VoiceSample)
                .where(
                    and_(
                        VoiceSample.__table__.c.npc_id == npc_id,
                        VoiceSample.__table__.c.id != sample_id,
                    )
                )
                .values(is_representative=False)
            )
            # Promote this one
            sample.is_representative = True
            session.add(sample)
            await session.commit()
            await session.refresh(sample)
            return sample

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
                id=npc_id,
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

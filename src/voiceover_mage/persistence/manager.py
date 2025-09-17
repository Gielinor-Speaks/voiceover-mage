# ABOUTME: Database manager for normalized NPC persistence schema
# ABOUTME: Provides helpers to assemble pipeline state and derive workflow stages

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncGenerator

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from voiceover_mage.core.models import NPCWikiSourcedData
from voiceover_mage.extraction.analysis.image import NPCVisualCharacteristics
from voiceover_mage.extraction.analysis.synthesizer import NPCDetails
from voiceover_mage.extraction.analysis.text import NPCTextCharacteristics
from voiceover_mage.persistence.models import AudioTranscript, CharacterProfile, NPC, VoicePreview, WikiSnapshot, utcnow
from voiceover_mage.utils.logging import get_logger

STAGE_ORDER = [
    "wiki_data",
    "character_profile",
    "voice_generation",
    "voice_selection",
    "transcription",
    "complete",
]


@dataclass(slots=True)
class NPCPipelineState:
    """Aggregated NPC pipeline state assembled from normalized tables."""

    npc: NPC
    wiki_snapshot: WikiSnapshot | None = None
    character_profile_entry: CharacterProfile | None = None
    voice_previews: list[VoicePreview] = field(default_factory=list)
    audio_transcripts: list[AudioTranscript] = field(default_factory=list)

    # --- Convenience identity fields -------------------------------------------------
    @property
    def id(self) -> int:
        return self.npc.id

    @property
    def npc_name(self) -> str:
        return self.npc.name

    @property
    def npc_variant(self) -> str | None:
        return self.npc.variant

    @property
    def wiki_url(self) -> str:
        return self.npc.wiki_url

    @property
    def created_at(self):
        return self.npc.created_at

    @property
    def updated_at(self):
        return self.npc.updated_at

    # --- Snapshot data ---------------------------------------------------------------
    @property
    def raw_markdown(self) -> str:
        return self.wiki_snapshot.raw_markdown if self.wiki_snapshot else ""

    @property
    def chathead_image_url(self) -> str | None:
        return self.wiki_snapshot.chathead_image_url if self.wiki_snapshot else None

    @property
    def image_url(self) -> str | None:
        return self.wiki_snapshot.image_url if self.wiki_snapshot else None

    @property
    def raw_data(self) -> NPCWikiSourcedData | None:
        return self.wiki_snapshot.raw_data_json if self.wiki_snapshot else None

    @property
    def source_checksum(self) -> str | None:
        return self.wiki_snapshot.source_checksum if self.wiki_snapshot else None

    @property
    def fetched_at(self):
        return self.wiki_snapshot.fetched_at if self.wiki_snapshot else None

    @property
    def extraction_success(self) -> bool:
        if self.wiki_snapshot is None:
            return False
        return self.wiki_snapshot.extraction_success

    @property
    def error_message(self) -> str | None:
        return self.wiki_snapshot.error_message if self.wiki_snapshot else None

    # --- Analysis and profile --------------------------------------------------------
    @property
    def text_analysis(self) -> NPCTextCharacteristics | None:
        if not self.character_profile_entry:
            return None
        return self.character_profile_entry.text_analysis_json

    @property
    def visual_analysis(self) -> NPCVisualCharacteristics | None:
        if not self.character_profile_entry:
            return None
        return self.character_profile_entry.visual_analysis_json

    @property
    def character_profile(self) -> NPCDetails | None:
        if not self.character_profile_entry:
            return None
        return self.character_profile_entry.profile_json

    @property
    def pipeline_version(self) -> str | None:
        if not self.character_profile_entry:
            return None
        return self.character_profile_entry.pipeline_version

    @property
    def profile_updated_at(self):
        if not self.character_profile_entry:
            return None
        return self.character_profile_entry.updated_at

    # --- Voice previews --------------------------------------------------------------
    @property
    def selected_preview_id(self) -> int | None:
        return self.npc.selected_preview_id

    @property
    def selected_preview(self) -> VoicePreview | None:
        if not self.voice_previews:
            return None
        if self.npc.selected_preview_id is not None:
            for preview in self.voice_previews:
                if preview.id == self.npc.selected_preview_id:
                    return preview
        for preview in self.voice_previews:
            if preview.is_representative:
                return preview
        return None

    @property
    def has_voice_previews(self) -> bool:
        return bool(self.voice_previews)

    @property
    def transcripts_for_selected_preview(self) -> list[AudioTranscript]:
        preview = self.selected_preview
        if not preview:
            return []
        preview_id = preview.id
        if preview_id is None:
            return []
        return [t for t in self.audio_transcripts if t.preview_id == preview_id]

    # --- Stage computation -----------------------------------------------------------
    @property
    def stage_flags(self) -> dict[str, bool]:
        wiki_done = bool(self.wiki_snapshot and self.wiki_snapshot.raw_markdown)
        profile_done = bool(self.character_profile)
        voice_generated = bool(self.voice_previews)
        selection_done = self.selected_preview is not None
        transcription_done = bool(self.transcripts_for_selected_preview)

        complete = wiki_done and profile_done and voice_generated and selection_done

        return {
            "wiki_data": wiki_done,
            "character_profile": profile_done,
            "voice_generation": voice_generated,
            "voice_selection": selection_done,
            "transcription": transcription_done,
            "complete": complete and transcription_done,
        }

    @property
    def completed_stages(self) -> list[str]:
        flags = self.stage_flags
        return [stage for stage in STAGE_ORDER if flags.get(stage)]

    def model_dump(self) -> dict[str, Any]:
        """Approximate dict representation for debugging and tests."""

        return {
            "npc": self.npc,
            "wiki_snapshot": self.wiki_snapshot,
            "character_profile": self.character_profile_entry,
            "voice_previews": list(self.voice_previews),
            "audio_transcripts": list(self.audio_transcripts),
            "completed_stages": self.completed_stages,
        }


class DatabaseManager:
    """Manages async database operations for normalized NPC data."""

    def __init__(self, database_url: str = "sqlite+aiosqlite:///./data/voiceover_mage.db"):
        self.database_url = database_url
        self.logger = get_logger(__name__)
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def ensure_npc(
        self,
        *,
        npc_id: int,
        name: str,
        wiki_url: str,
        variant: str | None = None,
    ) -> NPC:
        """Create or update the core NPC identity row."""
        async with self.async_session() as session:
            npc = await session.get(NPC, npc_id)
            if npc:
                changed = False
                if npc.name != name:
                    npc.name = name
                    changed = True
                if npc.variant != variant:
                    npc.variant = variant
                    changed = True
                if npc.wiki_url != wiki_url:
                    npc.wiki_url = wiki_url
                    changed = True
                if changed:
                    npc.updated_at = utcnow()
                    session.add(npc)
            else:
                npc = NPC(id=npc_id, name=name, variant=variant, wiki_url=wiki_url)
                session.add(npc)
            await session.commit()
            await session.refresh(npc)
            return npc

    async def upsert_wiki_snapshot(
        self,
        *,
        npc_id: int,
        raw_markdown: str,
        chathead_image_url: str | None,
        image_url: str | None,
        raw_data: NPCWikiSourcedData | None,
        source_checksum: str | None,
        fetched_at: datetime | None = None,
        extraction_success: bool = True,
        error_message: str | None = None,
    ) -> WikiSnapshot:
        """Insert or update the wiki snapshot for an NPC."""
        timestamp = fetched_at or utcnow()
        async with self.async_session() as session:
            snapshot = await session.get(WikiSnapshot, npc_id)
            if snapshot:
                snapshot.raw_markdown = raw_markdown
                snapshot.chathead_image_url = chathead_image_url
                snapshot.image_url = image_url
                snapshot.raw_data_json = raw_data
                snapshot.source_checksum = source_checksum
                snapshot.fetched_at = timestamp
                snapshot.extraction_success = extraction_success
                snapshot.error_message = error_message
            else:
                snapshot = WikiSnapshot(
                    npc_id=npc_id,
                    raw_markdown=raw_markdown,
                    chathead_image_url=chathead_image_url,
                    image_url=image_url,
                    raw_data_json=raw_data,
                    source_checksum=source_checksum,
                    fetched_at=timestamp,
                    extraction_success=extraction_success,
                    error_message=error_message,
                )
            session.add(snapshot)
            npc = await session.get(NPC, npc_id)
            if npc:
                npc.updated_at = utcnow()
                session.add(npc)
            await session.commit()
            await session.refresh(snapshot)
            return snapshot

    async def upsert_character_profile(
        self,
        *,
        npc_id: int,
        profile: NPCDetails | None,
        text_analysis: NPCTextCharacteristics | None = None,
        visual_analysis: NPCVisualCharacteristics | None = None,
        pipeline_version: str | None = None,
    ) -> CharacterProfile:
        """Insert or update the character profile for an NPC."""
        timestamp = utcnow()
        async with self.async_session() as session:
            profile_row = await session.get(CharacterProfile, npc_id)
            if profile_row:
                profile_row.profile_json = profile
                profile_row.text_analysis_json = text_analysis
                profile_row.visual_analysis_json = visual_analysis
                profile_row.pipeline_version = pipeline_version
                profile_row.updated_at = timestamp
            else:
                profile_row = CharacterProfile(
                    npc_id=npc_id,
                    profile_json=profile,
                    text_analysis_json=text_analysis,
                    visual_analysis_json=visual_analysis,
                    pipeline_version=pipeline_version,
                    updated_at=timestamp,
                )
            session.add(profile_row)
            npc = await session.get(NPC, npc_id)
            if npc:
                npc.updated_at = timestamp
                session.add(npc)
            await session.commit()
            await session.refresh(profile_row)
            return profile_row

    async def create_voice_preview(
        self,
        *,
        npc_id: int,
        voice_prompt: str,
        sample_text: str,
        provider: str,
        model: str,
        generation_metadata: dict[str, Any] | None = None,
        audio_path: str | None = None,
        audio_bytes: bytes | None = None,
        is_representative: bool = False,
    ) -> VoicePreview:
        """Persist a generated voice preview."""
        async with self.async_session() as session:
            if is_representative:
                await session.exec(
                    update(VoicePreview)
                    .where(VoicePreview.npc_id == npc_id)
                    .values(is_representative=False)
                )
            preview = VoicePreview(
                npc_id=npc_id,
                voice_prompt=voice_prompt,
                sample_text=sample_text,
                provider=provider,
                model=model,
                generation_metadata=generation_metadata or {},
                audio_path=audio_path,
                audio_bytes=audio_bytes,
                is_representative=is_representative,
            )
            session.add(preview)
            await session.commit()
            await session.refresh(preview)

            if is_representative and preview.id is not None:
                npc = await session.get(NPC, npc_id)
                if npc:
                    npc.selected_preview_id = preview.id
                    npc.updated_at = utcnow()
                    session.add(npc)
                    await session.commit()

            return preview

    async def set_selected_voice_preview(self, npc_id: int, preview_id: int) -> VoicePreview | None:
        """Mark a voice preview as the selected representative for the NPC."""
        async with self.async_session() as session:
            preview = await session.get(VoicePreview, preview_id)
            if not preview or preview.npc_id != npc_id:
                return None

            await session.exec(
                update(VoicePreview)
                .where(VoicePreview.npc_id == npc_id)
                .values(is_representative=False)
            )

            preview.is_representative = True
            session.add(preview)

            npc = await session.get(NPC, npc_id)
            if npc:
                npc.selected_preview_id = preview.id
                npc.updated_at = utcnow()
                session.add(npc)

            await session.commit()
            await session.refresh(preview)
            return preview

    async def list_voice_previews(self, npc_id: int) -> list[VoicePreview]:
        """Return all voice previews for an NPC, newest first."""
        async with self.async_session() as session:
            statement = (
                select(VoicePreview)
                .where(VoicePreview.npc_id == npc_id)
                .order_by(VoicePreview.created_at.desc())
            )
            result = await session.exec(statement)
            return list(result.scalars().all())

    async def save_audio_transcript(
        self,
        *,
        npc_id: int,
        preview_id: int,
        provider: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> AudioTranscript:
        """Persist a transcript for a voice preview."""
        async with self.async_session() as session:
            transcript = AudioTranscript(
                npc_id=npc_id,
                preview_id=preview_id,
                provider=provider,
                text=text,
                metadata_json=metadata or {},
            )
            session.add(transcript)
            await session.commit()
            await session.refresh(transcript)
            return transcript

    async def get_cached_extraction(self, npc_id: int) -> NPCPipelineState | None:
        """Assemble the aggregated pipeline state for an NPC."""
        async with self.async_session() as session:
            npc = await session.get(NPC, npc_id)
            if not npc:
                return None

            snapshot = await session.get(WikiSnapshot, npc_id)
            profile_row = await session.get(CharacterProfile, npc_id)

            previews_result = await session.exec(
                select(VoicePreview)
                .where(VoicePreview.npc_id == npc_id)
                .order_by(VoicePreview.created_at.desc())
            )
            previews = list(previews_result.scalars().all())

            transcripts_result = await session.exec(
                select(AudioTranscript).where(AudioTranscript.npc_id == npc_id)
            )
            transcripts = list(transcripts_result.scalars().all())

            return NPCPipelineState(
                npc=npc,
                wiki_snapshot=snapshot,
                character_profile_entry=profile_row,
                voice_previews=previews,
                audio_transcripts=transcripts,
            )

    async def compute_stage_map(self, npc_id: int) -> dict[str, bool]:
        """Return derived stage flags for the NPC."""
        state = await self.get_cached_extraction(npc_id)
        if not state:
            return {stage: False for stage in STAGE_ORDER}
        return state.stage_flags

    async def clear_cache(self) -> None:
        """Remove all cached NPC pipeline data."""
        async with self.async_session() as session:
            await session.exec(delete(AudioTranscript))
            await session.exec(delete(VoicePreview))
            await session.exec(delete(CharacterProfile))
            await session.exec(delete(WikiSnapshot))
            await session.exec(delete(NPC))
            await session.commit()

    async def close(self) -> None:
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yield an async session for advanced scenarios."""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

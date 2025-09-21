# ABOUTME: Normalized persistence models for NPC pipeline state
# ABOUTME: Captures NPC identity, wiki snapshots, character profiles, voice previews, and transcripts

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import LargeBinary
from sqlmodel import JSON, Column, Field, SQLModel

from voiceover_mage.core.models import NPCWikiSourcedData
from voiceover_mage.extraction.analysis.image import NPCVisualCharacteristics
from voiceover_mage.extraction.analysis.synthesizer import NPCDetails
from voiceover_mage.extraction.analysis.text import NPCTextCharacteristics
from voiceover_mage.persistence.json_types import PydanticJson


def utcnow() -> datetime:
    """Returns the current UTC timestamp."""

    return datetime.now(UTC)


class NPC(SQLModel, table=True):
    """Persistent identity for an NPC."""

    __tablename__ = "npc"  # type: ignore[assignment]

    id: int = Field(primary_key=True, description="Unique NPC identifier from the wiki")
    name: str = Field(description="Canonical NPC name")
    variant: str | None = Field(default=None, description="Variant or qualifier for the NPC")
    wiki_url: str = Field(description="URL to the NPC's wiki page")
    selected_preview_id: int | None = Field(
        default=None,
        foreign_key="voice_preview.id",
        description="Currently selected voice preview for this NPC",
    )
    created_at: datetime = Field(default_factory=utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=utcnow, description="Last modification timestamp")


class WikiSnapshot(SQLModel, table=True):
    """Cached wiki content and related metadata for an NPC."""

    __tablename__ = "wiki_snapshot"  # type: ignore[assignment]

    npc_id: int = Field(primary_key=True, foreign_key="npc.id", description="FK to npc.id")
    raw_markdown: str = Field(description="Raw markdown extracted from the wiki page")
    chathead_image_url: str | None = Field(default=None, description="Chathead image URL")
    image_url: str | None = Field(default=None, description="Primary image URL")
    raw_data_json: NPCWikiSourcedData | None = Field(
        default=None,
        sa_column=Column(PydanticJson(NPCWikiSourcedData)),
        description="Structured raw data extracted from the wiki",
    )
    source_checksum: str | None = Field(default=None, description="Checksum of the source content")
    fetched_at: datetime = Field(default_factory=utcnow, description="Timestamp when the snapshot was fetched")
    extraction_success: bool = Field(default=True, description="Whether the snapshot extraction succeeded")
    error_message: str | None = Field(default=None, description="Error message if extraction failed")


class CharacterProfile(SQLModel, table=True):
    """Synthesized characterization data for an NPC."""

    __tablename__ = "character_profile"  # type: ignore[assignment]

    npc_id: int = Field(primary_key=True, foreign_key="npc.id", description="FK to npc.id")
    profile_json: NPCDetails | None = Field(
        default=None,
        sa_column=Column(PydanticJson(NPCDetails)),
        description="Synthesized character profile ready for voice generation",
    )
    text_analysis_json: NPCTextCharacteristics | None = Field(
        default=None,
        sa_column=Column(PydanticJson(NPCTextCharacteristics)),
        description="Detailed text analysis results",
    )
    visual_analysis_json: NPCVisualCharacteristics | None = Field(
        default=None,
        sa_column=Column(PydanticJson(NPCVisualCharacteristics)),
        description="Detailed visual analysis results",
    )
    pipeline_version: str | None = Field(default=None, description="Pipeline version that produced this profile")
    updated_at: datetime = Field(default_factory=utcnow, description="Timestamp of the latest profile update")


class VoicePreview(SQLModel, table=True):
    """Generated voice preview for an NPC."""

    __tablename__ = "voice_preview"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True, description="Primary key for the voice preview")
    npc_id: int = Field(index=True, foreign_key="npc.id", description="FK to npc.id")
    voice_prompt: str = Field(description="Prompt used to generate the voice preview")
    sample_text: str = Field(description="Sample text spoken in the preview")
    provider: str = Field(description="Voice generation provider")
    model: str = Field(description="Provider model or generator identifier")
    generation_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Provider-specific metadata for the generation",
    )
    audio_path: str | None = Field(default=None, description="Filesystem path to the generated audio preview")
    audio_bytes: bytes | None = Field(
        default=None,
        sa_column=Column(LargeBinary),
        description="Raw audio bytes for the preview (if stored inline)",
    )
    is_representative: bool = Field(default=False, description="Whether this preview is the chosen representative")
    created_at: datetime = Field(default_factory=utcnow, description="Creation timestamp")


class AudioTranscript(SQLModel, table=True):
    """Transcript associated with an audio preview."""

    __tablename__ = "audio_transcript"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True, description="Primary key for the transcript")
    npc_id: int = Field(index=True, foreign_key="npc.id", description="FK to npc.id")
    preview_id: int = Field(foreign_key="voice_preview.id", description="FK to voice_preview.id")
    provider: str = Field(description="Transcription provider")
    text: str = Field(description="Transcript text")
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Additional metadata for the transcript",
    )
    created_at: datetime = Field(default_factory=utcnow, description="Creation timestamp")

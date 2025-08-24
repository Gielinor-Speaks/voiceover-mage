# ABOUTME: Database models for persistence layer - SQLModel tables with proper JSON columns
# ABOUTME: Checkpoint-based pipeline state management with TypeAdapter integration

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import JSON, Column, Field, SQLModel

if TYPE_CHECKING:
    from voiceover_mage.core.models import ExtractionStage


class NPCRawExtraction(SQLModel, table=True):
    """Raw extraction data from NPC wiki pages.

    This model stores the unprocessed markdown and image URLs extracted from
    wiki pages, providing a cache layer before any LLM analysis.
    """

    __tablename__ = "npc_raw_extractions"  # type: ignore[assignment]

    # Primary key
    id: int | None = Field(default=None, primary_key=True)

    # NPC identification
    npc_id: int = Field(index=True, description="Unique NPC ID from the wiki")
    npc_name: str = Field(description="Name of the NPC")
    npc_variant: str | None = Field(default=None, description="NPC variant if applicable")
    wiki_url: str = Field(description="Full URL to the NPC's wiki page")

    # Extracted content
    raw_markdown: str = Field(description="Full markdown content of the wiki page")

    # Simple image URLs (for Phase 1)
    chathead_image_url: str | None = Field(default=None, description="URL to the NPC's chathead image")
    image_url: str | None = Field(default=None, description="URL to the NPC's main/body image")

    # Pipeline stage management
    raw_data: dict = Field(default_factory=dict, sa_column=Column(JSON), description="Raw extracted data")
    text_analysis: dict = Field(default_factory=dict, sa_column=Column(JSON), description="Text analysis results")
    visual_analysis: dict = Field(default_factory=dict, sa_column=Column(JSON), description="Visual analysis results")
    character_profile: dict = Field(default_factory=dict, sa_column=Column(JSON), description="Character profile data")
    completed_stages: list[str] = Field(
        default_factory=list, sa_column=Column(JSON), description="Completed pipeline stages"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Timestamp when this extraction was created"
    )
    extraction_success: bool = Field(default=True, description="Whether the extraction succeeded")
    error_message: str | None = Field(default=None, description="Error message if extraction failed")

    def has_images(self) -> bool:
        """Check if any image URLs are available."""
        return bool(self.chathead_image_url or self.image_url)

    def add_stage(self, stage: "ExtractionStage") -> None:
        """Add a stage to completed stages."""
        if stage.value not in self.completed_stages:
            self.completed_stages.append(stage.value)

    def has_stage(self, stage: "ExtractionStage") -> bool:
        """Check if a stage has been completed."""
        return stage.value in self.completed_stages


# TODO: Enhanced pipeline model with checkpoint support
# This will be implemented in Phase 4 with proper TypeAdapter JSON columns:
#
# class NPCExtraction(SQLModel, table=True):
#     """Enhanced pipeline model with checkpoints."""
#     __tablename__ = "npc_extractions"
#
#     id: int | None = Field(primary_key=True, default=None)
#     npc_id: int = Field(index=True)
#     npc_name: str
#     current_stage: ExtractionStage
#
#     # Checkpoint data with proper TypeAdapter
#     raw_data: NPCRawExtractionData | None = Field(
#         default=None,
#         sa_column=Column(PydanticJson(NPCRawExtractionData))
#     )
#     text_analysis: NPCTextCharacteristics | None = Field(
#         default=None,
#         sa_column=Column(PydanticJson(NPCTextCharacteristics))
#     )
#     visual_analysis: NPCVisualCharacteristics | None = Field(
#         default=None,
#         sa_column=Column(PydanticJson(NPCVisualCharacteristics))
#     )

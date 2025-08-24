# ABOUTME: Working NPC extraction model using TypeAdapter approach
# ABOUTME: Proper JSON columns with Pydantic validation and serialization

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import Column
from sqlmodel import SQLModel

from voiceover_mage.lib.json_types import PydanticJson


class ExtractionStage(str, Enum):
    """Pipeline stages for NPC processing."""
    RAW = "raw"
    TEXT = "text"
    VISUAL = "visual"
    PROFILE = "profile"


class NPCRawExtractionData(BaseModel):
    """Raw data extracted from wiki pages."""
    wiki_url: str
    raw_markdown: str
    chathead_image_url: str | None = None
    image_url: str | None = None
    extraction_success: bool = True
    error_message: str | None = None
    markdown_length: int = Field(description="Length of markdown content")


class NPCExtraction(SQLModel, table=True):
    """NPC extraction record with TypeAdapter JSON columns."""
    
    __tablename__ = "npc_extractions"
    
    # Primary identification
    id: int | None = Field(primary_key=True, default=None)
    npc_id: int = Field(index=True, description="Unique NPC ID from wiki")
    npc_name: str = Field(description="Name of the NPC")
    npc_variant: str | None = Field(default=None, description="NPC variant like 'Pete', 'Ardougne', etc.")

    # JSON fields using TypeAdapter
    raw_data: dict[str, Any] | None = Field(
        default=None, 
        sa_column=Column(PydanticJson(dict[str, Any])), 
        description="Raw markdown and extraction data"
    )

    text_analysis: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(PydanticJson(dict[str, Any])),
        description="Text-based personality and behavioral analysis",
    )

    visual_analysis: dict[str, Any] | None = Field(
        default=None, 
        sa_column=Column(PydanticJson(dict[str, Any])), 
        description="Visual appearance and image analysis"
    )

    character_profile: dict[str, Any] | None = Field(
        default=None, 
        sa_column=Column(PydanticJson(dict[str, Any])), 
        description="Final synthesized character profile"
    )

    completed_stages: list[str] = Field(
        default_factory=list,
        sa_column=Column(PydanticJson(list[str])),
        description="List of completed pipeline stages",
    )

    # Metadata
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="When this record was last modified"
    )
    overall_confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Overall confidence score for the extraction"
    )

    # Methods for stage management
    def has_stage(self, stage: ExtractionStage) -> bool:
        """Check if a pipeline stage has been completed."""
        return stage in self.completed_stages

    def add_stage(self, stage: ExtractionStage) -> None:
        """Mark a pipeline stage as completed."""
        if stage not in self.completed_stages:
            self.completed_stages.append(stage)
            self.last_updated = datetime.now(UTC)

    def get_wiki_url(self) -> str | None:
        """Get wiki URL from raw data if available."""
        return self.raw_data.get("wiki_url") if self.raw_data else None

    def has_images(self) -> bool:
        """Check if any image URLs are available."""
        if not self.raw_data:
            return False
        return bool(self.raw_data.get("chathead_image_url") or self.raw_data.get("image_url"))

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage of pipeline stages."""
        total_stages = len(ExtractionStage)
        completed = len(self.completed_stages)
        return (completed / total_stages) * 100
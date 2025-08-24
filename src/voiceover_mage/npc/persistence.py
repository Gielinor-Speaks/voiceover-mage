# ABOUTME: SQLModel definitions for persisting NPC raw extraction data
# ABOUTME: Provides database schema for caching wiki page content and images

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    from voiceover_mage.npc.models.images import ImageExtractionSet


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
    wiki_url: str = Field(description="Full URL to the NPC's wiki page")

    # Extracted content
    raw_markdown: str = Field(description="Full markdown content of the wiki page")
    
    # Simple image URLs (for Phase 1)
    chathead_image_url: str | None = Field(default=None, description="URL to the NPC's chathead image")
    image_url: str | None = Field(default=None, description="URL to the NPC's main/body image")

    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Timestamp when this extraction was created"
    )
    extraction_success: bool = Field(default=True, description="Whether the extraction succeeded")
    error_message: str | None = Field(default=None, description="Error message if extraction failed")

    def has_images(self) -> bool:
        """Check if any image URLs are available."""
        return bool(self.chathead_image_url or self.image_url)

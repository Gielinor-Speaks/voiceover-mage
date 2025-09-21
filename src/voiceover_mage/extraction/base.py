# ABOUTME: Simple protocol interface for extracting raw NPC data from sources
# ABOUTME: Phase 1 focus - extract markdown and image URLs without LLM processing

from typing import Protocol

from pydantic import BaseModel, ConfigDict


class RawNPCExtractor(Protocol):
    """Protocol for extracting raw NPC data by ID. Simple interface for getting
    markdown content and image URLs without LLM analysis."""

    async def extract(self, npc_id: int) -> "RawExtractionResult":
        """Extract raw NPC data from the given NPC ID.

        Args:
            npc_id: The ID of the NPC to extract data from

        Returns:
            Raw extraction with markdown content and image URLs

        Raises:
            ExtractionError: If extraction fails
        """
        ...


class ExtractionError(Exception):
    """Raised when NPC data extraction fails."""

    pass


class RawExtractionResult(BaseModel):
    """Minimal result from the raw extraction stage."""

    npc_id: int
    npc_name: str
    wiki_url: str
    raw_markdown: str
    chathead_image_url: str | None = None
    image_url: str | None = None
    npc_variant: str | None = None
    extraction_success: bool = True
    error_message: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def has_markdown(self) -> bool:
        return bool(self.raw_markdown)

    @property
    def id(self) -> int:
        return self.npc_id

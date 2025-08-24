# ABOUTME: Simple protocol interface for extracting raw NPC data from sources
# ABOUTME: Phase 1 focus - extract markdown and image URLs without LLM processing

from typing import Protocol

from voiceover_mage.persistence import NPCRawExtraction


class RawNPCExtractor(Protocol):
    """Protocol for extracting raw NPC data by ID. Simple interface for getting
    markdown content and image URLs without LLM analysis."""

    async def extract(self, npc_id: int) -> NPCRawExtraction:
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

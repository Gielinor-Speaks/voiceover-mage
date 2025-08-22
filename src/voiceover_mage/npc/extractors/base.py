# ABOUTME: Abstract interface for extracting NPC data from various sources
# ABOUTME: Defines protocols and base classes for crawling-agnostic data extraction

from typing import Protocol

from ..models import NPCWikiSourcedData


class NPCDataExtractor(Protocol):
    """Protocol for extracting NPC data by ID. This protocol defines the methods required for
    extracting NPC data from any data source."""

    async def extract_npc_data(self, npc_id: int) -> NPCWikiSourcedData:
        """Extract NPC data from the given NPC ID.

        Args:
            npc_id: The ID of the NPC to extract data from

        Returns:
            The extracted NPC data object

        Raises:
            ExtractionError: If extraction fails
        """
        ...


class ExtractionError(Exception):
    """Raised when NPC data extraction fails."""

    pass

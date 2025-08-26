# ABOUTME: High-level service API for core business logic and orchestration
# ABOUTME: Coordinates extraction → persistence → business object workflow

from voiceover_mage.extraction.base import RawNPCExtractor
from voiceover_mage.extraction.wiki.markdown import MarkdownNPCExtractor
from voiceover_mage.persistence import DatabaseManager, NPCData
from voiceover_mage.utils.logging import get_logger

# Using NPCData as NPCExtraction alias during transition
NPCExtraction = NPCData


class NPCExtractionService:
    """Service for extracting NPC data with caching and database persistence.

    Implements cache-first logic: check database before extracting fresh data.
    """

    def __init__(
        self,
        extractor: RawNPCExtractor | None = None,
        database: DatabaseManager | None = None,
        force_refresh: bool = False,
    ):
        """Initialize the extraction service.

        Args:
            extractor: The raw NPC extractor to use (defaults to MarkdownNPCExtractor)
            database: Database manager (defaults to new DatabaseManager)
            force_refresh: If True, bypass cache and extract fresh data
        """
        self.extractor = extractor or MarkdownNPCExtractor()
        self.database = database or DatabaseManager()
        self.force_refresh = force_refresh
        self.logger = get_logger(__name__)

    async def extract_npc(self, npc_id: int) -> NPCExtraction:
        """Extract NPC data with cache-first logic.

        Args:
            npc_id: The NPC ID to extract

        Returns:
            The NPC extraction (from cache or fresh)
        """
        # Ensure database tables exist
        try:
            await self.database.create_tables()
        except Exception as e:
            self.logger.error("Failed to create database tables", error=str(e))
            raise

        # Check cache first (unless force refresh is enabled)
        if not self.force_refresh:
            cached_extraction = await self.database.get_cached_extraction(npc_id)
            if cached_extraction:
                self.logger.info(
                    "Using cached extraction",
                    npc_id=npc_id,
                    npc_name=cached_extraction.npc_name,
                    cached_at=cached_extraction.created_at,
                    extraction_success=cached_extraction.extraction_success,
                )
                return cached_extraction

        # Extract fresh data
        self.logger.info("Extracting fresh NPC data", npc_id=npc_id, force_refresh=self.force_refresh)

        extraction = await self.extractor.extract(npc_id)

        # Save to database (cache for future use)
        if self.force_refresh:
            # For force refresh, we want to update the cache, so save directly
            saved_extraction = await self._save_extraction_forced(extraction)
        else:
            # Normal save with cache check
            saved_extraction = await self.database.save_extraction(extraction)

        self.logger.info(
            "Extraction completed and cached",
            npc_id=npc_id,
            npc_name=saved_extraction.npc_name,
            extraction_success=saved_extraction.extraction_success,
            markdown_length=len(saved_extraction.raw_markdown),
        )

        return saved_extraction

    async def extract_multiple_npcs(self, npc_ids: list[int], progress_callback=None) -> list[NPCData]:
        """Extract data for multiple NPCs with optional progress reporting.

        Args:
            npc_ids: List of NPC IDs to extract
            progress_callback: Optional callback for progress updates (npc_id, current, total)

        Returns:
            List of extraction results
        """
        results = []
        total = len(npc_ids)

        self.logger.info("Starting batch extraction", npc_count=total, force_refresh=self.force_refresh)

        for i, npc_id in enumerate(npc_ids, 1):
            try:
                if progress_callback:
                    progress_callback(npc_id, i, total)

                extraction = await self.extract_npc(npc_id)
                results.append(extraction)

            except Exception as e:
                self.logger.error(
                    "Failed to extract NPC in batch", npc_id=npc_id, error=str(e), current_index=i, total=total
                )
                # Add failed extraction record
                failed_extraction = NPCData(
                    npc_id=npc_id,
                    npc_name=f"NPC_{npc_id}",
                    wiki_url="",
                    raw_markdown="",
                    chathead_image_url=None,
                    image_url=None,
                    extraction_success=False,
                    error_message=str(e),
                )
                results.append(failed_extraction)

        successful = sum(1 for r in results if r.extraction_success)
        self.logger.info("Batch extraction completed", total=total, successful=successful, failed=total - successful)

        return results

    async def get_extraction_status(self, npc_id: int) -> dict:
        """Get the status of an extraction from the cache.

        Args:
            npc_id: The NPC ID to check

        Returns:
            Status dictionary with extraction information
        """
        cached = await self.database.get_cached_extraction(npc_id)

        if not cached:
            return {"npc_id": npc_id, "cached": False, "extraction_success": None, "created_at": None, "npc_name": None}

        return {
            "npc_id": npc_id,
            "cached": True,
            "extraction_success": cached.extraction_success,
            "created_at": cached.created_at,
            "npc_name": cached.npc_name,
            "error_message": cached.error_message,
            "has_chathead": cached.chathead_image_url is not None,
            "has_image": cached.image_url is not None,
            "markdown_length": len(cached.raw_markdown) if cached.raw_markdown else 0,
        }

    async def clear_cache(self) -> None:
        """Clear all cached extractions."""
        await self.database.clear_cache()
        self.logger.info("Cleared all cached extractions")

    async def _save_extraction_forced(self, extraction: NPCData) -> NPCData:
        """Save extraction bypassing cache check (for force refresh)."""
        # Delete existing extraction if it exists
        existing = await self.database.get_cached_extraction(extraction.npc_id)
        if existing:
            async with self.database.async_session() as session:
                await session.delete(existing)
                await session.commit()

        # Save the new extraction
        async with self.database.async_session() as session:
            session.add(extraction)
            await session.commit()
            await session.refresh(extraction)
            return extraction

    async def close(self) -> None:
        """Close the service and clean up resources."""
        await self.database.close()

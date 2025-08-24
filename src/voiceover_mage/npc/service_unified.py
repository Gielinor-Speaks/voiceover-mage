# ABOUTME: Updated service layer for unified NPCExtraction model with pipeline stages
# ABOUTME: Coordinates raw extraction and converts to new unified persistence model

from voiceover_mage.lib.database import DatabaseManager
from voiceover_mage.lib.logging import get_logger
from voiceover_mage.npc.extractors.base import RawNPCExtractor
from voiceover_mage.npc.extractors.markdown import MarkdownNPCExtractor
from voiceover_mage.npc.models import NPCExtraction, NPCRawExtractionData, ExtractionStage
from voiceover_mage.npc.persistence import NPCRawExtraction  # Legacy model


class NPCExtractionService:
    """Service for extracting NPC data with unified pipeline persistence."""

    def __init__(
        self,
        extractor: RawNPCExtractor | None = None,
        database: DatabaseManager | None = None,
        force_refresh: bool = False,
        use_dspy_images: bool = False,
    ):
        """Initialize the extraction service."""
        self.extractor = extractor or MarkdownNPCExtractor(use_dspy_images=use_dspy_images)
        self.database = database or DatabaseManager()
        self.force_refresh = force_refresh
        self.logger = get_logger(__name__)

    async def extract_npc(self, npc_id: int) -> NPCExtraction:
        """Extract NPC raw data and store in unified model."""
        # Ensure database tables exist
        try:
            await self.database.create_tables()
        except Exception as e:
            self.logger.error("Failed to create database tables", error=str(e))
            raise

        # Check cache first (unless force refresh)
        if not self.force_refresh:
            cached = await self.database.get_cached_extraction(npc_id)
            if cached and cached.has_stage(ExtractionStage.RAW):
                self.logger.info(
                    "Using cached raw extraction",
                    npc_id=npc_id,
                    npc_name=cached.npc_name,
                    cached_at=cached.last_updated,
                    completion=f"{cached.completion_percentage:.1f}%"
                )
                return cached

        # Extract fresh raw data using legacy extractor
        self.logger.info("Extracting fresh NPC raw data", npc_id=npc_id)
        legacy_extraction = await self.extractor.extract(npc_id)
        
        # Convert legacy model to new unified model
        raw_data = NPCRawExtractionData(
            wiki_url=legacy_extraction.wiki_url,
            raw_markdown=legacy_extraction.raw_markdown,
            chathead_image_url=legacy_extraction.chathead_image_url,
            image_url=legacy_extraction.image_url,
            extraction_success=legacy_extraction.extraction_success,
            error_message=legacy_extraction.error_message,
            markdown_length=len(legacy_extraction.raw_markdown)
        )
        
        # Save using new database methods (convert Pydantic to dict)
        unified_extraction = await self.database.save_raw_data(
            npc_id=npc_id,
            npc_name=legacy_extraction.npc_name,
            raw_data=raw_data.model_dump(),  # Convert Pydantic to dict
            npc_variant=None  # TODO: Extract from legacy if available
        )
        
        self.logger.info(
            "Raw extraction completed and cached",
            npc_id=npc_id,
            npc_name=unified_extraction.npc_name,
            success=raw_data.extraction_success,
            markdown_length=raw_data.markdown_length,
            completion=f"{unified_extraction.completion_percentage:.1f}%"
        )
        
        return unified_extraction

    async def get_extraction_status(self, npc_id: int) -> dict:
        """Get detailed status of an NPC extraction pipeline."""
        extraction = await self.database.get_cached_extraction(npc_id)
        
        if not extraction:
            return {
                "npc_id": npc_id,
                "cached": False,
                "completion_percentage": 0.0,
                "completed_stages": [],
                "npc_name": None
            }

        raw_success = extraction.raw_data.get("extraction_success", False) if extraction.raw_data else False
        
        return {
            "npc_id": npc_id,
            "npc_name": extraction.npc_name,
            "npc_variant": extraction.npc_variant,
            "cached": True,
            "completion_percentage": extraction.completion_percentage,
            "completed_stages": [stage.value for stage in extraction.completed_stages],
            "last_updated": extraction.last_updated,
            "overall_confidence": extraction.overall_confidence,
            # Raw data status
            "raw_extraction_success": raw_success,
            "has_markdown": bool(extraction.raw_data and extraction.raw_data.get("raw_markdown")),
            "has_chathead": bool(extraction.raw_data and extraction.raw_data.get("chathead_image_url")),
            "has_image": bool(extraction.raw_data and extraction.raw_data.get("image_url")),
            "markdown_length": extraction.raw_data.get("markdown_length", 0) if extraction.raw_data else 0,
            # Pipeline stages
            "has_text_analysis": extraction.has_stage(ExtractionStage.TEXT),
            "has_visual_analysis": extraction.has_stage(ExtractionStage.VISUAL),
            "has_character_profile": extraction.has_stage(ExtractionStage.PROFILE),
        }

    async def clear_cache(self) -> None:
        """Clear all cached extractions."""
        await self.database.clear_cache()
        self.logger.info("Cleared all cached extractions")

    async def close(self) -> None:
        """Close the service and clean up resources."""
        await self.database.close()
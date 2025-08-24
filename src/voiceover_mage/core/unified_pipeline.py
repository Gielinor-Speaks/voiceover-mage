# ABOUTME: Unified pipeline service that coordinates all extraction stages
# ABOUTME: Manages database persistence and stage progression for NPC processing

from typing import cast

from voiceover_mage.core.models import ExtractionStage, NPCWikiSourcedData
from voiceover_mage.core.service import NPCExtractionService
from voiceover_mage.extraction.analysis.image import NPCVisualCharacteristics
from voiceover_mage.extraction.analysis.intelligent import NPCIntelligentExtractor
from voiceover_mage.extraction.analysis.synthesizer import NPCDetails
from voiceover_mage.extraction.analysis.text import NPCTextCharacteristics
from voiceover_mage.extraction.wiki.crawl4ai import Crawl4AINPCExtractor
from voiceover_mage.persistence.manager import DatabaseManager
from voiceover_mage.persistence.models import NPCRawExtraction
from voiceover_mage.utils.logging import get_logger


class UnifiedPipelineService:
    """Unified service that coordinates all NPC extraction and analysis stages.

    This service manages the complete pipeline:
    1. Raw extraction (basic markdown + images)
    2. Intelligent extraction (text + visual analysis)
    3. Synthesis (character profile generation)

    Each stage is saved to the database with proper tracking.
    """

    def __init__(
        self,
        database: DatabaseManager | None = None,
        force_refresh: bool = False,
        api_key: str | None = None,
    ):
        """Initialize the unified pipeline service.

        Args:
            database: Database manager (defaults to new DatabaseManager)
            force_refresh: If True, bypass cache and extract fresh data
            api_key: API key for LLM-based extraction (Crawl4AI)
        """
        self.database = database or DatabaseManager()
        self.force_refresh = force_refresh
        self.api_key = api_key
        self.logger = get_logger(__name__)

        # Initialize extraction services
        self.raw_service = NPCExtractionService(database=self.database, force_refresh=force_refresh)
        self.intelligent_extractor = NPCIntelligentExtractor()

    async def run_full_pipeline(self, npc_id: int) -> NPCRawExtraction:
        """Run the complete extraction pipeline for an NPC.

        Args:
            npc_id: The NPC ID to process

        Returns:
            The complete extraction with all stages processed
        """
        self.logger.info("Starting unified pipeline", npc_id=npc_id)

        # Ensure database tables exist
        await self.database.create_tables()

        # Stage 1: Raw extraction (basic markdown + images)
        extraction = await self._run_raw_extraction(npc_id)

        # Stage 2: LLM-based extraction using Crawl4AI
        if self.api_key:
            extraction = await self._run_llm_extraction(extraction)

        # Stage 3: Intelligent analysis (text + visual) - only if we have raw markdown
        self.logger.info(
            "Checking intelligent analysis prerequisites",
            npc_id=npc_id,
            has_markdown=bool(extraction.raw_markdown),
            markdown_length=len(extraction.raw_markdown) if extraction.raw_markdown else 0,
        )
        if extraction.raw_markdown:
            self.logger.info("Starting intelligent analysis stage", npc_id=npc_id)
            extraction = await self._run_intelligent_analysis(extraction)
        else:
            self.logger.warning("Skipping intelligent analysis - no markdown content", npc_id=npc_id)

        # Stage 4: Synthesis is now handled within the intelligent analysis stage
        # No separate synthesis needed since NPCIntelligentExtractor does everything

        self.logger.info(
            "Pipeline completed",
            npc_id=npc_id,
            npc_name=extraction.npc_name,
            completed_stages=extraction.completed_stages,
        )

        return extraction

    async def _run_raw_extraction(self, npc_id: int) -> NPCRawExtraction:
        """Stage 1: Basic raw extraction."""
        self.logger.info("Running raw extraction stage", npc_id=npc_id)

        # Use existing NPCExtractionService for raw extraction
        extraction = await self.raw_service.extract_npc(npc_id)

        # Mark stage as complete
        extraction.add_stage(ExtractionStage.RAW)
        await self._save_extraction(extraction)

        self.logger.info("Raw extraction complete", npc_id=npc_id, markdown_length=len(extraction.raw_markdown))

        return extraction

    async def _run_llm_extraction(self, extraction: NPCRawExtraction) -> NPCRawExtraction:
        """Stage 2: LLM-based extraction using Crawl4AI."""
        if not self.api_key:
            self.logger.warning("Skipping LLM extraction - no API key provided")
            return extraction

        self.logger.info("Running LLM extraction stage", npc_id=extraction.npc_id)

        try:
            # Use Crawl4AI extractor for structured data
            crawl_extractor = Crawl4AINPCExtractor(api_key=self.api_key)
            wiki_data: NPCWikiSourcedData = await crawl_extractor.extract_npc_data(extraction.npc_id)

            # Convert to dict for storage
            extraction.raw_data = wiki_data.model_dump()
            extraction.add_stage(ExtractionStage.TEXT)
            await self._save_extraction(extraction)

            self.logger.info("LLM extraction complete", npc_id=extraction.npc_id, npc_name=wiki_data.name.value)
        except Exception as e:
            import traceback

            self.logger.error(
                "LLM extraction failed",
                npc_id=extraction.npc_id,
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc(),
            )
            # Continue pipeline even if LLM extraction fails

        return extraction

    async def _run_intelligent_analysis(self, extraction: NPCRawExtraction) -> NPCRawExtraction:
        """Stage 3: Intelligent text and visual analysis."""
        self.logger.info(
            "Running intelligent analysis stage", npc_id=extraction.npc_id, markdown_length=len(extraction.raw_markdown)
        )

        try:
            # Run individual text and image extraction to capture intermediate results
            text_characteristics = cast(
                NPCTextCharacteristics,
                self.intelligent_extractor.text_extractor(
                    markdown_content=extraction.raw_markdown, npc_name=extraction.npc_name
                ),
            )

            image_characteristics = cast(
                NPCVisualCharacteristics,
                self.intelligent_extractor.image_extractor(
                    markdown_content=extraction.raw_markdown, npc_name=extraction.npc_name
                ),
            )

            # Store intermediate analysis results
            extraction.text_analysis = text_characteristics.model_dump()
            extraction.visual_analysis = image_characteristics.model_dump()

            # Synthesize into final profile
            npc_details = cast(
                NPCDetails,
                self.intelligent_extractor.synthesizer(
                    text_characteristics=text_characteristics,
                    visual_characteristics=image_characteristics,
                    npc_name=extraction.npc_name,
                ),
            )

            # Store the synthesized character profile
            extraction.character_profile = npc_details.model_dump()

            # Mark stages complete
            extraction.add_stage(ExtractionStage.TEXT)
            extraction.add_stage(ExtractionStage.VISUAL)
            extraction.add_stage(ExtractionStage.SYNTHESIS)
            extraction.add_stage(ExtractionStage.PROFILE)
            extraction.add_stage(ExtractionStage.COMPLETE)
            await self._save_extraction(extraction)

            self.logger.info(
                "Intelligent analysis complete - character profile generated",
                npc_id=extraction.npc_id,
                personality_traits=npc_details.personality_traits[:100] if npc_details.personality_traits else "None",
                occupation=npc_details.occupation,
                overall_confidence=npc_details.overall_confidence,
            )
        except Exception as e:
            import traceback

            self.logger.error(
                "Intelligent analysis failed",
                npc_id=extraction.npc_id,
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc(),
            )
            # Continue pipeline even if analysis fails

        return extraction

    async def _save_extraction(self, extraction: NPCRawExtraction) -> NPCRawExtraction:
        """Save extraction to database."""
        async with self.database.async_session() as session:
            # Merge to update existing record
            merged = await session.merge(extraction)
            await session.commit()
            await session.refresh(merged)
            return merged

    async def get_extraction_status(self, npc_id: int) -> dict:
        """Get the current status of an extraction."""
        extraction = await self.database.get_cached_extraction(npc_id)

        if not extraction:
            return {"npc_id": npc_id, "exists": False, "completed_stages": [], "has_character_profile": False}

        return {
            "npc_id": npc_id,
            "exists": True,
            "npc_name": extraction.npc_name,
            "completed_stages": extraction.completed_stages,
            "has_raw_data": bool(extraction.raw_data),
            "has_text_analysis": bool(extraction.text_analysis),
            "has_visual_analysis": bool(extraction.visual_analysis),
            "has_character_profile": bool(extraction.character_profile),
            "is_complete": ExtractionStage.COMPLETE.value in extraction.completed_stages,
        }

    async def close(self) -> None:
        """Close the service and clean up resources."""
        await self.raw_service.close()

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
from voiceover_mage.utils.retry import LLMAPIError, llm_retry


class UnifiedPipelineService:
    """Unified service that coordinates all NPC extraction and analysis stages.

    This service manages the complete pipeline:
    1. Raw extraction (basic markdown + images) → NPCWikiSourcedData
    2. Intelligent extraction (text + visual analysis) → NPCTextCharacteristics + NPCVisualCharacteristics
    3. Synthesis (character profile generation) → NPCDetails

    Each stage uses TypeAdapter for type-safe JSON database storage.
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

            # Store NPCWikiSourcedData directly with TypeAdapter
            extraction.raw_data = wiki_data
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
            # Run text and image analysis with retry logic
            text_characteristics = await self._run_text_analysis_with_retry(
                extraction.raw_markdown, extraction.npc_name
            )

            image_characteristics = await self._run_image_analysis_with_retry(
                extraction.raw_markdown, extraction.npc_name
            )

            # Store analysis results directly with TypeAdapter
            extraction.text_analysis = text_characteristics
            extraction.visual_analysis = image_characteristics

            # Synthesize into final profile with retry logic
            npc_details = await self._run_synthesis_with_retry(
                text_characteristics, image_characteristics, extraction.npc_name
            )

            # Store the synthesized character profile directly with TypeAdapter
            extraction.character_profile = npc_details

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
        except LLMAPIError as e:
            # Handle LLM-specific errors with appropriate logging
            self.logger.error(
                "LLM API failure during intelligent analysis",
                npc_id=extraction.npc_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Continue pipeline - don't fail completely on LLM errors
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

    @llm_retry(max_attempts=3, with_rate_limiting=True, with_circuit_breaker=True)
    async def _run_text_analysis_with_retry(self, markdown: str, npc_name: str) -> NPCTextCharacteristics:
        """Run text analysis with retry logic."""
        self.logger.debug("Running text analysis with retry protection", npc_name=npc_name)

        # Run synchronously but wrap in async for retry decorator
        import asyncio

        loop = asyncio.get_event_loop()

        result = await loop.run_in_executor(
            None, lambda: self.intelligent_extractor.text_extractor(markdown_content=markdown, npc_name=npc_name)
        )

        return cast(NPCTextCharacteristics, result)

    @llm_retry(max_attempts=3, with_rate_limiting=True, with_circuit_breaker=True)
    async def _run_image_analysis_with_retry(self, markdown: str, npc_name: str) -> NPCVisualCharacteristics:
        """Run image analysis with retry logic."""
        self.logger.debug("Running image analysis with retry protection", npc_name=npc_name)

        # Run synchronously but wrap in async for retry decorator
        import asyncio

        loop = asyncio.get_event_loop()

        result = await loop.run_in_executor(
            None, lambda: self.intelligent_extractor.image_extractor(markdown_content=markdown, npc_name=npc_name)
        )

        return cast(NPCVisualCharacteristics, result)

    @llm_retry(max_attempts=3, with_rate_limiting=True, with_circuit_breaker=True)
    async def _run_synthesis_with_retry(
        self,
        text_characteristics: NPCTextCharacteristics,
        image_characteristics: NPCVisualCharacteristics,
        npc_name: str,
    ) -> NPCDetails:
        """Run character synthesis with retry logic."""
        self.logger.debug("Running synthesis with retry protection", npc_name=npc_name)

        # Run synchronously but wrap in async for retry decorator
        import asyncio

        loop = asyncio.get_event_loop()

        result = await loop.run_in_executor(
            None,
            lambda: self.intelligent_extractor.synthesizer(
                text_characteristics=text_characteristics,
                visual_characteristics=image_characteristics,
                npc_name=npc_name,
            ),
        )

        return cast(NPCDetails, result)

    async def _save_extraction(self, extraction: NPCRawExtraction) -> NPCRawExtraction:
        """Save extraction to database."""
        return await self.database.save_extraction(extraction)

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

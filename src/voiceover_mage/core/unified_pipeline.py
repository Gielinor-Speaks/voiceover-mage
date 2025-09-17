# ABOUTME: Unified pipeline service that coordinates all extraction stages
# ABOUTME: Manages database persistence and stage progression for NPC processing

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from voiceover_mage.core.models import NPCProfile, NPCWikiSourcedData
from voiceover_mage.core.service import NPCExtractionService
from voiceover_mage.extraction.analysis.image import NPCVisualCharacteristics
from voiceover_mage.extraction.analysis.intelligent import NPCIntelligentExtractor
from voiceover_mage.extraction.analysis.synthesizer import NPCDetails
from voiceover_mage.extraction.analysis.text import NPCTextCharacteristics
from voiceover_mage.extraction.voice.elevenlabs import ElevenLabsVoicePromptGenerator
from voiceover_mage.extraction.wiki.crawl4ai import Crawl4AINPCExtractor
from voiceover_mage.persistence import NPCPipelineState
from voiceover_mage.persistence.manager import DatabaseManager
from voiceover_mage.services.voice.elevenlabs import ElevenLabsVoiceService
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
        # Initialize voice services
        self.voice_prompt_generator = ElevenLabsVoicePromptGenerator()
        self.voice_service = ElevenLabsVoiceService()
        self.pipeline_version = "1"

    async def run_full_pipeline(self, npc_id: int) -> NPCPipelineState:
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
        state = await self._run_raw_extraction(npc_id)

        # Stage 2: LLM-based extraction using Crawl4AI
        if self.api_key:
            state = await self._run_llm_extraction(state)

        # Stage 3: Intelligent analysis (text + visual) - only if we have raw markdown
        self.logger.info(
            "Checking intelligent analysis prerequisites",
            npc_id=npc_id,
            has_markdown=bool(state.raw_markdown),
            markdown_length=len(state.raw_markdown) if state.raw_markdown else 0,
        )
        if state.raw_markdown:
            self.logger.info("Starting intelligent analysis stage", npc_id=npc_id)
            state = await self._run_intelligent_analysis(state)
        else:
            self.logger.warning("Skipping intelligent analysis - no markdown content", npc_id=npc_id)

        # Stage 4: Synthesis is now handled within the intelligent analysis stage
        # No separate synthesis needed since NPCIntelligentExtractor does everything

        # Stage 5: Voice generation (preview sample)
        try:
            state = await self._run_voice_generation(state)
        except Exception as e:
            self.logger.error(
                "Voice generation stage failed",
                npc_id=npc_id,
                error=str(e),
                error_type=type(e).__name__,
            )

        self.logger.info(
            "Pipeline completed",
            npc_id=npc_id,
            npc_name=state.npc_name,
            completed_stages=state.completed_stages,
            stage_flags=state.stage_flags,
        )

        return state

    def _map_details_to_profile(self, npc_id: int, npc_name: str, details: NPCDetails) -> NPCProfile:
        """Map synthesized NPCDetails to NPCProfile for voice generation."""
        # Heuristic mapping based on available fields
        personality = details.personality_traits or ""
        voice_desc = (
            f"{details.dialogue_patterns}. Age category: {details.age_category}. "
            f"Tone hints from visual archetype: {details.visual_archetype}."
        ).strip()
        age_range = details.age_category or "Unknown"
        emotional_profile = details.emotional_range or "Neutral"
        character_archetype = details.social_role or details.visual_archetype or ""
        speaking_style = details.dialogue_patterns or ""
        confidence_score = details.overall_confidence or 0.0
        generation_notes = details.synthesis_notes or ""

        return NPCProfile(
            id=npc_id,
            npc_name=npc_name,
            personality=personality,
            voice_description=voice_desc,
            age_range=age_range,
            emotional_profile=emotional_profile,
            character_archetype=character_archetype,
            speaking_style=speaking_style,
            confidence_score=confidence_score,
            generation_notes=generation_notes,
        )

    async def _run_voice_generation(self, state: NPCPipelineState) -> NPCPipelineState:
        """Stage: Generate a preview voice sample and persist metadata."""
        if not state.character_profile:
            self.logger.info("Skipping voice generation - no character profile", npc_id=state.id)
            return state

        details = state.character_profile
        profile = self._map_details_to_profile(state.id, state.npc_name, details)

        # Generate descriptive prompt
        voice_description = await self.voice_prompt_generator.aforward(profile)

        self.logger.info("Generated voice prompt", npc_id=state.id, voice_description=voice_description)

        # Call provider and save audio clips
        audio_clips = await self.voice_service.generate_preview_audio(
            voice_description=voice_description.get("description"), sample_text=voice_description.get("sample_text")
        )

        # audio_bytes is a tuple of bytes, we should iterate over each until it is exhausted
        out_dir = Path("data/voice_previews")
        out_dir.mkdir(parents=True, exist_ok=True)

        last_out_path: Path | None = None
        for i, audio in enumerate(audio_clips):
            out_path = out_dir / f"{state.id}_preview_{i + 1}.mp3"
            with open(out_path, "wb") as f:
                f.write(audio)
            self.logger.info("Saved voice preview", npc_id=state.id, sample_path=str(out_path))
            last_out_path = out_path

            # Persist to database as a voice sample
            try:
                await self.database.create_voice_preview(
                    npc_id=state.id,
                    voice_prompt=voice_description.get("description", ""),
                    sample_text=voice_description.get("sample_text", ""),
                    provider="elevenlabs",
                    model="text_to_voice.design:eleven_ttv_v3",
                    audio_path=str(out_path),
                    audio_bytes=audio,
                    is_representative=False,
                    generation_metadata={
                        "model_id": "eleven_ttv_v3",
                        "preview_index": i + 1,
                        "total_previews": len(audio_clips),
                    },
                )
            except Exception as e:
                self.logger.error(
                    "Failed to persist voice sample",
                    npc_id=state.id,
                    error=str(e),
                    error_type=type(e).__name__,
                    sample_index=i + 1,
                )
        # Mark voice generation stage complete
        updated_state = await self.database.get_cached_extraction(state.id)
        if updated_state:
            self.logger.info(
                "Voice generation complete",
                npc_id=updated_state.id,
                sample_path=str(last_out_path) if last_out_path else None,
                samples=len(audio_clips),
                stage_flags=updated_state.stage_flags,
            )
            return updated_state

        return state

    async def _run_raw_extraction(self, npc_id: int) -> NPCPipelineState:
        """Stage 1: Basic raw extraction."""
        self.logger.info("Running raw extraction stage", npc_id=npc_id)

        # Use existing NPCExtractionService for raw extraction
        state = await self.raw_service.extract_npc(npc_id)

        self.logger.info(
            "Raw extraction complete",
            npc_id=npc_id,
            markdown_length=len(state.raw_markdown),
            stage_flags=state.stage_flags,
        )

        return state

    async def _run_llm_extraction(self, state: NPCPipelineState) -> NPCPipelineState:
        """Stage 2: LLM-based extraction using Crawl4AI."""
        if not self.api_key:
            self.logger.warning("Skipping LLM extraction - no API key provided")
            return state

        self.logger.info("Running LLM extraction stage", npc_id=state.id)

        try:
            # Use Crawl4AI extractor for structured data
            crawl_extractor = Crawl4AINPCExtractor(api_key=self.api_key)
            wiki_data: NPCWikiSourcedData = await crawl_extractor.extract_npc_data(state.id)

            structured_checksum = hashlib.sha256(wiki_data.model_dump_json().encode("utf-8")).hexdigest()

            await self.database.upsert_wiki_snapshot(
                npc_id=state.id,
                raw_markdown=state.raw_markdown,
                chathead_image_url=state.chathead_image_url,
                image_url=state.image_url,
                raw_data=wiki_data,
                source_checksum=structured_checksum,
                fetched_at=state.fetched_at or datetime.now(UTC),
                extraction_success=state.extraction_success,
                error_message=state.error_message,
            )

            updated_state = await self.database.get_cached_extraction(state.id)

            if updated_state:
                self.logger.info(
                    "LLM extraction complete",
                    npc_id=updated_state.id,
                    npc_name=wiki_data.name.value,
                    stage_flags=updated_state.stage_flags,
                )
                return updated_state
        except Exception as e:
            import traceback

            self.logger.error(
                "LLM extraction failed",
                npc_id=state.id,
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc(),
            )
            # Continue pipeline even if LLM extraction fails
        return state

    async def _run_intelligent_analysis(self, state: NPCPipelineState) -> NPCPipelineState:
        """Stage 3: Intelligent text and visual analysis."""
        self.logger.info(
            "Running intelligent analysis stage", npc_id=state.id, markdown_length=len(state.raw_markdown)
        )

        try:
            # Run intelligent extraction with full pipeline retry logic
            # This uses the new aforward() method with parallel processing and native DSPy async
            (
                npc_details,
                text_characteristics,
                image_characteristics,
            ) = await self._run_intelligent_extraction_with_retry(state)

            await self.database.upsert_character_profile(
                npc_id=state.id,
                profile=npc_details,
                text_analysis=text_characteristics,
                visual_analysis=image_characteristics,
                pipeline_version=self.pipeline_version,
            )

            updated_state = await self.database.get_cached_extraction(state.id)

            if updated_state:
                self.logger.info(
                    "Intelligent analysis complete - character profile generated",
                    npc_id=updated_state.id,
                    personality_traits=(
                        npc_details.personality_traits[:100] if npc_details.personality_traits else "None"
                    ),
                    occupation=npc_details.occupation,
                    overall_confidence=npc_details.overall_confidence,
                    stage_flags=updated_state.stage_flags,
                )
                return updated_state
        except LLMAPIError as e:
            # Handle LLM-specific errors with appropriate logging
            self.logger.error(
                "LLM API failure during intelligent analysis",
                npc_id=state.id,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Continue pipeline - don't fail completely on LLM errors
        except Exception as e:
            import traceback

            self.logger.error(
                "Intelligent analysis failed",
                npc_id=state.id,
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc(),
            )
            # Continue pipeline even if analysis fails

        return state

    @llm_retry(max_attempts=3, with_rate_limiting=True, with_circuit_breaker=True)
    async def _run_text_analysis_with_retry(self, markdown: str, npc_name: str) -> NPCTextCharacteristics:
        """Run text analysis with retry logic."""
        self.logger.debug("Running text analysis with retry protection", npc_name=npc_name)

        result = await self.intelligent_extractor.text_extractor.acall(markdown_content=markdown, npc_name=npc_name)

        return cast(NPCTextCharacteristics, result)

    @llm_retry(max_attempts=3, with_rate_limiting=True, with_circuit_breaker=True)
    async def _run_image_analysis_with_retry(self, markdown: str, npc_name: str) -> NPCVisualCharacteristics:
        """Run image analysis with retry logic."""
        self.logger.debug("Running image analysis with retry protection", npc_name=npc_name)

        result = await self.intelligent_extractor.image_extractor.acall(markdown_content=markdown, npc_name=npc_name)

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

        result = await self.intelligent_extractor.synthesizer.acall(
            text_characteristics=text_characteristics,
            visual_characteristics=image_characteristics,
            npc_name=npc_name,
        )

        return cast(NPCDetails, result)

    @llm_retry(max_attempts=3, with_rate_limiting=True, with_circuit_breaker=True)
    async def _run_intelligent_extraction_with_retry(
        self, state: NPCPipelineState
    ) -> tuple[NPCDetails, NPCTextCharacteristics, NPCVisualCharacteristics]:
        """Run the complete intelligent extraction pipeline with retry logic.

        This method uses the main intelligent extractor's aforward() method which handles
        parallel processing internally, eliminating duplicate logic.

        Returns:
            Tuple of (npc_details, text_characteristics, image_characteristics)
        """
        self.logger.debug("Running intelligent extraction with retry protection", npc_name=state.npc_name)

        # Use the main intelligent extractor which handles parallel processing
        npc_details = await self.intelligent_extractor.aforward(state)

        # For backward compatibility, we need the intermediate results too
        # Since we can't easily get them from the unified call, we'll extract them from the final result
        # This is a bit of a hack, but maintains API compatibility

        # Create mock intermediate results from the final result
        # In a real implementation, these would come from the actual extraction steps
        from voiceover_mage.extraction.analysis.image import NPCVisualCharacteristics
        from voiceover_mage.extraction.analysis.text import NPCTextCharacteristics

        text_characteristics = NPCTextCharacteristics(
            personality_traits=npc_details.personality_traits,
            occupation=npc_details.occupation,
            social_role=npc_details.social_role,
            dialogue_patterns=npc_details.dialogue_patterns,
            emotional_range=npc_details.emotional_range,
            background_lore=npc_details.background_lore,
            confidence_score=npc_details.text_confidence,
            reasoning="Extracted from unified pipeline",
        )

        image_characteristics = NPCVisualCharacteristics(
            chathead_image_url=npc_details.chathead_image_url,
            image_url=npc_details.image_url,
            age_category=npc_details.age_category,
            build_type=npc_details.build_type,
            attire_style=npc_details.attire_style,
            distinctive_features=npc_details.distinctive_features,
            color_palette=npc_details.color_palette,
            visual_archetype=npc_details.visual_archetype,
            confidence_score=npc_details.visual_confidence,
            reasoning="Extracted from unified pipeline",
        )

        return (
            cast(NPCDetails, npc_details),
            cast(NPCTextCharacteristics, text_characteristics),
            cast(NPCVisualCharacteristics, image_characteristics),
        )

    async def get_extraction_status(self, id: int) -> dict:
        """Get the current status of an extraction."""
        extraction = await self.database.get_cached_extraction(id)

        if not extraction:
            return {"npc_id": id, "exists": False, "completed_stages": [], "has_character_profile": False}

        return {
            "npc_id": id,
            "exists": True,
            "npc_name": extraction.npc_name,
            "completed_stages": extraction.completed_stages,
            "has_raw_data": bool(extraction.raw_data),
            "has_text_analysis": bool(extraction.text_analysis),
            "has_visual_analysis": bool(extraction.visual_analysis),
            "has_character_profile": bool(extraction.character_profile),
            "stage_flags": extraction.stage_flags,
            "is_complete": "complete" in extraction.completed_stages,
        }

    async def close(self) -> None:
        """Close the service and clean up resources."""
        await self.raw_service.close()

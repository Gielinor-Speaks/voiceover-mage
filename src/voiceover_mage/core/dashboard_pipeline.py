# ABOUTME: Pipeline wrapper that provides dashboard integration with real-time stage updates
# ABOUTME: Bridges the unified pipeline with the enhanced progress dashboard for live reporting

from voiceover_mage.config import get_config
from voiceover_mage.core.unified_pipeline import UnifiedPipelineService
from voiceover_mage.persistence import NPCPipelineState
from voiceover_mage.utils.logging.enhanced_progress import PipelineDashboard, PipelineStage, StageStatus


class DashboardIntegratedPipeline:
    """Wrapper around UnifiedPipelineService that provides dashboard integration."""

    def __init__(self, pipeline_service: UnifiedPipelineService):
        self.pipeline_service = pipeline_service

    async def run_full_pipeline_with_dashboard(self, npc_id: int, dashboard: PipelineDashboard) -> NPCPipelineState:
        """Run the complete pipeline with live dashboard updates."""
        config = get_config()

        # Stage 1: Raw extraction
        dashboard.start_stage(PipelineStage.RAW_EXTRACTION)
        try:
            state = await self.pipeline_service._run_raw_extraction(npc_id)

            # Circuit breaker: Check if extraction was successful
            if not state.extraction_success:
                error_msg = state.error_message or "Raw data extraction failed - no valid NPC data found"
                dashboard.error_stage(PipelineStage.RAW_EXTRACTION, error_msg)
                raise ValueError(f"Invalid NPC {npc_id}: {error_msg}")

            # Circuit breaker: Check if we have meaningful content
            has_content = bool(state.raw_markdown and state.raw_markdown.strip())
            has_structured_data = bool(state.raw_data)

            # Enhanced validation: Check for garbage/invalid pages
            if has_content:
                markdown_lower = state.raw_markdown.lower()

                # Check if NPC redirected to homepage or main wiki page
                wiki_url = state.wiki_url.lower() if state.wiki_url else ""

                is_homepage_redirect = (
                    wiki_url == "https://oldschool.runescape.wiki/"  # Exact homepage URL
                    or "oldschool.runescape.wiki/w/old_school_runescape" in wiki_url
                    or wiki_url.endswith("/wiki")
                    or wiki_url.endswith("/wiki/")
                    or "/w/main_page" in wiki_url
                    or "/w/runescape:about" in wiki_url
                )

                # Detect common garbage page indicators
                garbage_indicators = [
                    "page not found",
                    "404 error",
                    "no results found",
                    "search results",
                    "did you mean:",
                    "page does not exist",
                    "article not found",
                    "redirect notice",
                    "the requested page could not be found",
                ]

                # Check for NPC-specific content (more specific indicators)
                npc_content_indicators = [
                    "combat level:",
                    "hitpoints:",
                    "examine:",
                    "attack style:",
                    "weakness:",
                    "poisonous:",
                    "aggressive:",
                    "slayer level",
                    "slayer category",
                ]

                # Check for valid NPC page structure
                valid_npc_structure = [
                    "combat stats",
                    "drop table",
                    "location",
                    "dialogue",
                    "quest involvement",
                ]

                has_garbage_indicators = any(indicator in markdown_lower for indicator in garbage_indicators)
                has_npc_content = any(indicator in markdown_lower for indicator in npc_content_indicators)
                has_valid_structure = any(indicator in markdown_lower for indicator in valid_npc_structure)

                # Also check content quality - real NPC pages should have substantial unique content
                content_length = len(state.raw_markdown.strip())
                unique_lines = len(set(line.strip() for line in state.raw_markdown.split("\n") if line.strip()))
                content_diversity = unique_lines / max(content_length / 100, 1)  # Rough diversity metric

                # Comprehensive validation for invalid NPCs - based on content and URL redirects
                is_likely_invalid = (
                    has_garbage_indicators
                    or is_homepage_redirect  # NPC redirected to homepage = doesn't exist
                    or (
                        not has_npc_content
                        and not has_valid_structure
                        and content_diversity < config.content_diversity_threshold
                    )
                )

                if is_likely_invalid:
                    # Determine specific reason for better error messaging
                    if is_homepage_redirect:
                        reason = f"NPC redirected to homepage/main page (URL: {state.wiki_url})"
                    elif has_garbage_indicators:
                        reason = "Page contains 404/search result indicators"
                    else:
                        reason = (
                            f"Low content diversity ({content_diversity:.2f} < {config.content_diversity_threshold}) "
                            "with no NPC-specific content"
                        )

                    error_msg = f"Invalid NPC page detected: {reason}"
                    dashboard.error_stage(PipelineStage.RAW_EXTRACTION, error_msg)
                    raise ValueError(f"Invalid NPC {npc_id}: {error_msg}")

            if not has_content and not has_structured_data:
                error_msg = "No meaningful content found - raw_markdown and raw_data are both empty"
                dashboard.error_stage(PipelineStage.RAW_EXTRACTION, error_msg)
                raise ValueError(f"Invalid NPC {npc_id}: {error_msg}")

            dashboard.complete_stage(
                PipelineStage.RAW_EXTRACTION,
                data={
                    "markdown_chars": len(state.raw_markdown) if state.raw_markdown else 0,
                    "has_images": bool(state.chathead_image_url or state.image_url),
                    "extraction_success": state.extraction_success,
                    "has_structured_data": has_structured_data,
                },
            )
        except Exception as e:
            dashboard.error_stage(PipelineStage.RAW_EXTRACTION, str(e))
            raise  # Re-raise the exception to maintain error handling

        # Stage 2: LLM extraction (if API key available)
        if self.pipeline_service.api_key:
            dashboard.start_stage(PipelineStage.LLM_EXTRACTION)
            try:
                # Store original state for comparison
                original_data_size = len(str(state.raw_data)) if state.raw_data else 0

                state = await self.pipeline_service._run_llm_extraction(state)

                # Circuit breaker: Check if LLM extraction actually enhanced the data
                enhanced_data_size = len(str(state.raw_data)) if state.raw_data else 0
                enhancement_ratio = enhanced_data_size / max(original_data_size, 1)  # Avoid division by zero

                # Consider it enhanced if data grew significantly or contains structured information
                has_meaningful_enhancement = (
                    enhancement_ratio > config.llm_enhancement_ratio  # Data size increased significantly
                    or enhanced_data_size > (config.min_enhanced_data_size * 2)  # Has substantial structured data
                    or (
                        state.raw_data
                        and hasattr(state.raw_data, "dialogue")
                        and getattr(state.raw_data, "dialogue", None)
                    )  # Has dialogue
                )

                if not has_meaningful_enhancement and enhanced_data_size < config.min_enhanced_data_size:
                    # LLM extraction didn't meaningfully enhance the data
                    error_msg = (
                        f"LLM extraction failed to enhance data meaningfully "
                        f"(original: {original_data_size}, enhanced: {enhanced_data_size})"
                    )
                    dashboard.error_stage(PipelineStage.LLM_EXTRACTION, error_msg)
                    return state

                dashboard.complete_stage(
                    PipelineStage.LLM_EXTRACTION,
                    data={
                        "enhanced": True,
                        "original_size": original_data_size,
                        "enhanced_size": enhanced_data_size,
                        "enhancement_ratio": enhancement_ratio,
                    },
                )
            except Exception as e:
                dashboard.error_stage(PipelineStage.LLM_EXTRACTION, str(e))
                return state
        else:
            dashboard.skip_stage(PipelineStage.LLM_EXTRACTION, "No API key provided")

        # Stage 3: Intelligent analysis (if we have content)
        if state.raw_markdown:
            dashboard.start_stage(PipelineStage.INTELLIGENT_ANALYSIS)
            try:
                state = await self.pipeline_service._run_intelligent_analysis(state)

                # Circuit breaker: Check confidence threshold
                if state.character_profile:
                    confidence = getattr(state.character_profile, "overall_confidence", 0)

                    # Validate confidence meets minimum threshold
                    if confidence < config.confidence_threshold:
                        error_msg = (
                            f"Character analysis confidence too low: {confidence:.1%} < "
                            f"{config.confidence_threshold:.1%}"
                        )
                        dashboard.error_stage(PipelineStage.INTELLIGENT_ANALYSIS, error_msg)
                        # Don't raise exception, just mark as error and continue to show the failure
                        return state

                    dashboard.complete_stage(PipelineStage.INTELLIGENT_ANALYSIS, data={"confidence": confidence})
                else:
                    # No character profile generated - this is also a failure
                    error_msg = "No character profile generated - insufficient character data"
                    dashboard.error_stage(PipelineStage.INTELLIGENT_ANALYSIS, error_msg)
                    return state

            except Exception as e:
                dashboard.error_stage(PipelineStage.INTELLIGENT_ANALYSIS, str(e))
                return state
        else:
            dashboard.skip_stage(PipelineStage.INTELLIGENT_ANALYSIS, "No content to analyze")

        # Stage 4: Voice generation
        # Circuit breaker: Check if previous stages succeeded and we have sufficient data
        analysis_stage = dashboard.stages.get(PipelineStage.INTELLIGENT_ANALYSIS)
        analysis_failed = analysis_stage and analysis_stage.status == StageStatus.ERROR

        # If analysis failed, skip voice generation
        if analysis_failed:
            dashboard.skip_stage(
                PipelineStage.VOICE_GENERATION,
                "Character analysis failed - cannot generate voice without sufficient character data",
            )
        else:
            # Additional data sufficiency checks
            has_character_profile = bool(state.character_profile)
            has_high_confidence = False

            if state.character_profile:
                confidence = getattr(state.character_profile, "overall_confidence", 0)
                has_high_confidence = confidence >= config.confidence_threshold

            has_markdown_content = bool(state.raw_markdown and len(state.raw_markdown.strip()) > 50)
            has_analysis = bool(state.text_analysis or state.visual_analysis)

            # Require either high-confidence character profile OR substantial fallback data
            if not (has_high_confidence or (has_character_profile and has_markdown_content) or has_analysis):
                dashboard.skip_stage(
                    PipelineStage.VOICE_GENERATION,
                    "Insufficient character data - need high-confidence profile or substantial fallback content",
                )
            else:
                dashboard.start_stage(PipelineStage.VOICE_GENERATION)
                try:
                    state = await self.pipeline_service._run_voice_generation(state)
                    # Count voice samples generated in this session
                    voice_samples = 3  # Default based on ElevenLabs implementation
                    dashboard.complete_stage(PipelineStage.VOICE_GENERATION, data={"voice_samples": voice_samples})
                except Exception as e:
                    dashboard.error_stage(PipelineStage.VOICE_GENERATION, str(e))

        return state

    async def close(self) -> None:
        """Close the underlying pipeline service."""
        await self.pipeline_service.close()

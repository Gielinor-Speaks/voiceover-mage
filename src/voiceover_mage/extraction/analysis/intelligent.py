# ABOUTME: Coordinating DSPy module that orchestrates text and visual extraction for Phase 2
# ABOUTME: Implements the NPCIntelligentExtractor from the Phase 2 design architecture


import dspy

from voiceover_mage.config import get_config
from voiceover_mage.persistence import NPCRawExtraction
from voiceover_mage.utils.logging import get_logger

from .image import ImageDetailExtractor
from .synthesizer import DetailSynthesizer, NPCDetails
from .text import TextDetailExtractor


def _configure_dspy_global_state():
    """Configure DSPy global state with Gemini LLM.

    Note: This intentionally modifies global DSPy state as required by DSPy architecture.
    DSPy modules require global LM configuration to function properly.
    """
    logger = get_logger(__name__)
    config = get_config()

    if config.gemini_api_key:
        lm = dspy.LM("gemini/gemini-2.5-flash", api_key=config.gemini_api_key)
        dspy.configure(lm=lm)
        logger.info("Configured DSPy with Gemini for intelligent extraction")
        return True
    else:
        logger.warning("No Gemini API key found - DSPy modules may fail")
        return False


class NPCIntelligentExtractor(dspy.Module):
    """Coordinating DSPy module for Phase 2 intelligent NPC extraction.

    This module implements the Phase 2 architecture:
    NPCRawExtraction (Phase 1 output)
        ↓
    NPCIntelligentExtractor (DSPy Module)
        ├── TextDetailExtractor (DSPy Module)    (analyzes markdown → text profile)
        └── ImageDetailExtractor (DSPy Module)   (analyzes markdown → visual profile)
        ↓
    DetailSynthesizer → NPCDetails (unified profile)
    """

    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)

        # Configure DSPy global state (explicit global side effect)
        self._dspy_configured = _configure_dspy_global_state()

        self.text_extractor = TextDetailExtractor()
        self.image_extractor = ImageDetailExtractor()
        self.synthesizer = DetailSynthesizer()

    def forward(self, raw_extraction: NPCRawExtraction) -> NPCDetails:
        """Sync wrapper around aforward() for backward compatibility.

        Args:
            raw_extraction: Phase 1 raw markdown and basic image URLs

        Returns:
            NPCDetails: Comprehensive character profile ready for voice generation
        """
        import asyncio

        return asyncio.run(self.aforward(raw_extraction))

    async def aforward(self, raw_extraction: NPCRawExtraction) -> NPCDetails:
        """True async version with parallel text/image extraction.

        This eliminates run_in_executor by using DSPy's native async support
        and runs text/image analysis in parallel for maximum performance.

        Args:
            raw_extraction: Phase 1 raw markdown and basic image URLs

        Returns:
            NPCDetails: Comprehensive character profile ready for voice generation
        """
        import asyncio

        # Run text and image extraction in parallel using asyncio.gather()
        # This is true concurrency, not thread-based like run_in_executor
        async def run_text_extraction():
            return await self.text_extractor.aforward(
                markdown_content=raw_extraction.raw_markdown, npc_name=raw_extraction.npc_name
            )

        async def run_image_extraction():
            return await self.image_extractor.aforward(
                markdown_content=raw_extraction.raw_markdown, npc_name=raw_extraction.npc_name
            )

        # Await both extractions in parallel - much faster than sequential
        text_characteristics, image_characteristics = await asyncio.gather(
            run_text_extraction(), run_image_extraction()
        )

        # Synthesize the results into unified profile
        npc_details = await self.synthesizer.aforward(
            text_characteristics=text_characteristics,
            visual_characteristics=image_characteristics,
            npc_name=raw_extraction.npc_name,
        )

        return npc_details

    async def extract_async(self, raw_extraction: NPCRawExtraction) -> NPCDetails:
        """Legacy async method - now delegates to aforward for compatibility."""
        return await self.aforward(raw_extraction)

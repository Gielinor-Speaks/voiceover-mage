# ABOUTME: Coordinating DSPy module that orchestrates text and visual extraction for Phase 2
# ABOUTME: Implements the NPCIntelligentExtractor from the Phase 2 design architecture

import asyncio
import dspy
from voiceover_mage.npc.persistence import NPCRawExtraction

from .image_extractor import ImageDetailExtractor
from .synthesizer import DetailSynthesizer, NPCDetails
from .text_extractor import TextDetailExtractor


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
        self.text_extractor = TextDetailExtractor()
        self.image_extractor = ImageDetailExtractor()
        self.synthesizer = DetailSynthesizer()
    
    def forward(self, raw_extraction: NPCRawExtraction) -> NPCDetails:
        """Transform raw extraction into intelligent NPC profile.
        
        Args:
            raw_extraction: Phase 1 raw markdown and basic image URLs
            
        Returns:
            NPCDetails: Comprehensive character profile ready for voice generation
        """
        # Run text and image extraction in parallel for efficiency
        # Both modules analyze the same markdown but extract different aspects
        text_characteristics = self.text_extractor(
            markdown_content=raw_extraction.raw_markdown,
            npc_name=raw_extraction.npc_name
        )
        
        image_characteristics = self.image_extractor(
            markdown_content=raw_extraction.raw_markdown,
            npc_name=raw_extraction.npc_name
        )
        
        # Synthesize into unified profile
        npc_details = self.synthesizer(
            text_characteristics=text_characteristics,
            visual_characteristics=image_characteristics, 
            npc_name=raw_extraction.npc_name
        )
        
        return npc_details
    
    async def extract_async(self, raw_extraction: NPCRawExtraction) -> NPCDetails:
        """Async version for potential future parallel processing."""
        # For now, run synchronously since DSPy modules aren't async
        # Future: Could run text/image extraction in parallel threads
        return self.forward(raw_extraction)
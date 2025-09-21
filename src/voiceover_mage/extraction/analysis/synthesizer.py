# ABOUTME: DSPy module for synthesizing text and visual characteristics into unified NPC profile
# ABOUTME: Resolves conflicts between different data sources and fills in missing information

from typing import cast

import dspy
from pydantic import BaseModel, Field

from .image import NPCVisualCharacteristics
from .text import NPCTextCharacteristics


class NPCDetails(BaseModel):
    """Unified NPC profile synthesizing text and visual characteristics."""

    # Basic information
    npc_name: str = Field(description="Name of the NPC")

    # Text-based characteristics
    personality_traits: str = Field(default="", description="Core personality traits from text analysis")
    occupation: str = Field(default="", description="NPC's role or job")
    social_role: str = Field(default="", description="Social position or archetype")
    dialogue_patterns: str = Field(default="", description="Speech patterns and mannerisms")
    emotional_range: str = Field(default="", description="Range of emotions expressed")
    background_lore: str = Field(default="", description="Background information and context")

    # Visual characteristics
    age_category: str = Field(default="", description="Apparent age category")
    build_type: str = Field(default="", description="Physical build")
    attire_style: str = Field(default="", description="Clothing and equipment styles")
    distinctive_features: str = Field(default="", description="Notable visual features")
    color_palette: str = Field(default="", description="Dominant colors in appearance")
    visual_archetype: str = Field(default="", description="Visual archetype")

    # Image URLs
    chathead_image_url: str | None = Field(default=None, description="Chathead image URL")
    image_url: str | None = Field(default=None, description="Main body image URL")

    # Synthesis metadata
    text_confidence: float = Field(default=0.0, description="Confidence in text extraction")
    visual_confidence: float = Field(default=0.0, description="Confidence in visual extraction")
    overall_confidence: float = Field(default=0.0, description="Overall synthesis confidence")
    synthesis_notes: str = Field(default="", description="Notes about conflicts or gaps resolved")


class DetailSynthesisSignature(dspy.Signature):
    """Synthesize text and visual NPC characteristics into a unified profile.

    Resolve conflicts between text and visual information, fill gaps through inference,
    and create a coherent character profile suitable for voice generation.
    """

    npc_name: str = dspy.InputField(description="Name of the NPC being synthesized")
    text_characteristics: str = dspy.InputField(
        description="JSON representation of text characteristics from dialogue and descriptions"
    )
    visual_characteristics: str = dspy.InputField(
        description="JSON representation of visual characteristics from images and descriptions"
    )

    personality_synthesis: str = dspy.OutputField(description="Synthesized personality combining text and visual cues")
    archetype_synthesis: str = dspy.OutputField(
        description="Unified character archetype (e.g., 'wise elderly wizard', 'gruff warrior')"
    )
    conflict_resolution: str = dspy.OutputField(
        description="How any conflicts between text and visual data were resolved"
    )
    gap_filling: str = dspy.OutputField(description="What missing information was inferred and how")
    confidence_assessment: float = dspy.OutputField(
        description="Overall confidence in the synthesized profile (0.0-1.0)"
    )


class DetailSynthesizer(dspy.Module):
    """DSPy module for intelligent synthesis of text and visual NPC characteristics.

    This module:
    1. Combines text and visual characteristics into a unified profile
    2. Resolves conflicts between different data sources
    3. Fills in missing information through intelligent inference
    4. Provides confidence scores for the synthesis quality
    """

    def __init__(self):
        super().__init__()
        self.synthesize = dspy.ChainOfThought(DetailSynthesisSignature)

    def forward(
        self,
        text_characteristics: NPCTextCharacteristics,
        visual_characteristics: NPCVisualCharacteristics,
        npc_name: str,
    ) -> NPCDetails:
        """Sync wrapper around aforward() for backward compatibility.

        Args:
            text_characteristics: Text-based personality and behavioral traits
            visual_characteristics: Visual appearance and image information
            npc_name: Name of the NPC

        Returns:
            NPCDetails with synthesized and unified character profile
        """
        import anyio

        return anyio.run(self.aforward, text_characteristics, visual_characteristics, npc_name)

    async def aforward(
        self,
        text_characteristics: NPCTextCharacteristics,
        visual_characteristics: NPCVisualCharacteristics,
        npc_name: str,
    ) -> NPCDetails:
        """Async version of forward for native DSPy async support.

        Args:
            text_characteristics: Text-based personality and behavioral traits
            visual_characteristics: Visual appearance and image information
            npc_name: Name of the NPC

        Returns:
            NPCDetails with synthesized and unified character profile
        """
        # Convert characteristics to JSON for the LM to process
        text_json = text_characteristics.model_dump_json()
        visual_json = visual_characteristics.model_dump_json()

        # Use DSPy's native async support for synthesis
        synthesis_result = cast(
            DetailSynthesisSignature,
            await self.synthesize.acall(
                npc_name=npc_name, text_characteristics=text_json, visual_characteristics=visual_json
            ),
        )

        # Calculate overall confidence as weighted average
        text_weight = 0.6  # Text is usually more informative for personality
        visual_weight = 0.4  # Visual provides important archetype cues
        overall_confidence = (
            text_characteristics.confidence_score * text_weight
            + visual_characteristics.confidence_score * visual_weight
        )

        # Create unified profile combining both sources
        return NPCDetails(
            npc_name=npc_name,
            # Text characteristics
            personality_traits=text_characteristics.personality_traits,
            occupation=text_characteristics.occupation,
            social_role=text_characteristics.social_role,
            dialogue_patterns=text_characteristics.dialogue_patterns,
            emotional_range=text_characteristics.emotional_range,
            background_lore=text_characteristics.background_lore,
            # Visual characteristics
            age_category=visual_characteristics.age_category,
            build_type=visual_characteristics.build_type,
            attire_style=visual_characteristics.attire_style,
            distinctive_features=visual_characteristics.distinctive_features,
            color_palette=visual_characteristics.color_palette,
            visual_archetype=visual_characteristics.visual_archetype,
            # Image URLs
            chathead_image_url=visual_characteristics.chathead_image_url,
            image_url=visual_characteristics.image_url,
            # Metadata
            text_confidence=text_characteristics.confidence_score,
            visual_confidence=visual_characteristics.confidence_score,
            overall_confidence=overall_confidence,
            synthesis_notes=f"Archetype: {synthesis_result.archetype_synthesis}. "
            + f"Conflicts: {synthesis_result.conflict_resolution}. "
            + f"Gaps filled: {synthesis_result.gap_filling}",
        )

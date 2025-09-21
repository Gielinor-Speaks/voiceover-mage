# ABOUTME: DSPy module for intelligent extraction of NPC text characteristics and personality
# ABOUTME: Analyzes markdown content to extract personality traits, dialogue patterns, and social context

from typing import cast

import dspy
from pydantic import BaseModel, Field


class NPCTextCharacteristics(BaseModel):
    """Text-based characteristics extracted from NPC wiki content."""

    personality_traits: str = Field(
        default="",
        description="Core personality traits description (e.g., 'gruff but fair-minded, deeply wise')",
    )
    occupation: str = Field(
        default="", description="NPC's role or job (e.g., 'blacksmith', 'quest giver', 'shopkeeper')"
    )
    social_role: str = Field(
        default="", description="Social position or archetype (e.g., 'village elder', 'mysterious stranger')"
    )
    dialogue_patterns: str = Field(
        default="",
        description="Speech patterns and mannerisms description (e.g., 'formal, archaic tones')",
    )
    emotional_range: str = Field(
        default="",
        description="Range of emotions expressed (e.g., 'calm and measured, occasionally passionate')",
    )
    background_lore: str = Field(default="", description="Key background information and lore context")
    confidence_score: float = Field(default=0.0, description="Confidence in the extraction accuracy (0.0-1.0)")
    reasoning: str = Field(default="", description="Explanation of how characteristics were identified from the text")


class TextExtractionSignature(dspy.Signature):
    """Extract NPC personality and text characteristics from wiki markdown content.

    Analyze dialogue, quest interactions, and lore descriptions to understand
    the NPC's personality, role, and behavioral patterns.
    """

    markdown_content: str = dspy.InputField(description="Raw markdown content from the NPC's wiki page")
    npc_name: str = dspy.InputField(description="Name of the NPC to extract characteristics for")
    npc_variant: str = dspy.InputField(
        description="Optional NPC variant (e.g., 'Pete', 'Peta', 'Ardougne', 'Blue shirt') or 'None' if no variant"
    )

    personality_traits: str = dspy.OutputField(
        description="Descriptive summary of core personality traits (e.g., 'wise and patient mentor')"
    )
    occupation: str = dspy.OutputField(description="The NPC's primary role or occupation")
    social_role: str = dspy.OutputField(description="Social position or archetype within the game world")
    dialogue_patterns: str = dspy.OutputField(
        description="Descriptive summary of speech patterns and mannerisms (e.g., 'measured cadence')"
    )
    emotional_range: str = dspy.OutputField(
        description="Descriptive summary of emotional range and expressions (e.g., 'serene but capable of anger')",
    )
    background_lore: str = dspy.OutputField(description="Summary of key background information and context")
    confidence: float = dspy.OutputField(description="Confidence score from 0.0 to 1.0 for the extraction accuracy")
    reasoning: str = dspy.OutputField(description="Step-by-step reasoning for characteristic identification")


class TextDetailExtractor(dspy.Module):
    """DSPy module for intelligent NPC text characteristic extraction.

    This module analyzes markdown content to extract:
    1. Personality traits from dialogue and descriptions
    2. Social role and occupation from context
    3. Speech patterns and emotional range
    4. Background lore and context
    5. Confidence scores and reasoning
    """

    def __init__(self):
        super().__init__()
        self.extract_text_details = dspy.ChainOfThought(TextExtractionSignature)

    async def aforward(
        self, markdown_content: str, npc_name: str, npc_variant: str | None = None
    ) -> NPCTextCharacteristics:
        """Extract text characteristics for the given NPC using async DSPy.

        This is the main implementation - forward() is a sync wrapper around this.

        Args:
            markdown_content: Raw markdown content from wiki page
            npc_name: Name of the NPC to extract characteristics for
            npc_variant: Optional variant (e.g., 'Pete', 'Ardougne', 'Blue shirt')

        Returns:
            NPCTextCharacteristics with personality traits and context
        """
        # Prepare variant for DSPy (convert None to "None" string)
        variant_str = npc_variant or "None"

        # Use DSPy's native async support via acall()
        result = await self.extract_text_details.acall(
            markdown_content=markdown_content, npc_name=npc_name, npc_variant=variant_str
        )
        # Type annotation for DSPy result
        result = cast("TextExtractionSignature", result)

        return NPCTextCharacteristics(
            personality_traits=result.personality_traits,
            occupation=result.occupation,
            social_role=result.social_role,
            dialogue_patterns=result.dialogue_patterns,
            emotional_range=result.emotional_range,
            background_lore=result.background_lore,
            confidence_score=float(result.confidence),
            reasoning=result.reasoning,
        )

    def forward(self, markdown_content: str, npc_name: str, npc_variant: str | None = None) -> NPCTextCharacteristics:
        """Sync wrapper around aforward() for backward compatibility.

        Args:
            markdown_content: Raw markdown content from wiki page
            npc_name: Name of the NPC to extract characteristics for
            npc_variant: Optional variant (e.g., 'Pete', 'Ardougne', 'Blue shirt')

        Returns:
            NPCTextCharacteristics with personality traits and context
        """
        import anyio

        return anyio.run(self.aforward, markdown_content, npc_name, npc_variant)

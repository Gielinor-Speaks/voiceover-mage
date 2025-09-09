# ABOUTME: Business domain models for core layer - final processed business objects
# ABOUTME: Pipeline orchestration enums and high-level domain models for voice generation

from enum import Enum
from typing import Any, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ExtractionStage(str, Enum):
    """Pipeline stages for NPC processing."""

    RAW = "raw"
    TEXT = "text"
    VISUAL = "visual"
    SYNTHESIS = "synthesis"
    PROFILE = "profile"
    VOICE_GENERATION = "voice_generation"
    COMPLETE = "complete"


class TrackedField[T](BaseModel):
    """A field with tracking information such as source, confidence and evidence."""

    value: T = Field(description="The actual field value")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score for this field (0.0-1.0)")
    source: str = Field(default="unknown", description="Source of this information")
    evidence: str = Field(default="", description="Evidence or reasoning for this value")


class NPCWikiSourcedData(BaseModel):
    """Data extracted about the NPC from a wiki source.

    Some fields are explicitly provided, others are inferred from the page context
    and have varying reliability. We use this as a base for character analysis.
    """

    # Core identification
    name: TrackedField[str] = Field(description="NPC name")
    variant: TrackedField[str | None] = Field(
        default_factory=lambda: TrackedField(
            value=None, source="default", confidence=1.0, evidence="No variant specified"
        ),
        description="NPC variant (e.g., 'Pete', 'Ardougne', etc.)",
    )

    # Character information
    occupation: TrackedField[str | None] = Field(
        default_factory=lambda: TrackedField(
            value=None, source="default", confidence=1.0, evidence="No occupation specified"
        ),
        description="NPC's job or role",
    )
    location: TrackedField[str | None] = Field(
        default_factory=lambda: TrackedField(
            value=None, source="default", confidence=1.0, evidence="No location specified"
        ),
        description="Where the NPC can be found",
    )

    # Personality and behavior
    personality_summary: TrackedField[str | None] = Field(
        default_factory=lambda: TrackedField(
            value=None, source="default", confidence=1.0, evidence="No personality summary"
        ),
        description="Brief personality description",
    )
    dialogue_style: TrackedField[str | None] = Field(
        default_factory=lambda: TrackedField(
            value=None, source="default", confidence=1.0, evidence="No dialogue style specified"
        ),
        description="How the NPC speaks and communicates",
    )

    # Physical characteristics
    appearance: TrackedField[str | None] = Field(
        default_factory=lambda: TrackedField(
            value=None, source="default", confidence=1.0, evidence="No appearance description"
        ),
        description="Physical appearance",
    )
    age_estimate: TrackedField[str | None] = Field(
        default_factory=lambda: TrackedField(value=None, source="default", confidence=1.0, evidence="No age estimate"),
        description="Estimated age category (young, middle-aged, elderly, etc.)",
    )

    # Quest and game context
    quest_involvement: TrackedField[list[str]] = Field(
        default_factory=lambda: TrackedField(
            value=[], source="default", confidence=1.0, evidence="No quest involvement"
        ),
        description="Quests this NPC is involved in",
    )
    game_significance: TrackedField[str | None] = Field(
        default_factory=lambda: TrackedField(
            value=None, source="default", confidence=1.0, evidence="No special significance"
        ),
        description="Significance or importance in the game world",
    )


class NPCDetails(BaseModel):
    """Unified NPC profile synthesizing text and visual characteristics.

    This represents the final synthesized profile ready for voice generation.
    """

    # Identity
    id: int
    npc_name: str
    npc_variant: str | None = None

    # Synthesized characteristics
    personality_profile: str = Field(description="Comprehensive personality description")
    voice_characteristics: str = Field(description="Voice and speech pattern description")
    visual_archetype: str = Field(description="Visual archetype and appearance summary")

    # Background and context
    background_summary: str = Field(description="Key background and lore information")
    social_context: str = Field(description="Social role and relationships")

    # Technical metadata
    synthesis_confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence in the synthesis")
    synthesis_reasoning: str = Field(description="AI reasoning for the synthesis decisions")

    # Source data references
    text_confidence: float = Field(ge=0.0, le=1.0, description="Confidence from text analysis")
    visual_confidence: float = Field(ge=0.0, le=1.0, description="Confidence from visual analysis")


class NPCProfile(BaseModel):
    """Final NPC profile optimized for voice generation.

    This is the ultimate business object ready for ElevenLabs Voice Design API.
    """

    # Core identity
    id: int
    npc_name: str
    npc_variant: str | None = None

    # Voice generation fields
    personality: str = Field(description="Personality traits for voice generation")
    voice_description: str = Field(description="Detailed voice characteristics")
    age_range: str = Field(description="Age category for voice selection")
    emotional_profile: str = Field(description="Emotional range and expression style")

    # Context for generation
    character_archetype: str = Field(description="Overall character archetype")
    speaking_style: str = Field(description="How the character speaks")

    # Quality metrics
    confidence_score: float = Field(ge=0.0, le=1.0, description="Overall confidence in the profile")
    generation_notes: str = Field(default="", description="Notes for voice generation process")


class VoiceGenerationResult(BaseModel):
    """Result from the voice sample generation process."""

    audio_sample_path: str = Field(description="The path to the saved audio sample file.")
    sample_text_used: str = Field(description="The exact text used to generate the sample.")
    generation_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific metadata from the generation process."
    )

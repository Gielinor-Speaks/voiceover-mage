# ABOUTME: Data models for raw NPC information extracted from wiki sources
# ABOUTME: Contains base Pydantic models for NPC data before character analysis

from typing import Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class TrackedField[T](BaseModel):
    """A field with tracking information such as information soruce, confidence and evidence."""

    value: T
    source: Literal["explicit", "inferred", "default"] = Field(
        ...,
        description=(
            "explicit: directly stated in text, inferred: concluded from context, default: reasonable assumption"
        ),
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence level of the value, from 0.0 (no confidence) to 1.0 (certain)"
    )
    evidence: str | None = Field(None, description="Text snippet or reasoning that supports this value")


class NPCWikiSourcedData(BaseModel):
    """Data extracted about the NPC from a wiki source, some fields are explicitly provided, others are inferred
    from the page context and have varying reliability. We use this as a base for character analysis which
    will be used to generate a description of a voice."""

    # Always explicitly provided (from page structure/URL)
    name: str = Field(..., description="The name of the NPC")
    wiki_url: str = Field(..., description="The URL of the NPC's wiki page")

    # Image fields (explicit if present, None if not)
    chathead_image_url: str | None = Field(None, description="The URL of the NPC's chathead image")
    image_url: str | None = Field(None, description="The URL of the NPC's image")

    # Core demographic fields with tracking
    gender: TrackedField[Literal["male", "female", "unknown"]] = Field(..., description="The gender of the NPC")
    race: TrackedField[str] = Field(..., description="The race/species of the NPC (human, elf, dwarf, tzhaar, etc.)")
    age_category: TrackedField[Literal["child", "young_adult", "middle_aged", "elderly", "unknown"]] = Field(
        ..., description="Approximate age category"
    )

    # Location and context
    location: TrackedField[str] = Field(..., description="Where the NPC is found (region, city, specific building)")
    examine_text: TrackedField[str] = Field(..., description="The exact examine text if available")

    # Social and professional attributes
    occupation: TrackedField[str] = Field(
        ..., description="Job, role, or profession (guard, merchant, wizard, servant, adventurer, etc.)"
    )
    social_class: TrackedField[
        Literal["nobility", "wealthy", "merchant", "commoner", "servant", "outlaw", "unknown"]
    ] = Field(..., description="Social standing in society")
    education_level: TrackedField[Literal["scholarly", "educated", "basic", "uneducated", "unknown"]] = Field(
        ..., description="Level of formal education or knowledge"
    )

    # Personality and behavior
    personality: TrackedField[str] = Field(
        ..., description="Key personality traits (brave, cowardly, cheerful, grumpy, mysterious, etc.)"
    )
    emotional_traits: TrackedField[str] = Field(
        ..., description="Emotional tendencies and temperament (anxious, calm, quick-tempered, melancholic)"
    )
    notable_quirks: TrackedField[str | None] = Field(
        ..., description="Unique behaviors, speech patterns, or mannerisms"
    )

    # Physical and mental condition
    physical_condition: TrackedField[str] = Field(
        ..., description="Physical health, fitness level, or notable conditions (fit, frail, injured, tired)"
    )
    mental_state: TrackedField[str] = Field(
        ..., description="Mental condition (sharp, confused, obsessed, paranoid, stable)"
    )

    # Cultural and regional identity
    cultural_background: TrackedField[str] = Field(
        ..., description="Cultural origin (Misthalin, Asgarnia, Kandarin, Karamjan, Fremennik, etc.)"
    )
    accent_region: TrackedField[str] = Field(..., description="Regional accent or dialect indicators")

    # Capabilities and skills
    combat_experience: TrackedField[
        Literal["veteran_warrior", "experienced", "some_training", "civilian", "pacifist"]
    ] = Field(..., description="Level of combat experience")
    magical_abilities: TrackedField[Literal["archmage", "wizard", "apprentice", "hedge_magic", "non_magical"]] = Field(
        ..., description="Level of magical ability"
    )

    # Speaking style attributes
    speech_formality: TrackedField[Literal["archaic_formal", "formal", "professional", "casual", "rough", "crude"]] = (
        Field(..., description="How formally they speak")
    )
    vocabulary_level: TrackedField[Literal["erudite", "sophisticated", "average", "simple", "primitive"]] = Field(
        ..., description="Complexity of vocabulary used"
    )
    speaking_pace: TrackedField[Literal["very_fast", "fast", "moderate", "normal", "slow", "very_slow"]] = Field(
        ..., description="Speed of speech"
    )
    voice_energy: TrackedField[Literal["energetic", "animated", "normal", "tired", "lethargic"]] = Field(
        ..., description="Energy level in voice"
    )

    # Story and quest significance
    quest_importance: TrackedField[Literal["protagonist", "major", "supporting", "minor", "none"]] = Field(
        ..., description="Importance in quests or storylines"
    )
    relationships: list[TrackedField[str]] = Field(..., description="Important relationships with other NPCs")

    # Dialogue and quotes
    dialogue_examples: list[str] = Field(
        default_factory=lambda: [], description="Actual quotes from the NPC if available"
    )
    common_phrases: list[TrackedField[str]] = Field(
        default_factory=lambda: [], description="Recurring phrases or expressions they use"
    )

    # Synthesized fields
    description: str = Field(
        ..., description="A comprehensive description of the NPC synthesized from all available information"
    )
    voice_direction: str = Field(
        ..., description="Specific voice direction for voice synthesis based on all character attributes"
    )
    confidence_overall: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in the extraction quality (weighted average of field confidences)",
    )

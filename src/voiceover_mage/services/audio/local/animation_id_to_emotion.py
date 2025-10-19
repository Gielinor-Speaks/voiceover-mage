# ABOUTME: Maps OSRS animation IDs to 8D emotion vectors for IndexTTS v2
# ABOUTME: Uses intermediary name lookup with pattern-based matching for maintainability

"""Animation ID to Emotion Vector Mapper for IndexTTS v2.

This module maps Old School RuneScape (OSRS) NPC dialogue animation IDs to
8-dimensional emotion vectors used by IndexTTS v2 for expressive voice synthesis.

Emotion Vector Format (8 dimensions):
    [happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]

Each dimension ranges from 0.0 to 1.0. Vectors can blend multiple emotions for
nuanced expression (e.g., laughing = happy + surprised).

References:
    - RuneLite AnimationID: https://static.runelite.net/runelite-api/apidocs/net/runelite/api/gameval/AnimationID.html
    - IndexTTS v2 Paper: docs/IndexTTSv2 Paper - 2506.21619v2.pdf
    - Implementation Plan: NPC_ANIMATION_TO_EMOTION_COPY.md
"""

from __future__ import annotations

import re
from typing import NamedTuple

from loguru import logger


class EmotionVector(NamedTuple):
    """8-dimensional emotion vector for IndexTTS v2."""

    happy: float
    angry: float
    sad: float
    afraid: float
    disgusted: float
    melancholic: float
    surprised: float
    calm: float

    def to_list(self) -> list[float]:
        """Convert to list format expected by IndexTTS v2 API."""
        return list(self)

    @classmethod
    def from_list(cls, values: list[float]) -> EmotionVector:
        """Create EmotionVector from list."""
        if len(values) != 8:
            raise ValueError(f"Expected 8 values, got {len(values)}")
        return cls(*values)


# ============================================================================
# Emotion Vector Presets
# ============================================================================

# Core emotions
HAPPY = EmotionVector(0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.0)
ANGRY = EmotionVector(0.0, 0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1)
SAD = EmotionVector(0.0, 0.0, 0.8, 0.0, 0.0, 0.2, 0.0, 0.0)
AFRAID = EmotionVector(0.0, 0.0, 0.0, 0.8, 0.0, 0.0, 0.2, 0.0)
DISGUSTED = EmotionVector(0.0, 0.0, 0.0, 0.0, 0.8, 0.0, 0.0, 0.2)
MELANCHOLIC = EmotionVector(0.0, 0.0, 0.2, 0.0, 0.0, 0.7, 0.0, 0.1)
SURPRISED = EmotionVector(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.8, 0.2)
CALM = EmotionVector(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)

# Blended emotions
LAUGHING = EmotionVector(0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.0)  # Happy + Surprised
ENTHUSIASTIC = EmotionVector(0.6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.1)  # Happy + Surprised + Calm
BORED = EmotionVector(0.0, 0.0, 0.0, 0.0, 0.0, 0.4, 0.0, 0.6)  # Melancholic + Calm
CONFUSED = EmotionVector(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.4, 0.6)  # Surprised + Calm (quizzical)
SHIFTY = EmotionVector(0.0, 0.0, 0.0, 0.3, 0.0, 0.0, 0.1, 0.6)  # Afraid + Calm (nervous)
DRUNK = EmotionVector(0.2, 0.0, 0.0, 0.0, 0.0, 0.1, 0.1, 0.6)  # Happy + Confused + Calm
SKEPTICAL = EmotionVector(0.0, 0.1, 0.0, 0.0, 0.0, 0.1, 0.2, 0.6)  # Slight angry + surprised + calm
MENACING = EmotionVector(0.0, 0.6, 0.0, 0.0, 0.0, 0.3, 0.0, 0.1)  # Angry + Melancholic (dark/ominous)
CHANTING = EmotionVector(0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.0, 0.8)  # Calm + slight melancholic (ritual/trance)
SLEEPY = EmotionVector(0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.0, 0.7)  # Very calm + melancholic
HYPNOTIZED = EmotionVector(0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0, 0.9)  # Almost pure calm
GESTURING = EmotionVector(0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.8)  # Mostly calm with slight engagement

# Special cases
NEUTRAL = CALM  # Alias for clarity


# ============================================================================
# Animation ID to Name Mapping
# ============================================================================
# Based on RuneLite's AnimationID constants
# See: https://static.runelite.net/runelite-api/apidocs/net/runelite/api/gameval/AnimationID.html

ANIMATION_ID_TO_NAME: dict[int, str] = {
    # CHATBORED series (562-565)
    562: "CHATBORED1",
    563: "CHATBORED2",
    564: "CHATBORED3",
    565: "CHATBORED4",

    # SHORTCHATNEU (566)
    566: "SHORTCHATNEU1",

    # CHATHAP series (567-570)
    567: "CHATHAP1",
    568: "CHATHAP2",
    569: "CHATHAP3",
    570: "CHATHAP4",

    # CHATSHOCK series (571-574)
    571: "CHATSHOCK1",
    572: "CHATSHOCK2",
    573: "CHATSHOCK3",
    574: "CHATSHOCK4",

    # CHATNEU series (588-591)
    588: "CHATNEU1",
    589: "CHATNEU2",
    590: "CHATNEU3",
    591: "CHATNEU4",

    # CHATSCARED series (596-599)
    596: "CHATSCARED1",
    597: "CHATSCARED2",
    598: "CHATSCARED3",
    599: "CHATSCARED4",

    # CHATLAUGH series (605-608)
    605: "CHATLAUGH1",
    606: "CHATLAUGH2",
    607: "CHATLAUGH3",
    608: "CHATLAUGH4",

    # CHATSAD series (610-613)
    610: "CHATSAD1",
    611: "CHATSAD2",
    612: "CHATSAD3",
    613: "CHATSAD4",

    # CHATANG series (614-617)
    614: "CHATANG1",
    615: "CHATANG2",
    616: "CHATANG3",
    617: "CHATANG4",

    # Additional chat animations (IDs to be confirmed)
    # CHATCON series (Confused) - estimated IDs
    592: "CHATCON1",
    593: "CHATCON2",
    594: "CHATCON3",
    595: "CHATCON4",

    # CHATDRUNK series - estimated IDs
    575: "CHATDRUNK1",
    576: "CHATDRUNK2",
    577: "CHATDRUNK3",
    578: "CHATDRUNK4",

    # CHATENT series (Enthusiastic) - estimated IDs
    579: "CHATENT1",
    580: "CHATENT2",
    581: "CHATENT3",
    582: "CHATENT4",
    583: "CHATENT_IDLE",

    # CHATSHIFTY series - estimated IDs
    600: "CHATSHIFTY1",
    601: "CHATSHIFTY2",
    602: "CHATSHIFTY3",
    603: "CHATSHIFTY4",

    # CHATQUIZ series (Quizzical) - estimated IDs
    584: "CHATQUIZ1",
    585: "CHATQUIZ2",
    586: "CHATQUIZ3",
    587: "CHATQUIZ4",

    # CHATHAND series (Gesturing) - estimated IDs
    618: "CHATHAND1",
    619: "CHATHAND2",
    620: "CHATHAND3",
    621: "CHATHAND4",

    # CHATSKULL series - estimated IDs
    622: "CHATSKULL1",
    623: "CHATSKULL2",
    624: "CHATSKULL3",
    625: "CHATSKULL4",

    # Special/unique animations
    561: "CHAT_HUMAN_SLEEP",
    626: "CHATCHANT1",
    627: "CHATIDLENEU1",
    628: "CHATHAP_IDLE",
    629: "CHATEASTERBUNNY4",
    630: "CHATHYPNOBUNNY4_2006",

    # NPC-specific animations
    631: "CHATGOBLIN1",
    632: "CHATGOBLIN2",
    633: "CHATGOBLIN3",
    634: "CHATGOBLIN4",

    # Character-specific (Xamphur)
    9502: "CHATHEAD_XAMPHUR_DEFAULT",
    9503: "CHATHEAD_XAMPHUR_DEFAULT_AFFIRMATIVE",
    9504: "CHATHEAD_XAMPHUR_DEFAULT_EXTROVERTED",
    9505: "CHATHEAD_XAMPHUR_DEFAULT_INTROVERTED",
    9506: "CHATHEAD_XAMPHUR_DEFAULT_NEGATIVE",
    9507: "CHATHEAD_XAMPHUR_DEFAULT_TILT",

    # Character-specific (Rat Boss)
    9508: "CHATHEAD_RAT_BOSS_IDLE_01",
    9509: "CHATHEAD_RAT_BOSS_IDLE_02",
    9510: "CHATHEAD_RAT_BOSS_IDLE_03",
}


# ============================================================================
# Pattern-Based Emotion Mapping
# ============================================================================

class EmotionPattern(NamedTuple):
    """Pattern matcher for animation names to emotions."""

    pattern: str  # Regex pattern
    emotion: EmotionVector
    description: str


# Ordered from most specific to least specific
EMOTION_PATTERNS: list[EmotionPattern] = [
    # Specific character animations (most specific first)
    EmotionPattern(r"XAMPHUR_DEFAULT_AFFIRMATIVE", HAPPY, "Xamphur agreeing"),
    EmotionPattern(r"XAMPHUR_DEFAULT_NEGATIVE", SAD, "Xamphur disagreeing"),
    EmotionPattern(r"XAMPHUR_DEFAULT_EXTROVERTED", ENTHUSIASTIC, "Xamphur extroverted"),
    EmotionPattern(r"XAMPHUR_DEFAULT_INTROVERTED", BORED, "Xamphur introverted"),
    EmotionPattern(r"XAMPHUR_DEFAULT_TILT", CONFUSED, "Xamphur confused"),
    EmotionPattern(r"XAMPHUR_DEFAULT", NEUTRAL, "Xamphur default"),

    # Rat boss animations
    EmotionPattern(r"RAT_BOSS_IDLE", MENACING, "Rat boss idle (menacing)"),

    # Core emotion patterns (by name prefix/infix)
    EmotionPattern(r"^CHATHAP", HAPPY, "Happy chat"),
    EmotionPattern(r"^CHATANG", ANGRY, "Angry chat"),
    EmotionPattern(r"^CHATSAD", SAD, "Sad chat"),
    EmotionPattern(r"^CHATSCARED", AFRAID, "Scared chat"),
    EmotionPattern(r"^CHATSHOCK", SURPRISED, "Shocked chat"),
    EmotionPattern(r"^CHATLAUGH", LAUGHING, "Laughing chat"),
    EmotionPattern(r"^CHATNEU", NEUTRAL, "Neutral chat"),
    EmotionPattern(r"^CHATBORED", BORED, "Bored chat"),

    # Blended emotion patterns
    EmotionPattern(r"^CHATENT", ENTHUSIASTIC, "Enthusiastic chat"),
    EmotionPattern(r"^CHATCON", CONFUSED, "Confused chat"),
    EmotionPattern(r"^CHATDRUNK", DRUNK, "Drunk chat"),
    EmotionPattern(r"^CHATSHIFTY", SHIFTY, "Shifty chat"),
    EmotionPattern(r"^CHATQUIZ", CONFUSED, "Quizzical chat"),
    EmotionPattern(r"^CHATHAND", GESTURING, "Hand gesturing chat"),
    EmotionPattern(r"^CHATSKULL", MENACING, "Skull/menacing chat"),
    EmotionPattern(r"^CHATCHANT", CHANTING, "Chanting"),

    # Special states
    EmotionPattern(r"SLEEP", SLEEPY, "Sleeping"),
    EmotionPattern(r"HYPNO", HYPNOTIZED, "Hypnotized"),
    EmotionPattern(r"EASTERBUNNY", HAPPY, "Easter bunny (playful)"),

    # Goblin-specific (neutral for now, could be customized)
    EmotionPattern(r"GOBLIN", NEUTRAL, "Goblin chat"),

    # Generic idle/neutral patterns (least specific)
    EmotionPattern(r"IDLE", NEUTRAL, "Idle animation"),
    EmotionPattern(r"NEU", NEUTRAL, "Neutral animation"),
]


# ============================================================================
# Animation Emotion Mapper
# ============================================================================

class AnimationEmotionMapper:
    """Maps OSRS animation IDs to IndexTTS v2 emotion vectors.

    This mapper uses a two-stage lookup:
    1. Animation ID → Animation Name (direct lookup)
    2. Animation Name → Emotion Vector (pattern matching)

    Benefits:
    - Self-documenting: Names carry semantic meaning
    - Maintainable: Pattern-based matching reduces duplication
    - Extensible: New animations can be added easily
    - Debuggable: Logs show animation names, not just IDs

    Example:
        >>> mapper = AnimationEmotionMapper()
        >>> emotion, source = mapper.map_animation_to_emotion(567)
        >>> print(emotion)  # HAPPY emotion vector
        [0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.0]
        >>> print(source)
        animation_name:CHATHAP1
    """

    def __init__(self) -> None:
        """Initialize the mapper."""
        self._animation_id_to_name = ANIMATION_ID_TO_NAME
        self._emotion_patterns = EMOTION_PATTERNS
        self._neutral_vector = NEUTRAL
        # Cache for animation lookups (avoid lru_cache on method to prevent memory leaks)
        self._cache: dict[int | None, tuple[list[float], str] | None] = {}

    def map_animation_to_emotion(
        self,
        animation_id: int | None,
    ) -> tuple[list[float], str] | None:
        """Map animation ID to emotion vector.

        Args:
            animation_id: OSRS animation ID, or None

        Returns:
            Tuple of (emotion_vector, source) if animation is explicitly mapped, None otherwise:
            - emotion_vector: 8D list of floats [happy, angry, sad, afraid,
              disgusted, melancholic, surprised, calm]
            - source: Description of how emotion was determined:
                * "animation_name:<NAME>" - Matched by pattern

            Returns None for ANY unmapped animation (including None, unknown IDs,
            or unmatched patterns) to signal that text-based emotion inference
            should be used as a fallback. No default emotions are ever returned.

        Examples:
            >>> mapper = AnimationEmotionMapper()
            >>> emotion, source = mapper.map_animation_to_emotion(567)
            >>> emotion
            [0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.0]
            >>> source
            'animation_name:CHATHAP1'

            >>> result = mapper.map_animation_to_emotion(None)
            >>> result is None
            True

            >>> result = mapper.map_animation_to_emotion(99999)  # Unknown
            >>> result is None
            True
        """
        # Check cache first
        if animation_id in self._cache:
            cached_result = self._cache[animation_id]
            # Return a copy to ensure immutability
            if cached_result is None:
                return None
            emotion_vector, source = cached_result
            return (emotion_vector.copy(), source)

        # Case 1: No animation provided
        if animation_id is None:
            logger.debug("No animation ID provided, returning None for text-based inference")
            self._cache[animation_id] = None
            return None

        # Case 2: Lookup animation name
        animation_name = self._animation_id_to_name.get(animation_id)

        if animation_name is None:
            logger.warning(
                f"Unknown animation ID {animation_id}. Returning None to signal "
                f"text-based emotion inference should be used. Consider adding "
                f"this animation to ANIMATION_ID_TO_NAME mapping if it's a valid OSRS animation."
            )
            self._cache[animation_id] = None
            return None

        # Case 3: Pattern match on animation name
        for pattern_info in self._emotion_patterns:
            if re.search(pattern_info.pattern, animation_name):
                emotion_vector = pattern_info.emotion.to_list()
                source = f"animation_name:{animation_name}"

                logger.debug(
                    f"Mapped animation {animation_name} ({animation_id}) "
                    f"to {pattern_info.description} emotion: {emotion_vector}"
                )

                result = (emotion_vector, source)
                self._cache[animation_id] = result
                return result

        # Case 4: No pattern matched (shouldn't happen with good patterns)
        logger.warning(
            f"Animation name '{animation_name}' ({animation_id}) did not match any "
            f"emotion pattern. Returning None to signal text-based emotion inference "
            f"should be used. Consider adding a pattern for this animation family."
        )
        self._cache[animation_id] = None
        return None

    def get_animation_name(self, animation_id: int) -> str | None:
        """Get the animation name for a given ID.

        Args:
            animation_id: OSRS animation ID

        Returns:
            Animation name if known, None otherwise
        """
        return self._animation_id_to_name.get(animation_id)

    def get_supported_animations(self) -> dict[int, str]:
        """Get all supported animation IDs and their names.

        Returns:
            Dictionary mapping animation IDs to names
        """
        return self._animation_id_to_name.copy()

    def get_emotion_for_name(self, animation_name: str) -> EmotionVector | None:
        """Get emotion vector for a given animation name.

        Useful for testing and debugging.

        Args:
            animation_name: Animation name (e.g., "CHATHAP1")

        Returns:
            EmotionVector if pattern matches, None otherwise
        """
        for pattern_info in self._emotion_patterns:
            if re.search(pattern_info.pattern, animation_name):
                return pattern_info.emotion
        return None


# ============================================================================
# Convenience Functions
# ============================================================================

# Global singleton instance for convenience
_default_mapper: AnimationEmotionMapper | None = None


def get_default_mapper() -> AnimationEmotionMapper:
    """Get the default global mapper instance."""
    global _default_mapper
    if _default_mapper is None:
        _default_mapper = AnimationEmotionMapper()
    return _default_mapper


def map_animation_to_emotion(
    animation_id: int | None,
) -> tuple[list[float], str] | None:
    """Convenience function to map animation ID to emotion using default mapper.

    Args:
        animation_id: OSRS animation ID, or None

    Returns:
        Tuple of (emotion_vector, source) if animation is known, None otherwise.
        None signals that text-based emotion inference should be used.
    """
    return get_default_mapper().map_animation_to_emotion(animation_id)

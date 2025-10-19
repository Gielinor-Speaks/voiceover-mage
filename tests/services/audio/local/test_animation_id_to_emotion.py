# ABOUTME: Tests for animation ID to emotion vector mapping

"""Tests for AnimationEmotionMapper and related functionality."""

import pytest

from voiceover_mage.services.audio.local.animation_id_to_emotion import (
    AFRAID,
    ANGRY,
    BORED,
    CALM,
    CHANTING,
    CONFUSED,
    DRUNK,
    ENTHUSIASTIC,
    GESTURING,
    HAPPY,
    HYPNOTIZED,
    LAUGHING,
    MENACING,
    SAD,
    SHIFTY,
    SLEEPY,
    SURPRISED,
    AnimationEmotionMapper,
    EmotionVector,
    get_default_mapper,
    map_animation_to_emotion,
)


class TestEmotionVector:
    """Tests for EmotionVector class."""

    def test_emotion_vector_creation(self) -> None:
        """Test creating an emotion vector."""
        emotion = EmotionVector(0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.0)
        assert emotion.happy == 0.8
        assert emotion.angry == 0.0
        assert emotion.surprised == 0.2
        assert emotion.calm == 0.0

    def test_emotion_vector_to_list(self) -> None:
        """Test converting emotion vector to list."""
        emotion = HAPPY
        result = emotion.to_list()
        assert isinstance(result, list)
        assert len(result) == 8
        assert result[0] == 0.8  # happy
        assert result[6] == 0.2  # surprised

    def test_emotion_vector_from_list(self) -> None:
        """Test creating emotion vector from list."""
        values = [0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.0]
        emotion = EmotionVector.from_list(values)
        assert emotion.happy == 0.8
        assert emotion.surprised == 0.2

    def test_emotion_vector_from_list_wrong_length(self) -> None:
        """Test creating emotion vector from list with wrong length."""
        with pytest.raises(ValueError, match="Expected 8 values"):
            EmotionVector.from_list([0.8, 0.0, 0.0])


class TestEmotionPresets:
    """Tests for emotion preset constants."""

    def test_core_emotions_have_8_dimensions(self) -> None:
        """Test that all core emotion presets have 8 dimensions."""
        emotions = [HAPPY, ANGRY, SAD, AFRAID, SURPRISED, CALM]
        for emotion in emotions:
            assert len(emotion.to_list()) == 8

    def test_blended_emotions_have_8_dimensions(self) -> None:
        """Test that all blended emotion presets have 8 dimensions."""
        emotions = [
            LAUGHING,
            ENTHUSIASTIC,
            BORED,
            CONFUSED,
            SHIFTY,
            DRUNK,
            MENACING,
            CHANTING,
            SLEEPY,
            HYPNOTIZED,
            GESTURING,
        ]
        for emotion in emotions:
            assert len(emotion.to_list()) == 8

    def test_emotion_values_in_valid_range(self) -> None:
        """Test that all emotion preset values are in [0.0, 1.0] range."""
        emotions = [
            HAPPY,
            ANGRY,
            SAD,
            AFRAID,
            SURPRISED,
            CALM,
            LAUGHING,
            BORED,
            CONFUSED,
            DRUNK,
        ]
        for emotion in emotions:
            for value in emotion.to_list():
                assert 0.0 <= value <= 1.0, f"Value {value} out of range in {emotion}"


class TestAnimationEmotionMapper:
    """Tests for AnimationEmotionMapper class."""

    def test_mapper_initialization(self) -> None:
        """Test that mapper initializes correctly."""
        mapper = AnimationEmotionMapper()
        assert mapper is not None
        assert len(mapper.get_supported_animations()) > 0

    def test_map_happy_animation(self) -> None:
        """Test mapping happy chat animation."""
        mapper = AnimationEmotionMapper()
        emotion, source = mapper.map_animation_to_emotion(567)  # CHATHAP1

        assert len(emotion) == 8
        assert emotion[0] == 0.8  # happy dimension
        assert source == "animation_name:CHATHAP1"

    def test_map_angry_animation(self) -> None:
        """Test mapping angry chat animation."""
        mapper = AnimationEmotionMapper()
        emotion, source = mapper.map_animation_to_emotion(614)  # CHATANG1

        assert len(emotion) == 8
        assert emotion[1] == 0.9  # angry dimension
        assert source == "animation_name:CHATANG1"

    def test_map_sad_animation(self) -> None:
        """Test mapping sad chat animation."""
        mapper = AnimationEmotionMapper()
        emotion, source = mapper.map_animation_to_emotion(610)  # CHATSAD1

        assert len(emotion) == 8
        assert emotion[2] == 0.8  # sad dimension
        assert emotion[5] == 0.2  # melancholic dimension
        assert source == "animation_name:CHATSAD1"

    def test_map_scared_animation(self) -> None:
        """Test mapping scared chat animation."""
        mapper = AnimationEmotionMapper()
        emotion, source = mapper.map_animation_to_emotion(596)  # CHATSCARED1

        assert len(emotion) == 8
        assert emotion[3] == 0.8  # afraid dimension
        assert source == "animation_name:CHATSCARED1"

    def test_map_surprised_animation(self) -> None:
        """Test mapping surprised chat animation."""
        mapper = AnimationEmotionMapper()
        emotion, source = mapper.map_animation_to_emotion(571)  # CHATSHOCK1

        assert len(emotion) == 8
        assert emotion[6] == 0.8  # surprised dimension
        assert source == "animation_name:CHATSHOCK1"

    def test_map_laughing_animation(self) -> None:
        """Test mapping laughing chat animation (blended emotion)."""
        mapper = AnimationEmotionMapper()
        emotion, source = mapper.map_animation_to_emotion(605)  # CHATLAUGH1

        assert len(emotion) == 8
        assert emotion[0] == 0.7  # happy dimension
        assert emotion[6] == 0.3  # surprised dimension
        assert source == "animation_name:CHATLAUGH1"

    def test_map_neutral_animation(self) -> None:
        """Test mapping neutral chat animation."""
        mapper = AnimationEmotionMapper()
        emotion, source = mapper.map_animation_to_emotion(588)  # CHATNEU1

        assert len(emotion) == 8
        assert emotion[7] == 1.0  # calm dimension
        assert source == "animation_name:CHATNEU1"

    def test_map_bored_animation(self) -> None:
        """Test mapping bored chat animation."""
        mapper = AnimationEmotionMapper()
        emotion, source = mapper.map_animation_to_emotion(562)  # CHATBORED1

        assert len(emotion) == 8
        assert emotion[5] == 0.4  # melancholic dimension
        assert emotion[7] == 0.6  # calm dimension
        assert source == "animation_name:CHATBORED1"

    def test_map_null_animation_id(self) -> None:
        """Test mapping null animation ID returns None for text inference."""
        mapper = AnimationEmotionMapper()
        result = mapper.map_animation_to_emotion(None)

        # None animation should return None to signal text-based inference
        assert result is None

    def test_map_unknown_animation_id(self) -> None:
        """Test mapping unknown animation ID returns None for text inference."""
        mapper = AnimationEmotionMapper()
        result = mapper.map_animation_to_emotion(99999)

        # Unknown animation should return None to signal text-based inference
        assert result is None

    def test_pattern_matching_all_happy_variants(self) -> None:
        """Test that all CHATHAP variants map to happy emotion."""
        mapper = AnimationEmotionMapper()
        happy_ids = [567, 568, 569, 570]  # CHATHAP1-4

        for animation_id in happy_ids:
            emotion, source = mapper.map_animation_to_emotion(animation_id)
            assert emotion[0] == 0.8  # happy dimension
            assert "CHATHAP" in source

    def test_pattern_matching_all_angry_variants(self) -> None:
        """Test that all CHATANG variants map to angry emotion."""
        mapper = AnimationEmotionMapper()
        angry_ids = [614, 615, 616, 617]  # CHATANG1-4

        for animation_id in angry_ids:
            emotion, source = mapper.map_animation_to_emotion(animation_id)
            assert emotion[1] == 0.9  # angry dimension
            assert "CHATANG" in source

    def test_get_animation_name(self) -> None:
        """Test getting animation name from ID."""
        mapper = AnimationEmotionMapper()

        assert mapper.get_animation_name(567) == "CHATHAP1"
        assert mapper.get_animation_name(614) == "CHATANG1"
        assert mapper.get_animation_name(99999) is None

    def test_get_supported_animations(self) -> None:
        """Test getting all supported animations."""
        mapper = AnimationEmotionMapper()
        animations = mapper.get_supported_animations()

        assert isinstance(animations, dict)
        assert len(animations) > 40  # We have 50+ animations
        assert 567 in animations  # CHATHAP1
        assert animations[567] == "CHATHAP1"

    def test_get_emotion_for_name(self) -> None:
        """Test getting emotion for animation name."""
        mapper = AnimationEmotionMapper()

        emotion = mapper.get_emotion_for_name("CHATHAP1")
        assert emotion == HAPPY

        emotion = mapper.get_emotion_for_name("CHATANG1")
        assert emotion == ANGRY

        emotion = mapper.get_emotion_for_name("UNKNOWN_ANIMATION")
        assert emotion is None

    def test_caching_works(self) -> None:
        """Test that caching works for repeated lookups."""
        mapper = AnimationEmotionMapper()

        # First lookup
        result1 = mapper.map_animation_to_emotion(567)
        assert result1 is not None
        emotion1, source1 = result1

        # Second lookup should be cached
        result2 = mapper.map_animation_to_emotion(567)
        assert result2 is not None
        emotion2, source2 = result2

        assert emotion1 == emotion2
        assert source1 == source2

        # Cache should have the entry
        assert 567 in mapper._cache

    def test_caching_works_for_unknown_animations(self) -> None:
        """Test that caching works for unknown animations (None results)."""
        mapper = AnimationEmotionMapper()

        # First lookup of unknown animation
        result1 = mapper.map_animation_to_emotion(99999)
        assert result1 is None

        # Second lookup should be cached
        result2 = mapper.map_animation_to_emotion(99999)
        assert result2 is None

        # Cache should have the entry
        assert 99999 in mapper._cache
        assert mapper._cache[99999] is None

    def test_xamphur_specific_animations(self) -> None:
        """Test character-specific Xamphur animations."""
        mapper = AnimationEmotionMapper()

        # Affirmative should be happy
        result = mapper.map_animation_to_emotion(9503)
        assert result is not None
        emotion, source = result
        assert emotion == HAPPY.to_list()
        assert "XAMPHUR_DEFAULT_AFFIRMATIVE" in source

        # Negative should be sad
        result = mapper.map_animation_to_emotion(9506)
        assert result is not None
        emotion, source = result
        assert emotion == SAD.to_list()
        assert "XAMPHUR_DEFAULT_NEGATIVE" in source

        # Extroverted should be enthusiastic
        result = mapper.map_animation_to_emotion(9504)
        assert result is not None
        emotion, source = result
        assert emotion == ENTHUSIASTIC.to_list()
        assert "XAMPHUR_DEFAULT_EXTROVERTED" in source

    def test_special_state_animations(self) -> None:
        """Test special state animations (sleep, hypno, etc.)."""
        mapper = AnimationEmotionMapper()

        # Sleep should be sleepy
        result = mapper.map_animation_to_emotion(561)
        assert result is not None
        emotion, source = result
        assert emotion == SLEEPY.to_list()
        assert "CHAT_HUMAN_SLEEP" in source

        # Hypno should be hypnotized
        result = mapper.map_animation_to_emotion(630)
        assert result is not None
        emotion, source = result
        assert emotion == HYPNOTIZED.to_list()
        assert "CHATHYPNOBUNNY4_2006" in source

        # Chant should be chanting
        result = mapper.map_animation_to_emotion(626)
        assert result is not None
        emotion, source = result
        assert emotion == CHANTING.to_list()
        assert "CHATCHANT1" in source


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_default_mapper(self) -> None:
        """Test getting default mapper singleton."""
        mapper1 = get_default_mapper()
        mapper2 = get_default_mapper()

        assert mapper1 is mapper2  # Same instance (singleton)

    def test_map_animation_to_emotion_convenience(self) -> None:
        """Test convenience function for mapping animation to emotion."""
        result = map_animation_to_emotion(567)

        assert result is not None
        emotion, source = result
        assert len(emotion) == 8
        assert emotion[0] == 0.8  # happy
        assert source == "animation_name:CHATHAP1"

    def test_map_animation_to_emotion_null(self) -> None:
        """Test convenience function with null animation."""
        result = map_animation_to_emotion(None)

        # None animation should return None
        assert result is None

    def test_map_animation_to_emotion_unknown(self) -> None:
        """Test convenience function with unknown animation."""
        result = map_animation_to_emotion(99999)

        # Unknown animation should return None
        assert result is None


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_vector_immutability(self) -> None:
        """Test that returned vectors are copies (immutable from mapper perspective)."""
        mapper = AnimationEmotionMapper()

        emotion1, _ = mapper.map_animation_to_emotion(567)
        emotion2, _ = mapper.map_animation_to_emotion(567)

        # Modify first result
        emotion1[0] = 0.0

        # Second result should be unchanged
        assert emotion2[0] == 0.8

    def test_all_emotions_have_valid_ranges(self) -> None:
        """Test that all mapped emotions have values in valid range."""
        mapper = AnimationEmotionMapper()

        # Test a sample of known animation IDs
        test_ids = [562, 567, 571, 588, 596, 605, 610, 614]

        for animation_id in test_ids:
            emotion, _ = mapper.map_animation_to_emotion(animation_id)
            for value in emotion:
                assert (
                    0.0 <= value <= 1.0
                ), f"Invalid value {value} for animation {animation_id}"

    def test_pattern_specificity_order(self) -> None:
        """Test that more specific patterns match before generic ones."""
        mapper = AnimationEmotionMapper()

        # Xamphur affirmative should match specific pattern, not generic XAMPHUR
        result = mapper.map_animation_to_emotion(9503)
        assert result is not None
        emotion, source = result
        assert "AFFIRMATIVE" in source
        assert emotion == HAPPY.to_list()

        # Generic Xamphur should still work
        result = mapper.map_animation_to_emotion(9502)
        assert result is not None
        emotion, source = result
        assert "XAMPHUR_DEFAULT" in source
        assert emotion == CALM.to_list()


class TestIntegration:
    """Integration tests for the animation emotion mapper."""

    def test_end_to_end_emotion_mapping(self) -> None:
        """Test complete workflow from animation ID to emotion vector."""
        # Simulate receiving animation IDs from game
        animation_sequence = [
            (567, "happy"),  # CHATHAP1
            (614, "angry"),  # CHATANG1
            (610, "sad"),  # CHATSAD1
            (588, "neutral"),  # CHATNEU1
        ]

        mapper = AnimationEmotionMapper()

        for animation_id, expected_emotion in animation_sequence:
            result = mapper.map_animation_to_emotion(animation_id)
            assert result is not None
            emotion, source = result

            # Verify we got a valid emotion vector
            assert len(emotion) == 8
            assert all(0.0 <= v <= 1.0 for v in emotion)

            # Verify source includes animation name
            assert "animation_name:" in source

    def test_mapper_handles_realistic_game_sequence(self) -> None:
        """Test mapper with realistic sequence of game animations."""
        # Simulate an NPC conversation with varying emotions
        conversation_animations = [
            588,  # Start neutral
            567,  # Get happy
            567,  # Stay happy
            614,  # Get angry
            610,  # Get sad
            588,  # Return to neutral
        ]

        mapper = AnimationEmotionMapper()
        results = []

        for animation_id in conversation_animations:
            result = mapper.map_animation_to_emotion(animation_id)
            assert result is not None
            emotion, source = result
            results.append((emotion, source))

        # All should have valid results
        assert len(results) == len(conversation_animations)
        for emotion, source in results:
            assert len(emotion) == 8
            assert "animation_name:" in source

    def test_fallback_to_text_inference(self) -> None:
        """Test that unknown animations return None for text inference fallback."""
        mapper = AnimationEmotionMapper()

        # Simulate receiving an unknown animation from game
        unknown_animation_id = 7777

        result = mapper.map_animation_to_emotion(unknown_animation_id)

        # Should return None to signal text-based emotion inference needed
        assert result is None

        # Caller can then fall back to text inference
        # (This would be implemented in the TTS service layer)
        if result is None:
            # Fallback: use text-based emotion inference
            text_based_emotion = CALM.to_list()  # Example fallback
            assert len(text_based_emotion) == 8

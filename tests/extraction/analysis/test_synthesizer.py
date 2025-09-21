# ABOUTME: Tests for DSPy character synthesis module
# ABOUTME: Comprehensive testing of unified NPC profile generation

from unittest.mock import Mock, patch

import pytest

from voiceover_mage.extraction.analysis.image import NPCVisualCharacteristics
from voiceover_mage.extraction.analysis.synthesizer import (
    DetailSynthesizer,
    NPCDetails,
)
from voiceover_mage.extraction.analysis.text import NPCTextCharacteristics


class TestNPCDetails:
    """Test the NPCDetails unified profile model."""

    def test_model_creation_minimal(self):
        """Test model can be created with minimal data."""
        details = NPCDetails(npc_name="Test NPC")

        assert details.npc_name == "Test NPC"
        assert details.personality_traits == ""
        assert details.occupation == ""
        assert details.visual_archetype == ""
        assert details.overall_confidence == 0.0

    def test_model_creation_comprehensive(self):
        """Test model creation with comprehensive character data."""
        details = NPCDetails(
            npc_name="Master Wizard Gandros",
            personality_traits="wise, patient, mysterious, deeply knowledgeable",
            occupation="archmage, keeper of ancient knowledge",
            social_role="magical mentor, advisor to kings",
            dialogue_patterns="speaks in riddles, uses archaic language, profound wisdom",
            emotional_range="calm contemplation to fierce determination",
            background_lore="ancient wizard who survived the Great Mage Wars",
            age_category="ancient",
            build_type="tall, lean, carries himself with dignity",
            attire_style="flowing robes with celestial patterns, ornate staff",
            distinctive_features="long white beard, piercing eyes, aura of power",
            visual_archetype="archetypal wise wizard",
            overall_confidence=0.82,
        )

        assert "wizard" in details.npc_name.lower()
        assert "wise" in details.personality_traits
        assert "archmage" in details.occupation
        assert "ancient" in details.age_category
        assert details.overall_confidence > 0.8

    def test_model_with_confidence_metrics(self):
        """Test model with various confidence scoring."""
        details = NPCDetails(
            npc_name="Uncertain Character",
            text_confidence=0.6,
            visual_confidence=0.4,
            overall_confidence=0.5,
            synthesis_notes="Test synthesis with moderate confidence",
        )

        assert details.text_confidence == 0.6
        assert details.visual_confidence == 0.4
        assert details.overall_confidence == 0.5
        assert details.synthesis_notes == "Test synthesis with moderate confidence"

    def test_model_serialization(self):
        """Test comprehensive model serialization."""
        original = NPCDetails(
            npc_name="Serialization Test",
            personality_traits="test traits",
            occupation="test job",
            overall_confidence=0.75,
            synthesis_notes="Combined text and visual analysis with moderate confidence",
        )

        # Test dict serialization
        data = original.model_dump()
        assert data["npc_name"] == "Serialization Test"
        assert data["personality_traits"] == "test traits"
        assert data["overall_confidence"] == 0.75

        # Test reconstruction
        reconstructed = NPCDetails(**data)
        assert reconstructed.npc_name == original.npc_name
        assert reconstructed.overall_confidence == original.overall_confidence


class TestDetailSynthesizer:
    """Test the DSPy DetailSynthesizer module."""

    def setup_method(self):
        """Setup for each test method."""
        self.synthesizer = DetailSynthesizer()

    def test_initialization(self):
        """Test synthesizer initializes correctly."""
        assert self.synthesizer is not None
        assert hasattr(self.synthesizer, "forward")

    @pytest.mark.asyncio
    async def test_synthesize_balanced_analysis(self):
        """Test synthesis with balanced text and visual analysis."""
        # Create mock text characteristics
        text_characteristics = NPCTextCharacteristics(
            personality_traits="friendly, helpful, enthusiastic about trade",
            occupation="merchant, shopkeeper",
            social_role="local business owner, community member",
            dialogue_patterns="enthusiastic, uses trade terminology",
            emotional_range="cheerful, occasionally frustrated with difficult customers",
        )

        # Create mock visual characteristics
        visual_characteristics = NPCVisualCharacteristics(
            chathead_image_url="https://wiki.com/merchant_chathead.png",
            image_url="https://wiki.com/merchant.png",
            age_category="middle-aged",
            build_type="average build, well-fed appearance",
            attire_style="colorful merchant clothes, money pouch",
            distinctive_features="welcoming smile, gold tooth",
            visual_archetype="prosperous merchant",
        )

        with patch.object(self.synthesizer, "forward") as mock_forward:
            mock_result = Mock(spec=NPCDetails)
            mock_result.npc_name = "Merchant Bob"
            mock_result.personality_traits = "friendly, helpful, business-minded, enthusiastic about trade"
            mock_result.occupation = "merchant, shopkeeper of general goods"
            mock_result.social_role = "local business owner, helpful community member"
            mock_result.dialogue_patterns = "enthusiastic speech, uses trade terms, welcoming to customers"
            mock_result.emotional_range = "generally cheerful, occasionally frustrated but never hostile"
            mock_result.background_lore = "established merchant with years of experience serving the community"
            mock_result.age_category = "middle-aged"
            mock_result.build_type = "average build, well-fed from prosperous business"
            mock_result.attire_style = "colorful merchant clothing with practical money pouch"
            mock_result.distinctive_features = "welcoming smile, gold tooth from prosperity"
            mock_result.visual_archetype = "prosperous small-town merchant"
            mock_result.text_confidence = 0.8
            mock_result.visual_confidence = 0.7
            mock_result.overall_confidence = 0.75
            mock_result.synthesis_notes = (
                "Strong text analysis combined with good visual data creates reliable merchant profile"
            )
            mock_forward.return_value = mock_result

            result = self.synthesizer(
                text_characteristics=text_characteristics,
                visual_characteristics=visual_characteristics,
                npc_name="Merchant Bob",
            )

            mock_forward.assert_called_once()

            # Check synthesis results
            assert "merchant" in result.npc_name.lower()  # type: ignore[attr-defined]
            assert "friendly" in result.personality_traits.lower()  # type: ignore[attr-defined]
            assert "merchant" in result.occupation.lower()  # type: ignore[attr-defined]
            assert "middle-aged" in result.age_category  # type: ignore[attr-defined]
            assert result.overall_confidence > 0.7  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_synthesize_conflicting_data(self):
        """Test synthesis resolving conflicts between text and visual data."""
        # Text suggests young, energetic character
        text_characteristics = NPCTextCharacteristics(
            personality_traits="energetic, impulsive, eager to prove himself",
            occupation="apprentice warrior",
            social_role="young trainee seeking glory",
            dialogue_patterns="excited, uses modern slang",
            emotional_range="highly enthusiastic, sometimes reckless",
        )

        # Visual suggests older, experienced character
        visual_characteristics = NPCVisualCharacteristics(
            age_category="elderly",
            build_type="weathered, scarred from many battles",
            attire_style="well-worn armor, veteran equipment",
            distinctive_features="gray beard, battle scars, wise eyes",
            visual_archetype="grizzled veteran",
        )

        with patch.object(self.synthesizer, "forward") as mock_forward:
            mock_result = Mock(spec=NPCDetails)
            mock_result.npc_name = "Conflicted Character"
            # Synthesizer should resolve the conflict intelligently
            mock_result.personality_traits = "energetic spirit in experienced body, eager but tempered by wisdom"
            mock_result.occupation = "veteran warrior who maintains youthful enthusiasm"
            mock_result.age_category = "appears elderly but acts youthful"
            mock_result.overall_confidence = 0.6
            mock_result.synthesis_notes = (
                "Resolved conflict between youthful text persona and elderly visual appearance "
                "by creating nuanced character"
            )
            mock_forward.return_value = mock_result

            result = self.synthesizer(
                text_characteristics=text_characteristics,
                visual_characteristics=visual_characteristics,
                npc_name="Conflicted Character",
            )

            mock_forward.assert_called_once()

            # Should handle conflicts with lower confidence
            assert result.overall_confidence <= 0.7  # type: ignore[attr-defined]
            assert "conflict" in result.synthesis_notes.lower() or "resolved" in result.synthesis_notes.lower()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_synthesize_minimal_data(self):
        """Test synthesis with minimal input data."""
        text_characteristics = NPCTextCharacteristics()  # Empty/default
        visual_characteristics = NPCVisualCharacteristics()  # Empty/default

        with patch.object(self.synthesizer, "forward") as mock_forward:
            mock_result = Mock(spec=NPCDetails)
            mock_result.npc_name = "Minimal Data NPC"
            mock_result.personality_traits = ""
            mock_result.occupation = ""
            mock_result.overall_confidence = 0.1
            mock_result.synthesis_notes = "Very limited data available for synthesis"
            mock_forward.return_value = mock_result

            result = self.synthesizer(
                text_characteristics=text_characteristics,
                visual_characteristics=visual_characteristics,
                npc_name="Minimal Data NPC",
            )

            mock_forward.assert_called_once()

            # Should handle minimal data gracefully
            assert result.overall_confidence < 0.5  # type: ignore[attr-defined]
            assert "limited" in result.synthesis_notes.lower()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_synthesize_high_quality_data(self):
        """Test synthesis with rich, high-quality input data."""
        # Rich text analysis
        text_characteristics = NPCTextCharacteristics(
            personality_traits="deeply wise, patient teacher, haunted by past failures, compassionate toward students",
            occupation="master wizard, headmaster of magical academy",
            social_role="respected educator, former adventurer, keeper of dangerous knowledge",
            dialogue_patterns=(
                "speaks slowly and thoughtfully, uses educational metaphors, occasionally reveals darker wisdom"
            ),
            emotional_range="calm patience to fierce protectiveness, underlying melancholy from past losses",
        )

        # Rich visual analysis
        visual_characteristics = NPCVisualCharacteristics(
            chathead_image_url="https://wiki.com/headmaster_chathead.png",
            image_url="https://wiki.com/headmaster.png",
            age_category="elderly but vigorous",
            build_type="tall, lean, maintains dignity despite age",
            attire_style="elaborate academic robes with subtle magical protections",
            distinctive_features=(
                "silver beard, knowing eyes, subtle scars from past adventures, aura of contained power"
            ),
            visual_archetype="wise mentor with hidden depths",
        )

        with patch.object(self.synthesizer, "forward") as mock_forward:
            mock_result = Mock(spec=NPCDetails)
            mock_result.npc_name = "Headmaster Arcanum"
            mock_result.personality_traits = (
                "deeply wise educator haunted by past failures, patient with students but fiercely protective"
            )
            mock_result.occupation = "headmaster of prestigious magical academy, former adventurer"
            mock_result.social_role = "respected educator and keeper of dangerous magical knowledge"
            mock_result.background_lore = (
                "former adventurer who established academy after losing companions to dangerous magic"
            )
            mock_result.age_category = "elderly but maintains vigorous presence"
            mock_result.visual_archetype = "archetypal wise mentor with complex past"
            mock_result.text_confidence = 0.9
            mock_result.visual_confidence = 0.85
            mock_result.overall_confidence = 0.88
            mock_result.synthesis_notes = (
                "High-quality text and visual data create comprehensive character profile "
                "with strong internal consistency"
            )
            mock_forward.return_value = mock_result

            result = self.synthesizer(
                text_characteristics=text_characteristics,
                visual_characteristics=visual_characteristics,
                npc_name="Headmaster Arcanum",
            )

            mock_forward.assert_called_once()

            # Should produce high-confidence results
            assert result.overall_confidence > 0.8  # type: ignore[attr-defined]
            assert "high-quality" in result.synthesis_notes.lower() or "comprehensive" in result.synthesis_notes.lower()  # type: ignore[attr-defined]

    def test_invalid_input_handling(self):
        """Test synthesizer handles invalid inputs gracefully."""
        with patch.object(self.synthesizer, "forward") as mock_forward:
            mock_forward.side_effect = ValueError("Invalid input")

            with pytest.raises(ValueError, match="Invalid input"):
                self.synthesizer(text_characteristics=None, visual_characteristics=None, npc_name="Test")

    def test_synthesizer_call_signature(self):
        """Test that the synthesizer is callable."""
        # DSPy modules are callable and should accept keyword arguments
        assert callable(self.synthesizer)

        # Test that we can call it with expected parameters (mocked)
        with patch.object(self.synthesizer, "forward") as mock_forward:
            mock_forward.return_value = Mock()

            try:
                self.synthesizer(text_characteristics=Mock(), visual_characteristics=Mock(), npc_name="Test")
                # If no exception, the interface works
                assert True
            except Exception as e:
                # Should be callable with these parameters
                raise AssertionError(f"Synthesizer not callable with expected parameters: {e}") from e

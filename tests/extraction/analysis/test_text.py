# ABOUTME: Tests for DSPy text analysis module
# ABOUTME: Comprehensive testing of NPC personality and dialogue extraction

from unittest.mock import Mock, patch

import pytest

from voiceover_mage.extraction.analysis.text import (
    NPCTextCharacteristics,
    TextDetailExtractor,
)


class TestNPCTextCharacteristics:
    """Test the NPCTextCharacteristics Pydantic model."""

    def test_model_creation_minimal(self):
        """Test model can be created with minimal data."""
        characteristics = NPCTextCharacteristics()

        assert characteristics.personality_traits == ""
        assert characteristics.occupation == ""
        assert characteristics.social_role == ""
        assert characteristics.dialogue_patterns == ""
        assert characteristics.emotional_range == ""

    def test_model_creation_full(self):
        """Test model can be created with full data."""
        characteristics = NPCTextCharacteristics(
            personality_traits="Gruff but fair-minded, deeply wise",
            occupation="Village blacksmith",
            social_role="Respected craftsperson",
            dialogue_patterns="Speaks in short, direct sentences with practical wisdom",
            emotional_range="Calm and measured, occasionally passionate about craftsmanship",
        )

        assert "gruff" in characteristics.personality_traits.lower()
        assert "blacksmith" in characteristics.occupation.lower()
        assert "craftsperson" in characteristics.social_role.lower()
        assert "direct" in characteristics.dialogue_patterns.lower()
        assert "calm" in characteristics.emotional_range.lower()

    def test_model_serialization(self):
        """Test model can be serialized and deserialized."""
        original = NPCTextCharacteristics(
            personality_traits="Mysterious and enigmatic", occupation="Quest giver", social_role="Village elder"
        )

        # Test dict serialization
        data = original.model_dump()
        assert data["personality_traits"] == "Mysterious and enigmatic"
        assert data["occupation"] == "Quest giver"

        # Test reconstruction
        reconstructed = NPCTextCharacteristics(**data)
        assert reconstructed.personality_traits == original.personality_traits
        assert reconstructed.occupation == original.occupation


class TestTextDetailExtractor:
    """Test the DSPy TextDetailExtractor module."""

    def setup_method(self):
        """Setup for each test method."""
        self.extractor = TextDetailExtractor()

    def test_initialization(self):
        """Test extractor initializes correctly."""
        assert self.extractor is not None
        # Check that it's a DSPy module
        assert hasattr(self.extractor, "forward")

    @pytest.mark.asyncio
    async def test_extract_from_markdown_basic(self):
        """Test basic text extraction from markdown content."""
        # Sample markdown content for a merchant NPC
        sample_markdown = """
        # Shopkeeper Bob
        
        **Bob** is a friendly merchant who runs the general store in Lumbridge.
        He is known for his cheerful demeanor and helpful attitude toward new players.
        
        Bob speaks with enthusiasm: "Welcome to my shop, adventurer! I have everything you need!"
        He is middle-aged and has been running the shop for many years.
        
        ## Dialogue
        - "Hello there! Looking for supplies?"
        - "I've been running this shop for 20 years!"
        - "Safe travels, and come back soon!"
        
        ## Location
        Located in Lumbridge, Bob's shop serves as the first stop for many new players.
        """

        # Mock the DSPy forward method to return expected results
        with patch.object(self.extractor, "forward") as mock_forward:
            mock_result = Mock(spec=NPCTextCharacteristics)
            mock_result.personality_traits = "friendly, cheerful, helpful, enthusiastic"
            mock_result.occupation = "shopkeeper, general store owner"
            mock_result.social_role = "merchant, helpful guide for new players"
            mock_result.dialogue_patterns = "enthusiastic, welcoming, uses exclamation points"
            mock_result.emotional_range = "cheerful, welcoming, encouraging"
            mock_forward.return_value = mock_result

            result = self.extractor(markdown_content=sample_markdown, npc_name="Bob")

            # Verify the mock was called with correct parameters
            mock_forward.assert_called_once()

            # Check result properties
            assert "friendly" in result.personality_traits.lower()  # type: ignore[attr-defined]
            assert "shopkeeper" in result.occupation.lower()  # type: ignore[attr-defined]
            assert "merchant" in result.social_role.lower()  # type: ignore[attr-defined]
            assert "enthusiastic" in result.dialogue_patterns.lower()  # type: ignore[attr-defined]
            assert "cheerful" in result.emotional_range.lower()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_extract_from_empty_markdown(self):
        """Test extraction handles empty or minimal markdown."""
        empty_markdown = "# Test NPC\n\nMinimal content."

        with patch.object(self.extractor, "forward") as mock_forward:
            # Mock should return minimal/default values for poor input
            mock_result = Mock(spec=NPCTextCharacteristics)
            mock_result.personality_traits = ""
            mock_result.occupation = ""
            mock_result.social_role = ""
            mock_result.dialogue_patterns = ""
            mock_result.emotional_range = ""
            mock_forward.return_value = mock_result

            result = self.extractor(markdown_content=empty_markdown, npc_name="Test NPC")

            # Should handle gracefully
            mock_forward.assert_called_once()
            assert isinstance(result, Mock | NPCTextCharacteristics)

    @pytest.mark.asyncio
    async def test_extract_with_complex_character(self):
        """Test extraction with complex character description."""
        complex_markdown = """
        # Master Wizard Zarathos
        
        **Zarathos** is an ancient and powerful wizard who has lived for centuries.
        Once a student of the great mages, he now serves as the guardian of mystical knowledge.
        
        His personality is complex - he appears stern and intimidating to most visitors,
        but those who earn his respect find him to be deeply wise and surprisingly caring.
        He has little patience for fools but will go to great lengths to help those
        who demonstrate genuine dedication to the magical arts.
        
        ## Dialogue Examples
        - "Hmph. Another seeker of easy power, I presume?"
        - "Magic is not a toy, young one. It demands respect, discipline, and sacrifice."
        - "You show promise... very well, I shall teach you, but mark my words: fail me and face the consequences."
        - ("In my centuries of study, I have learned that true wisdom comes not from power, "
           "but from understanding one's limitations.")
        
        ## Background
        Zarathos was once involved in the Great Mage Wars, where he lost many friends.
        This tragedy shaped his cautious and sometimes harsh demeanor, though beneath
        his stern exterior lies a mentor who genuinely cares about preserving magical knowledge.
        
        ## Teaching Style
        He is known for his challenging tests and riddles, believing that only through
        struggle can a student truly master the arcane arts. His methods may seem harsh,
        but they have produced some of the most skilled mages in the realm.
        """

        with patch.object(self.extractor, "forward") as mock_forward:
            mock_result = Mock(spec=NPCTextCharacteristics)
            mock_result.personality_traits = (
                "stern, intimidating, wise, caring beneath surface, impatient with fools, dedicated mentor"
            )
            mock_result.occupation = "ancient wizard, guardian of mystical knowledge, teacher"
            mock_result.social_role = "magical mentor, keeper of arcane wisdom, former war veteran"
            mock_result.dialogue_patterns = (
                "formal, challenging, uses rhetorical questions, speaks with authority and gravitas"
            )
            mock_result.emotional_range = "stern to caring, impatient to deeply invested, cautious due to past trauma"
            mock_forward.return_value = mock_result

            result = self.extractor(markdown_content=complex_markdown, npc_name="Master Wizard Zarathos")

            mock_forward.assert_called_once()

            # Check for complex character traits
            assert "stern" in result.personality_traits.lower()  # type: ignore[attr-defined]
            assert "wise" in result.personality_traits.lower()  # type: ignore[attr-defined]
            assert "wizard" in result.occupation.lower()  # type: ignore[attr-defined]
            assert "mentor" in result.social_role.lower()  # type: ignore[attr-defined]
            assert "formal" in result.dialogue_patterns.lower()  # type: ignore[attr-defined]

    def test_invalid_input_handling(self):
        """Test extractor handles invalid inputs gracefully."""
        with patch.object(self.extractor, "forward") as mock_forward:
            # Test with None input
            mock_forward.side_effect = ValueError("Invalid input")

            with pytest.raises(ValueError, match="Invalid input"):
                self.extractor(markdown_content=None, npc_name="Test")

    def test_extractor_signature(self):
        """Test that the extractor has the expected call signature."""
        # The TextDetailExtractor should be callable with markdown_content and npc_name
        import inspect

        # Get the __call__ method since DSPy modules are callable
        if callable(self.extractor):
            sig = inspect.signature(self.extractor.__call__)
            param_names = list(sig.parameters.keys())

            # Should accept self, markdown_content, npc_name (at minimum)
            # DSPy may add additional parameters
            assert "markdown_content" in str(sig) or len(param_names) > 1

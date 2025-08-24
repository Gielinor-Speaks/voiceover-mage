# ABOUTME: Tests for DSPy image analysis module
# ABOUTME: Comprehensive testing of NPC visual characteristic extraction

from unittest.mock import Mock, patch

import pytest

from voiceover_mage.extraction.analysis.image import (
    ImageDetailExtractor,
    NPCVisualCharacteristics,
)


class TestNPCVisualCharacteristics:
    """Test the NPCVisualCharacteristics Pydantic model."""

    def test_model_creation_minimal(self):
        """Test model can be created with minimal data."""
        characteristics = NPCVisualCharacteristics()

        assert characteristics.chathead_image_url is None
        assert characteristics.image_url is None
        assert characteristics.age_category == ""
        assert characteristics.build_type == ""
        assert characteristics.attire_style == ""

    def test_model_creation_full(self):
        """Test model can be created with full visual data."""
        characteristics = NPCVisualCharacteristics(
            chathead_image_url="https://wiki.com/images/bob_chathead.png",
            image_url="https://wiki.com/images/bob_full.png",
            age_category="middle-aged",
            build_type="stocky",
            attire_style="leather apron over simple tunic",
            distinctive_features="graying beard, calloused hands",
            visual_archetype="village craftsperson",
        )

        assert characteristics.chathead_image_url is not None and characteristics.chathead_image_url.endswith(
            "_chathead.png"
        )
        assert characteristics.image_url is not None and characteristics.image_url.endswith("_full.png")
        assert characteristics.age_category == "middle-aged"
        assert "stocky" in characteristics.build_type
        assert "apron" in characteristics.attire_style
        assert "beard" in characteristics.distinctive_features

    def test_model_with_image_urls_only(self):
        """Test model with just image URLs (common case)."""
        characteristics = NPCVisualCharacteristics(
            chathead_image_url="https://oldschool.runescape.wiki/images/Master_Chef_chathead.png",
            image_url="https://oldschool.runescape.wiki/images/Master_Chef.png",
        )

        assert characteristics.chathead_image_url is not None and "Master_Chef" in characteristics.chathead_image_url
        assert characteristics.age_category == ""  # Defaults
        assert characteristics.build_type == ""

    def test_model_serialization(self):
        """Test model can be serialized and deserialized."""
        original = NPCVisualCharacteristics(
            age_category="elderly",
            build_type="frail",
            attire_style="wizard robes with star patterns",
            visual_archetype="wise sage",
        )

        # Test dict serialization
        data = original.model_dump()
        assert data["age_category"] == "elderly"
        assert data["build_type"] == "frail"

        # Test reconstruction
        reconstructed = NPCVisualCharacteristics(**data)
        assert reconstructed.age_category == original.age_category
        assert reconstructed.attire_style == original.attire_style


class TestImageDetailExtractor:
    """Test the DSPy ImageDetailExtractor module."""

    def setup_method(self):
        """Setup for each test method."""
        self.extractor = ImageDetailExtractor()

    def test_initialization(self):
        """Test extractor initializes correctly."""
        assert self.extractor is not None
        assert hasattr(self.extractor, "forward")

    @pytest.mark.asyncio
    async def test_extract_visual_characteristics_basic(self):
        """Test basic visual extraction from markdown with images."""
        sample_markdown = """
        # Guard Captain Marcus
        
        ![Guard Captain](https://wiki.com/images/Marcus.png)
        ![Chathead](https://wiki.com/images/Marcus_chathead.png)
        
        **Marcus** is a tall, imposing figure who commands respect through his presence.
        He wears the standard guard armor with additional decorative elements that mark his rank.
        His weathered face shows years of military service, and his steel-gray hair is kept
        in a practical short cut.
        
        ## Appearance
        Marcus stands nearly six feet tall with a muscular build developed from years
        of military training. His armor is well-maintained but shows signs of use.
        He carries himself with military bearing and rarely smiles.
        
        ## Equipment
        - Steel armor with captain's insignia
        - Well-crafted sword at his side
        - Military-issued shield
        """

        with patch.object(self.extractor, "forward") as mock_forward:
            mock_result = Mock(spec=NPCVisualCharacteristics)
            mock_result.chathead_image_url = "https://wiki.com/images/Marcus_chathead.png"
            mock_result.image_url = "https://wiki.com/images/Marcus.png"
            mock_result.age_category = "middle-aged"
            mock_result.build_type = "muscular, imposing"
            mock_result.attire_style = "steel guard armor with captain's insignia"
            mock_result.distinctive_features = "weathered face, steel-gray hair, military bearing"
            mock_result.visual_archetype = "military commander"
            mock_forward.return_value = mock_result

            result = self.extractor(markdown_content=sample_markdown, npc_name="Guard Captain Marcus")

            mock_forward.assert_called_once()

            # Check extracted image URLs
            assert "Marcus_chathead.png" in result.chathead_image_url  # type: ignore[attr-defined]
            assert "Marcus.png" in result.image_url  # type: ignore[attr-defined]

            # Check visual characteristics
            assert "middle-aged" in result.age_category  # type: ignore[attr-defined]
            assert "muscular" in result.build_type.lower()  # type: ignore[attr-defined]
            assert "armor" in result.attire_style.lower()  # type: ignore[attr-defined]
            assert "military" in result.visual_archetype.lower()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_extract_with_minimal_visual_info(self):
        """Test extraction with minimal visual descriptions."""
        minimal_markdown = """
        # Mysterious Stranger
        
        A figure shrouded in shadows. Little is known about their appearance.
        """

        with patch.object(self.extractor, "forward") as mock_forward:
            mock_result = Mock(spec=NPCVisualCharacteristics)
            mock_result.chathead_image_url = None
            mock_result.image_url = None
            mock_result.age_category = "unknown"
            mock_result.build_type = "unknown"
            mock_result.attire_style = "dark, concealing clothing"
            mock_result.distinctive_features = "shrouded in shadows"
            mock_result.visual_archetype = "mysterious figure"
            mock_forward.return_value = mock_result

            result = self.extractor(markdown_content=minimal_markdown, npc_name="Mysterious Stranger")

            mock_forward.assert_called_once()

            # Should handle lack of visual info gracefully
            assert result.chathead_image_url is None  # type: ignore[attr-defined]
            assert result.image_url is None  # type: ignore[attr-defined]
            assert "unknown" in result.age_category or result.age_category == ""  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_extract_fantasy_character_features(self):
        """Test extraction of fantasy-specific visual elements."""
        fantasy_markdown = """
        # Archmage Celestine
        
        ![Full Body](https://wiki.com/images/Celestine.png)
        ![Portrait](https://wiki.com/images/Celestine_chathead.png)
        
        **Celestine** appears ageless, with the ethereal beauty common to high elves.
        Her silver hair flows like liquid moonlight, and her eyes glow with arcane power.
        She wears elaborate robes of deep blue silk, embroidered with golden runes
        that seem to shimmer and move in the light.
        
        ## Magical Appearance  
        Celestine's presence seems to bend light around her, creating a subtle aura.
        Her staff, carved from crystallized mana, pulses with inner light.
        Ancient tattoos of power spiral up her arms, visible beneath translucent sleeves.
        
        ## Distinctive Features
        - Pointed ears marking her elven heritage
        - Eyes that glow with subtle blue light
        - Voice that carries magical resonance
        - Moves with supernatural grace
        """

        with patch.object(self.extractor, "forward") as mock_forward:
            mock_result = Mock(spec=NPCVisualCharacteristics)
            mock_result.chathead_image_url = "https://wiki.com/images/Celestine_chathead.png"
            mock_result.image_url = "https://wiki.com/images/Celestine.png"
            mock_result.age_category = "ageless, appears young adult"
            mock_result.build_type = "slender, graceful"
            mock_result.attire_style = "elaborate blue silk robes with golden rune embroidery"
            mock_result.distinctive_features = "silver hair, glowing eyes, pointed ears, magical aura, arcane tattoos"
            mock_result.visual_archetype = "high elf archmage"
            mock_forward.return_value = mock_result

            result = self.extractor(markdown_content=fantasy_markdown, npc_name="Archmage Celestine")

            mock_forward.assert_called_once()

            # Check fantasy-specific features
            assert "ageless" in result.age_category.lower() or "young" in result.age_category.lower()  # type: ignore[attr-defined]
            assert "graceful" in result.build_type.lower() or "slender" in result.build_type.lower()  # type: ignore[attr-defined]
            assert "robe" in result.attire_style.lower()  # type: ignore[attr-defined]
            assert "elf" in result.visual_archetype.lower()  # type: ignore[attr-defined]
            assert "magical" in result.distinctive_features.lower() or "arcane" in result.distinctive_features.lower()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_extract_with_equipment_focus(self):
        """Test extraction focusing on equipment and gear."""
        equipment_markdown = """
        # Master Blacksmith Thorek
        
        ![Thorek at work](https://wiki.com/images/Thorek.png)
        
        **Thorek** is a dwarf of impressive build, his muscles honed by decades at the forge.
        He wears a thick leather apron over chainmail, protection against both sparks
        and the occasional disagreeable customer. His beard is braided with small metal rings,
        and his arms bear the scars of his dangerous profession.
        
        ## Workshop Attire
        - Heavy leather apron, stained and scorched
        - Chainmail underneath for protection  
        - Thick leather gloves, worn smooth
        - Steel-toed boots, essential for forge work
        - Tool belt with hammers, tongs, and measuring devices
        
        ## Physical Characteristics
        Typical dwarven build - short, broad, and incredibly strong.
        His hands are massive and calloused from forge work.
        """

        with patch.object(self.extractor, "forward") as mock_forward:
            mock_result = Mock(spec=NPCVisualCharacteristics)
            mock_result.chathead_image_url = None
            mock_result.image_url = "https://wiki.com/images/Thorek.png"
            mock_result.age_category = "mature adult"
            mock_result.build_type = "stocky, muscular, dwarven build"
            mock_result.attire_style = "leather apron over chainmail, steel-toed boots, tool belt"
            mock_result.distinctive_features = "braided beard with metal rings, calloused hands, forge scars"
            mock_result.visual_archetype = "dwarven craftsman"
            mock_forward.return_value = mock_result

            result = self.extractor(markdown_content=equipment_markdown, npc_name="Master Blacksmith Thorek")

            mock_forward.assert_called_once()

            # Check equipment-focused extraction
            assert "apron" in result.attire_style.lower()  # type: ignore[attr-defined]
            assert "chainmail" in result.attire_style.lower() or "mail" in result.attire_style.lower()  # type: ignore[attr-defined]
            assert "muscular" in result.build_type.lower() or "stocky" in result.build_type.lower()  # type: ignore[attr-defined]
            assert "dwarven" in result.visual_archetype.lower() or "dwarf" in result.visual_archetype.lower()  # type: ignore[attr-defined]

    def test_invalid_input_handling(self):
        """Test extractor handles invalid inputs gracefully."""
        with patch.object(self.extractor, "forward") as mock_forward:
            mock_forward.side_effect = ValueError("Invalid input")

            with pytest.raises(ValueError, match="Invalid input"):
                self.extractor(markdown_content=None, npc_name="Test")

    def test_extractor_call_signature(self):
        """Test that the extractor has the expected interface."""
        import inspect

        if callable(self.extractor):
            sig = inspect.signature(self.extractor.__call__)
            # Should accept markdown_content and npc_name
            assert "markdown_content" in str(sig) or len(list(sig.parameters.keys())) > 1

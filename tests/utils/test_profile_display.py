"""Tests for the character profile HTML renderer."""


from voiceover_mage.core.models import NPCDetails
from voiceover_mage.utils.profile_display import render_character_profile_html


def test_render_character_profile_html_basic():
    """Test that the profile renderer generates valid HTML."""
    profile = NPCDetails(
        id=1,
        npc_name="Test NPC",
        npc_variant="Variant 1",
        personality_profile="A brave and noble knight",
        voice_characteristics="Deep and commanding voice with a formal accent",
        visual_archetype="Medieval Knight",
        background_summary="A veteran warrior with years of experience",
        social_context="Respected member of the royal guard",
        synthesis_confidence=0.85,
        synthesis_reasoning="High confidence based on detailed wiki content",
        text_confidence=0.90,
        visual_confidence=0.80,
    )

    html = render_character_profile_html(
        profile=profile,
        chathead_url="https://example.com/chathead.png",
        image_url="https://example.com/full.png",
        npc_name="Test NPC Override",
    )

    # Verify HTML structure
    assert 'class="character-portfolio"' in html
    assert "Test NPC Override" in html
    assert "(Variant 1)" in html
    assert "Medieval Knight" in html
    assert "A brave and noble knight" in html
    assert "Deep and commanding voice" in html
    assert "A veteran warrior" in html
    assert "Respected member" in html

    # Verify images are included
    assert "https://example.com/chathead.png" in html
    assert "https://example.com/full.png" in html

    # Verify confidence bars
    assert "85%" in html or "85.0%" in html
    assert "90%" in html or "90.0%" in html
    assert "80%" in html or "80.0%" in html

    # Verify reasoning section
    assert "AI Analysis Reasoning" in html
    assert "High confidence based on detailed wiki content" in html


def test_render_character_profile_html_no_images():
    """Test rendering without images."""
    profile = NPCDetails(
        id=2,
        npc_name="Simple NPC",
        npc_variant=None,
        personality_profile="A simple merchant",
        voice_characteristics="Friendly and casual voice",
        visual_archetype="Shopkeeper",
        background_summary="Runs a small shop",
        social_context="Local merchant",
        synthesis_confidence=0.75,
        synthesis_reasoning="Moderate confidence",
        text_confidence=0.70,
        visual_confidence=0.80,
    )

    html = render_character_profile_html(profile=profile)

    # Verify HTML structure
    assert 'class="character-portfolio"' in html
    assert "Simple NPC" in html
    assert "Shopkeeper" in html

    # Verify no image gallery when images aren't provided
    assert "<div class='image-gallery'>" not in html


def test_render_character_profile_html_with_variant():
    """Test rendering with NPC variant."""
    profile = NPCDetails(
        id=3,
        npc_name="Guard",
        npc_variant="Varrock",
        personality_profile="Dutiful guard",
        voice_characteristics="Stern voice",
        visual_archetype="City Guard",
        background_summary="City protector",
        social_context="Guard duty",
        synthesis_confidence=0.85,
        synthesis_reasoning="Good data",
        text_confidence=0.85,
        visual_confidence=0.85,
    )

    html = render_character_profile_html(profile=profile)

    # Verify variant is displayed
    assert "Guard" in html
    assert "(Varrock)" in html


def test_render_character_profile_html_low_confidence():
    """Test rendering with low confidence scores."""
    profile = NPCDetails(
        id=4,
        npc_name="Unknown NPC",
        npc_variant=None,
        personality_profile="Unknown",
        voice_characteristics="Unknown",
        visual_archetype="Unknown",
        background_summary="No data",
        social_context="Unknown",
        synthesis_confidence=0.45,
        synthesis_reasoning="Low confidence due to limited data",
        text_confidence=0.40,
        visual_confidence=0.50,
    )

    html = render_character_profile_html(profile=profile)

    # Verify low confidence is rendered
    assert "45%" in html or "45.0%" in html
    assert "40%" in html or "40.0%" in html
    assert "50%" in html or "50.0%" in html

    # Verify reasoning explains low confidence
    assert "Low confidence due to limited data" in html


def test_render_character_profile_html_missing_variant_field():
    """Test rendering when variant field is missing (older data compatibility)."""
    # Create a profile dict without npc_variant to simulate older data
    profile_dict = {
        "id": 5,
        "npc_name": "Legacy NPC",
        "personality_profile": "Old character",
        "voice_characteristics": "Classic voice",
        "visual_archetype": "Legacy",
        "background_summary": "Old data",
        "social_context": "Historical",
        "synthesis_confidence": 0.75,
        "synthesis_reasoning": "Legacy data",
        "text_confidence": 0.75,
        "visual_confidence": 0.75,
    }

    # Create model - it should use the default None for npc_variant
    profile = NPCDetails(**profile_dict)

    html = render_character_profile_html(profile=profile)

    # Verify HTML renders without error
    assert 'class="character-portfolio"' in html
    assert "Legacy NPC" in html
    # Variant should not appear since it's None
    assert "npc_variant" not in html.lower()
    assert "(None)" not in html


def test_render_character_profile_html_very_old_data():
    """Test rendering with very old data missing confidence fields."""

    # Simulate an old NPCDetails-like object using a mock class
    class LegacyProfile:
        """Mock legacy profile with minimal fields."""

        npc_name = "Very Old NPC"
        personality_profile = "Ancient warrior"
        voice_characteristics = "Gruff voice"
        background_summary = "Very old lore"
        social_context = "Legendary figure"

    legacy_profile = LegacyProfile()

    # This should render without crashing even though confidence fields are missing
    html = render_character_profile_html(profile=legacy_profile)

    # Verify basic structure
    assert 'class="character-portfolio"' in html
    assert "Very Old NPC" in html
    assert "Ancient warrior" in html
    assert "Gruff voice" in html

    # Confidence bars should not appear for legacy data
    assert "Analysis Confidence" not in html

    # Reasoning section should not appear
    assert "AI Analysis Reasoning" not in html


def test_render_character_profile_html_legacy_wiki_sourced_format():
    """Test rendering with legacy NPCWikiSourcedData format."""

    # Simulate NPCWikiSourcedData structure with the fields from your database
    class LegacyWikiProfile:
        """Mock legacy NPCWikiSourcedData profile."""

        npc_name = "Bob"
        personality_traits = (
            "Bob is notably prejudiced and unwelcoming towards non-human races, "
            "often expressing strong disgust and using exclusionary language."
        )
        occupation = 'Owner of "Bob\'s Brilliant Axes," a merchant selling various axes'
        social_role = "A prominent local merchant in Lumbridge"
        dialogue_patterns = (
            "His dialogue is often direct, gruff, and can become aggressive or accusatory"
        )
        emotional_range = "Bob displays a strong range of negative emotions, including intense disgust and anger"
        background_lore = "Bob was the very first non-player character added to RuneScape Classic"
        visual_archetype = "Commoner/Laborer"
        age_category = "Young adult"
        build_type = "Stocky"
        attire_style = "Simple, rustic clothing"
        chathead_image_url = "https://example.com/bob_chathead.png"
        image_url = "https://example.com/bob.png"
        text_confidence = 1.0
        visual_confidence = 0.93
        overall_confidence = 0.972

    legacy_profile = LegacyWikiProfile()

    html = render_character_profile_html(
        profile=legacy_profile,
        chathead_url=legacy_profile.chathead_image_url,
        image_url=legacy_profile.image_url,
    )

    # Verify basic structure
    assert 'class="character-portfolio"' in html
    assert "Bob" in html

    # Verify personality is mapped correctly
    assert "prejudiced and unwelcoming" in html

    # Verify voice characteristics are created from dialogue_patterns and emotional_range
    assert "direct, gruff" in html or "negative emotions" in html

    # Verify background is created from background_lore and occupation
    assert "RuneScape Classic" in html
    assert "Brilliant Axes" in html or "merchant" in html

    # Verify social context is mapped
    assert "Lumbridge" in html or "merchant" in html

    # Verify visual archetype
    assert "Commoner/Laborer" in html

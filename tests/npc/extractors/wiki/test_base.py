import httpx
import pytest

from voiceover_mage.npc.extractors.wiki.base import BaseWikiNPCExtractor
from voiceover_mage.npc.models import NPCWikiSourcedData, TrackedField


def _create_test_npc() -> NPCWikiSourcedData:
    """Create a minimal test NPC with all required fields."""
    return NPCWikiSourcedData(
        name="Test NPC",
        wiki_url="https://test.com/Test_NPC",
        chathead_image_url=None,
        image_url=None,
        gender=TrackedField(value="male", source="default", confidence=1.0, evidence="test"),
        race=TrackedField(value="Human", source="default", confidence=1.0, evidence="test"),
        age_category=TrackedField(value="unknown", source="default", confidence=1.0, evidence="test"),
        location=TrackedField(value="Test Location", source="default", confidence=1.0, evidence="test"),
        examine_text=TrackedField(value="A test NPC", source="default", confidence=1.0, evidence="test"),
        occupation=TrackedField(value="Tester", source="default", confidence=1.0, evidence="test"),
        social_class=TrackedField(value="unknown", source="default", confidence=1.0, evidence="test"),
        education_level=TrackedField(value="unknown", source="default", confidence=1.0, evidence="test"),
        personality=TrackedField(value="Test personality", source="default", confidence=1.0, evidence="test"),
        emotional_traits=TrackedField(value="Calm", source="default", confidence=1.0, evidence="test"),
        notable_quirks=TrackedField(value=None, source="default", confidence=1.0, evidence="test"),
        physical_condition=TrackedField(value="Healthy", source="default", confidence=1.0, evidence="test"),
        mental_state=TrackedField(value="Stable", source="default", confidence=1.0, evidence="test"),
        cultural_background=TrackedField(value="Unknown", source="default", confidence=1.0, evidence="test"),
        accent_region=TrackedField(value="Generic", source="default", confidence=1.0, evidence="test"),
        combat_experience=TrackedField(value="civilian", source="default", confidence=1.0, evidence="test"),
        magical_abilities=TrackedField(value="non_magical", source="default", confidence=1.0, evidence="test"),
        speech_formality=TrackedField(value="casual", source="default", confidence=1.0, evidence="test"),
        vocabulary_level=TrackedField(value="average", source="default", confidence=1.0, evidence="test"),
        speaking_pace=TrackedField(value="normal", source="default", confidence=1.0, evidence="test"),
        voice_energy=TrackedField(value="normal", source="default", confidence=1.0, evidence="test"),
        quest_importance=TrackedField(value="none", source="default", confidence=1.0, evidence="test"),
        relationships=[],
        dialogue_examples=[],
        common_phrases=[],
        description="Test description",
        voice_direction="Test voice direction",
        confidence_overall=1.0,
    )


class TestUrlParsing:
    """Test static URL parsing methods - no HTTP calls, pure logic"""

    @pytest.mark.parametrize(
        "url,expected_name,expected_variant",
        [
            ("https://oldschool.runescape.wiki/w/Bob#Variant", "Bob", "Variant"),
            ("https://oldschool.runescape.wiki/w/Alice", "Alice", None),
            ("https://oldschool.runescape.wiki/w/Complex_Name#Old", "Complex_Name", "Old"),
            ("https://oldschool.runescape.wiki/w/Makeover_Mage", "Makeover_Mage", None),
            ("invalid-url", None, None),
            ("", None, None),
            (None, None, None),
        ],
    )
    def test_url_parsing(self, url, expected_name, expected_variant):
        assert BaseWikiNPCExtractor._extract_npc_name_from_url(url) == expected_name
        assert BaseWikiNPCExtractor._extract_npc_variant_from_url(url) == expected_variant

    @pytest.mark.parametrize(
        "title,expected_name",
        [
            ("Bob#Variant", "Bob"),
            ("Simple_Name", "Simple_Name"),
            ("", None),
            (None, None),
        ],
    )
    def test_name_from_title(self, title, expected_name):
        assert BaseWikiNPCExtractor._extract_npc_name_from_title(title) == expected_name

    @pytest.mark.parametrize(
        "title,expected_variant",
        [
            ("Bob#Variant", "Variant"),
            ("Bob#Ancient_Variant", "Ancient_Variant"),
            ("Simple_Name", None),
            ("", None),
            (None, None),
        ],
    )
    def test_variant_from_title(self, title, expected_variant):
        assert BaseWikiNPCExtractor._extract_npc_variant_from_title(title) == expected_variant


class TestNPCLookup:
    """Test HTTP integration for NPC ID -> URL resolution"""

    @pytest.fixture
    def wiki_extractor(self):
        """Create concrete test implementation for HTTP testing"""

        class TestWikiExtractor(BaseWikiNPCExtractor):
            async def extract_npc_data(self, npc_id: int) -> NPCWikiSourcedData:
                # Minimal implementation - we're testing the base class
                return _create_test_npc()

        return TestWikiExtractor()

    @pytest.mark.asyncio
    async def test_get_npc_page_url_success(self, wiki_extractor, httpx_mock):
        # Mock successful wiki lookup
        httpx_mock.add_response(
            url="https://oldschool.runescape.wiki/w/Special:Lookup?type=npc&id=123",
            status_code=302,
            headers={"Location": "https://oldschool.runescape.wiki/w/Bob"},
        )

        # Final PAGE
        httpx_mock.add_response(url="https://oldschool.runescape.wiki/w/Bob", status_code=200)

        url = await wiki_extractor._get_npc_page_url(123)
        assert "Bob" in url

    @pytest.mark.asyncio
    async def test_get_npc_page_url_not_found(self, wiki_extractor, httpx_mock):
        # Mock 404 response
        httpx_mock.add_response(status_code=404)

        with pytest.raises(httpx.HTTPStatusError):
            await wiki_extractor._get_npc_page_url(999)

    def test_initialization_default_client(self, wiki_extractor):
        assert wiki_extractor.http_client is not None
        assert "Gielinor-Speaks" in wiki_extractor.http_client.headers["User-Agent"]

    def test_initialization_custom_client(self):
        custom_client = httpx.AsyncClient()

        class TestExtractor(BaseWikiNPCExtractor):
            async def extract_npc_data(self, npc_id: int) -> NPCWikiSourcedData:
                return _create_test_npc()

        extractor = TestExtractor(client=custom_client)
        assert extractor.http_client is custom_client

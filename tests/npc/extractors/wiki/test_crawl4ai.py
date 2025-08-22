# ABOUTME: Tests for Crawl4AI NPC extractor covering initialization, extraction, and error handling
# ABOUTME: Includes unit tests for configuration and integration tests with mocked crawl4ai components

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tenacity import RetryError

from voiceover_mage.npc.extractors.base import ExtractionError
from voiceover_mage.npc.extractors.wiki.crawl4ai import Crawl4AINPCExtractor
from voiceover_mage.npc.models import NPCWikiSourcedData


class TestCrawl4AINPCExtractorInitialization:
    """Test extractor initialization and configuration"""

    def test_initialization_with_api_key(self):
        extractor = Crawl4AINPCExtractor(api_key="test-key")
        assert extractor.llm_config.api_token == "test-key"
        assert extractor.headless is True

    def test_initialization_with_env_var(self, monkeypatch):
        monkeypatch.setenv("VOICEOVER_MAGE_GEMINI_API_KEY", "env-key")
        # Clear the config cache to pick up the new env var
        from voiceover_mage.config import reload_config

        reload_config()
        extractor = Crawl4AINPCExtractor()
        assert extractor.llm_config.api_token == "env-key"

    def test_initialization_custom_provider(self):
        extractor = Crawl4AINPCExtractor(api_key="test-key", llm_provider="openai/gpt-4")
        assert extractor.llm_config.provider == "openai/gpt-4"

    def test_initialization_headless_false(self):
        extractor = Crawl4AINPCExtractor(api_key="test-key", headless=False)
        assert extractor.headless is False

    def test_initialization_no_api_key_raises_error(self, monkeypatch):
        # Explicitly set empty API key in environment
        monkeypatch.setenv("VOICEOVER_MAGE_GEMINI_API_KEY", "")
        # Clear the config cache to pick up the empty env var
        from voiceover_mage.config import reload_config

        reload_config()
        with pytest.raises(ExtractionError, match="API key required"):
            Crawl4AINPCExtractor()


def _create_complete_npc_data(name: str, custom_fields: dict | None = None) -> dict:
    """Create complete NPC data as it would come from crawl4ai JSON response."""
    base_data = {
        "name": name,
        "wiki_url": f"https://oldschool.runescape.wiki/w/{name}",
        "chathead_image_url": None,
        "image_url": None,
        "gender": {"value": "male", "source": "explicit", "confidence": 0.9, "evidence": "Male NPC"},
        "race": {"value": "Human", "source": "explicit", "confidence": 0.9, "evidence": "Human race"},
        "age_category": {
            "value": "young_adult",
            "source": "inferred",
            "confidence": 0.8,
            "evidence": "Adult appearance",
        },
        "location": {"value": "Lumbridge", "source": "explicit", "confidence": 1.0, "evidence": "Lives in Lumbridge"},
        "examine_text": {"value": "A test NPC.", "source": "explicit", "confidence": 1.0, "evidence": "Examine text"},
        "occupation": {"value": "Worker", "source": "inferred", "confidence": 0.9, "evidence": "Working NPC"},
        "social_class": {"value": "commoner", "source": "inferred", "confidence": 0.7, "evidence": "Manual labor"},
        "education_level": {"value": "basic", "source": "inferred", "confidence": 0.6, "evidence": "Basic occupation"},
        "personality": {
            "value": "Friendly",
            "source": "inferred",
            "confidence": 0.8,
            "evidence": "Character description",
        },
        "emotional_traits": {
            "value": "Cheerful",
            "source": "inferred",
            "confidence": 0.7,
            "evidence": "Friendly demeanor",
        },
        "notable_quirks": {"value": None, "source": "default", "confidence": 1.0, "evidence": "No notable quirks"},
        "physical_condition": {
            "value": "Healthy",
            "source": "inferred",
            "confidence": 0.8,
            "evidence": "Active worker",
        },
        "mental_state": {"value": "Stable", "source": "inferred", "confidence": 0.8, "evidence": "Normal behavior"},
        "cultural_background": {
            "value": "Human_Misthalin",
            "source": "inferred",
            "confidence": 0.7,
            "evidence": "Lumbridge location",
        },
        "accent_region": {"value": "Generic", "source": "default", "confidence": 0.5, "evidence": "No specific accent"},
        "combat_experience": {
            "value": "civilian",
            "source": "inferred",
            "confidence": 0.8,
            "evidence": "Non-combat NPC",
        },
        "magical_abilities": {
            "value": "non_magical",
            "source": "inferred",
            "confidence": 0.9,
            "evidence": "Regular human",
        },
        "speech_formality": {"value": "casual", "source": "inferred", "confidence": 0.7, "evidence": "Friendly manner"},
        "vocabulary_level": {
            "value": "average",
            "source": "inferred",
            "confidence": 0.6,
            "evidence": "Common occupation",
        },
        "speaking_pace": {"value": "normal", "source": "default", "confidence": 0.5, "evidence": "No indication"},
        "voice_energy": {"value": "normal", "source": "default", "confidence": 0.5, "evidence": "No indication"},
        "quest_importance": {"value": "none", "source": "explicit", "confidence": 1.0, "evidence": "Not quest-related"},
        "relationships": [],
        "dialogue_examples": [],
        "common_phrases": [],
        "description": f"{name} is a test NPC.",
        "voice_direction": "Friendly voice with normal tone",
        "confidence_overall": 0.75,
    }

    if custom_fields:
        # Deep merge custom fields into base data
        for key, value in custom_fields.items():
            if isinstance(value, dict) and key in base_data and isinstance(base_data[key], dict):
                base_data[key].update(value)
            else:
                base_data[key] = value

    return base_data


class TestCrawl4AINPCExtractorExtraction:
    """Test NPC data extraction functionality"""

    @pytest.fixture
    def extractor(self):
        return Crawl4AINPCExtractor(api_key="test-key")

    @pytest.fixture
    def mock_npc_data(self):
        """Create complete mock NPC data as it would come from crawl4ai JSON response."""
        return _create_complete_npc_data(
            "Bob",
            {
                "examine_text": {
                    "value": "A skilled axeman.",
                    "source": "explicit",
                    "confidence": 1.0,
                    "evidence": "Examine text",
                },
                "occupation": {
                    "value": "Lumberjack",
                    "source": "explicit",
                    "confidence": 0.9,
                    "evidence": "Works with axes",
                },
                "personality": {
                    "value": "Friendly and hardworking",
                    "source": "inferred",
                    "confidence": 0.8,
                    "evidence": "Character description",
                },
                "description": "Bob is a lumberjack who lives in Lumbridge.",
                "voice_direction": "Friendly working-class voice with a slight cheerful tone",
            },
        )

    @pytest.fixture
    def mock_crawler_result(self, mock_npc_data):
        result = MagicMock()
        result.success = True
        result.extracted_content = json.dumps([mock_npc_data])
        result.error_message = None
        return result

    @pytest.mark.asyncio
    async def test_extract_npc_data_success(self, extractor, mock_crawler_result, mock_npc_data):
        npc_id = 123
        url = "https://oldschool.runescape.wiki/w/Bob"

        with (
            patch.object(extractor, "_get_npc_page_url", return_value=url) as mock_url_lookup,
            patch("voiceover_mage.npc.extractors.wiki.crawl4ai.AsyncWebCrawler") as mock_crawler_class,
        ):
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_crawler_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            result = await extractor.extract_npc_data(npc_id)

            mock_url_lookup.assert_called_once_with(npc_id)
            assert isinstance(result, NPCWikiSourcedData)
            assert result.name == "Bob"
            assert result.gender.value == "male"
            assert result.race.value == "Human"

    @pytest.mark.asyncio
    async def test_extract_npc_data_from_url_multiple_npcs(self, extractor):
        url = "https://oldschool.runescape.wiki/w/SomeLocation"

        npc_data_list = [
            _create_complete_npc_data(
                "Bob",
                {
                    "examine_text": {
                        "value": "A skilled axeman.",
                        "source": "explicit",
                        "confidence": 1.0,
                        "evidence": "Examine text",
                    },
                    "description": "Bob is a lumberjack.",
                    "personality": {
                        "value": "Friendly",
                        "source": "inferred",
                        "confidence": 0.8,
                        "evidence": "Character description",
                    },
                },
            ),
            _create_complete_npc_data(
                "Alice",
                {
                    "gender": {"value": "female", "source": "explicit", "confidence": 0.9, "evidence": "Female NPC"},
                    "examine_text": {
                        "value": "A local merchant.",
                        "source": "explicit",
                        "confidence": 1.0,
                        "evidence": "Examine text",
                    },
                    "description": "Alice sells goods.",
                    "personality": {
                        "value": "Business-minded",
                        "source": "inferred",
                        "confidence": 0.8,
                        "evidence": "Character description",
                    },
                },
            ),
        ]

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.extracted_content = json.dumps(npc_data_list)

        with patch("voiceover_mage.npc.extractors.wiki.crawl4ai.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            # Test the private method that handles multiple NPCs
            result = await extractor._extract_npc_data_from_url(url)

            assert len(result) == 2
            assert result[0].name == "Bob"
            assert result[1].name == "Alice"


class TestCrawl4AINPCExtractorErrorHandling:
    """Test error handling scenarios"""

    @pytest.fixture
    def extractor(self):
        return Crawl4AINPCExtractor(api_key="test-key")

    @pytest.mark.asyncio
    async def test_extract_npc_data_crawl_failure(self, extractor):
        url = "https://oldschool.runescape.wiki/w/Bob"

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Network timeout"

        with patch("voiceover_mage.npc.extractors.wiki.crawl4ai.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            with pytest.raises(RetryError) as exc_info:
                await extractor._extract_npc_data_from_url(url)

            # Verify the original exception is an ExtractionError with the right message
            assert isinstance(exc_info.value.last_attempt.exception(), ExtractionError)
            assert "Crawling failed: Network timeout" in str(exc_info.value.last_attempt.exception())

    @pytest.mark.asyncio
    async def test_extract_npc_data_no_result(self, extractor):
        url = "https://oldschool.runescape.wiki/w/Bob"

        with patch("voiceover_mage.npc.extractors.wiki.crawl4ai.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = None
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            with pytest.raises(RetryError) as exc_info:
                await extractor._extract_npc_data_from_url(url)

            # Verify the original exception is an ExtractionError with the right message
            assert isinstance(exc_info.value.last_attempt.exception(), ExtractionError)
            assert "Unexpected error during extraction: Expected CrawlResult object" in str(
                exc_info.value.last_attempt.exception()
            )

    @pytest.mark.asyncio
    async def test_extract_npc_data_invalid_json(self, extractor):
        url = "https://oldschool.runescape.wiki/w/Bob"

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.extracted_content = "invalid json content"

        with patch("voiceover_mage.npc.extractors.wiki.crawl4ai.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            with pytest.raises(RetryError) as exc_info:
                await extractor._extract_npc_data_from_url(url)

            # Verify the original exception is an ExtractionError with the right message
            assert isinstance(exc_info.value.last_attempt.exception(), ExtractionError)
            assert "Failed to parse extracted content as JSON" in str(exc_info.value.last_attempt.exception())

    @pytest.mark.asyncio
    async def test_extract_npc_data_invalid_npc_data(self, extractor):
        url = "https://oldschool.runescape.wiki/w/Bob"

        # Missing required fields
        invalid_data = [{"name": "Bob"}]  # Missing gender, race, etc.

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.extracted_content = json.dumps(invalid_data)

        with patch("voiceover_mage.npc.extractors.wiki.crawl4ai.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            with pytest.raises(RetryError) as exc_info:
                await extractor._extract_npc_data_from_url(url)

            # Verify the original exception is an ExtractionError with the right message
            assert isinstance(exc_info.value.last_attempt.exception(), ExtractionError)
            assert "Failed to validate NPC data" in str(exc_info.value.last_attempt.exception())

    @pytest.mark.asyncio
    async def test_extract_npc_data_unexpected_exception(self, extractor):
        url = "https://oldschool.runescape.wiki/w/Bob"

        with patch("voiceover_mage.npc.extractors.wiki.crawl4ai.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler_class.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(RetryError) as exc_info:
                await extractor._extract_npc_data_from_url(url)

            # Verify the original exception is an ExtractionError with the right message
            assert isinstance(exc_info.value.last_attempt.exception(), ExtractionError)
            assert "Unexpected error during extraction" in str(exc_info.value.last_attempt.exception())

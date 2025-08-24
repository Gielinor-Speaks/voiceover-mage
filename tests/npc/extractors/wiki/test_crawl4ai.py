# ABOUTME: Tests for Crawl4AI NPC extractor covering initialization, extraction, and error handling
# ABOUTME: Includes unit tests for configuration and integration tests with mocked crawl4ai components

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tenacity import RetryError

from voiceover_mage.core.models import NPCWikiSourcedData
from voiceover_mage.extraction.base import ExtractionError
from voiceover_mage.extraction.wiki.crawl4ai import Crawl4AINPCExtractor


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
    """Create complete NPC data matching the new NPCWikiSourcedData model structure."""
    base_data = {
        "name": {"value": name, "source": "explicit", "confidence": 1.0, "evidence": f"NPC name: {name}"},
        "variant": {"value": None, "source": "default", "confidence": 1.0, "evidence": "No variant specified"},
        "occupation": {
            "value": "Worker",
            "source": "inferred",
            "confidence": 0.8,
            "evidence": "Appears to be a worker",
        },
        "location": {"value": "Lumbridge", "source": "explicit", "confidence": 1.0, "evidence": "Located in Lumbridge"},
        "personality_summary": {
            "value": "Friendly and helpful",
            "source": "inferred",
            "confidence": 0.7,
            "evidence": "Friendly demeanor",
        },
        "dialogue_style": {
            "value": "Casual and approachable",
            "source": "inferred",
            "confidence": 0.6,
            "evidence": "Speaking style",
        },
        "appearance": {
            "value": "Standard human appearance",
            "source": "inferred",
            "confidence": 0.5,
            "evidence": "Visual description",
        },
        "age_estimate": {"value": "middle-aged", "source": "inferred", "confidence": 0.6, "evidence": "Age appearance"},
        "quest_involvement": {"value": [], "source": "explicit", "confidence": 1.0, "evidence": "No quest involvement"},
        "game_significance": {
            "value": None,
            "source": "default",
            "confidence": 1.0,
            "evidence": "No special significance",
        },
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
                "occupation": {
                    "value": "Lumberjack",
                    "source": "explicit",
                    "confidence": 0.9,
                    "evidence": "Works with axes - a skilled axeman",
                },
                "personality_summary": {
                    "value": "Friendly and hardworking",
                    "source": "inferred",
                    "confidence": 0.8,
                    "evidence": "Character description",
                },
                "location": {
                    "value": "Lumbridge",
                    "source": "explicit",
                    "confidence": 1.0,
                    "evidence": "Lives in Lumbridge",
                },
                "dialogue_style": {
                    "value": "Friendly working-class tone",
                    "source": "inferred",
                    "confidence": 0.7,
                    "evidence": "Cheerful and approachable",
                },
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
            patch("voiceover_mage.extraction.wiki.crawl4ai.AsyncWebCrawler") as mock_crawler_class,
        ):
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_crawler_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            result = await extractor.extract_npc_data(npc_id)

            mock_url_lookup.assert_called_once_with(npc_id)
            assert isinstance(result, NPCWikiSourcedData)
            assert result.name.value == "Bob"
            assert result.occupation.value == "Lumberjack"
            assert result.location.value == "Lumbridge"

    @pytest.mark.asyncio
    async def test_extract_npc_data_from_url_multiple_npcs(self, extractor):
        url = "https://oldschool.runescape.wiki/w/SomeLocation"

        npc_data_list = [
            _create_complete_npc_data(
                "Bob",
                {
                    "occupation": {
                        "value": "Lumberjack",
                        "source": "explicit",
                        "confidence": 1.0,
                        "evidence": "A skilled axeman",
                    },
                    "personality_summary": {
                        "value": "Friendly lumberjack",
                        "source": "inferred",
                        "confidence": 0.8,
                        "evidence": "Character description",
                    },
                },
            ),
            _create_complete_npc_data(
                "Alice",
                {
                    "occupation": {
                        "value": "Merchant",
                        "source": "explicit",
                        "confidence": 0.9,
                        "evidence": "A local merchant",
                    },
                    "personality_summary": {
                        "value": "Business-minded merchant",
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

        with patch("voiceover_mage.extraction.wiki.crawl4ai.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            # Test the private method that handles multiple NPCs
            result = await extractor._extract_npc_data_from_url(url)

            assert len(result) == 2
            assert result[0].name.value == "Bob"
            assert result[1].name.value == "Alice"


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

        with patch("voiceover_mage.extraction.wiki.crawl4ai.AsyncWebCrawler") as mock_crawler_class:
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

        with patch("voiceover_mage.extraction.wiki.crawl4ai.AsyncWebCrawler") as mock_crawler_class:
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

        with patch("voiceover_mage.extraction.wiki.crawl4ai.AsyncWebCrawler") as mock_crawler_class:
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

        with patch("voiceover_mage.extraction.wiki.crawl4ai.AsyncWebCrawler") as mock_crawler_class:
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

        with patch("voiceover_mage.extraction.wiki.crawl4ai.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler_class.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(RetryError) as exc_info:
                await extractor._extract_npc_data_from_url(url)

            # Verify the original exception is an ExtractionError with the right message
            assert isinstance(exc_info.value.last_attempt.exception(), ExtractionError)
            assert "Unexpected error during extraction" in str(exc_info.value.last_attempt.exception())

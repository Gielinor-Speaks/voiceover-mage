# ABOUTME: Tests for Crawl4AI NPC extractor covering initialization, extraction, and error handling
# ABOUTME: Includes unit tests for configuration and integration tests with mocked crawl4ai components

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tenacity import RetryError

from voiceover_mage.npc.extractors.base import ExtractionError
from voiceover_mage.npc.extractors.wiki.crawl4ai import Crawl4AINPCExtractor
from voiceover_mage.npc.models import Gender, NPCWikiSourcedData


class TestCrawl4AINPCExtractorInitialization:
    """Test extractor initialization and configuration"""
    
    def test_initialization_with_api_key(self):
        extractor = Crawl4AINPCExtractor(api_key="test-key")
        assert extractor.llm_config.api_token == "test-key"
        assert extractor.headless is True
    
    def test_initialization_with_env_var(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "env-key")
        extractor = Crawl4AINPCExtractor()
        assert extractor.llm_config.api_token == "env-key"
    
    def test_initialization_custom_provider(self):
        extractor = Crawl4AINPCExtractor(api_key="test-key", llm_provider="openai/gpt-4")
        assert extractor.llm_config.provider == "openai/gpt-4"
    
    def test_initialization_headless_false(self):
        extractor = Crawl4AINPCExtractor(api_key="test-key", headless=False)
        assert extractor.headless is False
    
    def test_initialization_no_api_key_raises_error(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(ExtractionError, match="API key required"):
            Crawl4AINPCExtractor()


class TestCrawl4AINPCExtractorExtraction:
    """Test NPC data extraction functionality"""
    
    @pytest.fixture
    def extractor(self):
        return Crawl4AINPCExtractor(api_key="test-key")
    
    @pytest.fixture
    def mock_npc_data(self):
        return {
            "name": "Bob",
            "gender": "male",
            "race": "Human",
            "location": "Lumbridge",
            "examine_text": "A skilled axeman.",
            "description": "Bob is a lumberjack who lives in Lumbridge.",
            "personality": "Friendly and hardworking"
        }
    
    @pytest.fixture
    def mock_crawler_result(self, mock_npc_data):
        result = MagicMock()
        result.success = True
        result.extracted_content = json.dumps([mock_npc_data])
        result.error_message = None
        return result
    
    @pytest.mark.asyncio
    async def test_extract_npc_data_success(self, extractor, mock_crawler_result, mock_npc_data):
        url = "https://oldschool.runescape.wiki/w/Bob"
        
        with patch('voiceover_mage.npc.extractors.wiki.crawl4ai.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_crawler_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
            
            result = await extractor.extract_npc_data(url)
            
            assert len(result) == 1
            assert isinstance(result[0], NPCWikiSourcedData)
            assert result[0].name == "Bob"
            assert result[0].gender == Gender.MALE
            assert result[0].race == "Human"
    
    @pytest.mark.asyncio
    async def test_extract_npc_data_multiple_npcs(self, extractor):
        url = "https://oldschool.runescape.wiki/w/SomeLocation"
        
        npc_data_list = [
            {
                "name": "Bob",
                "gender": "male",
                "race": "Human",
                "location": "Lumbridge",
                "examine_text": "A skilled axeman.",
                "description": "Bob is a lumberjack.",
                "personality": "Friendly"
            },
            {
                "name": "Alice",
                "gender": "female", 
                "race": "Human",
                "location": "Lumbridge",
                "examine_text": "A local merchant.",
                "description": "Alice sells goods.",
                "personality": "Business-minded"
            }
        ]
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.extracted_content = json.dumps(npc_data_list)
        
        with patch('voiceover_mage.npc.extractors.wiki.crawl4ai.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
            
            result = await extractor.extract_npc_data(url)
            
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
        
        with patch('voiceover_mage.npc.extractors.wiki.crawl4ai.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
            
            with pytest.raises(RetryError) as exc_info:
                await extractor.extract_npc_data(url)
            
            # Verify the original exception is an ExtractionError with the right message
            assert isinstance(exc_info.value.last_attempt.exception(), ExtractionError)
            assert "Crawling failed: Network timeout" in str(exc_info.value.last_attempt.exception())
    
    @pytest.mark.asyncio
    async def test_extract_npc_data_no_result(self, extractor):
        url = "https://oldschool.runescape.wiki/w/Bob"
        
        with patch('voiceover_mage.npc.extractors.wiki.crawl4ai.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = None
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
            
            with pytest.raises(RetryError) as exc_info:
                await extractor.extract_npc_data(url)
            
            # Verify the original exception is an ExtractionError with the right message
            assert isinstance(exc_info.value.last_attempt.exception(), ExtractionError)
            assert "Crawling failed: No result returned" in str(exc_info.value.last_attempt.exception())
    
    @pytest.mark.asyncio
    async def test_extract_npc_data_invalid_json(self, extractor):
        url = "https://oldschool.runescape.wiki/w/Bob"
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.extracted_content = "invalid json content"
        
        with patch('voiceover_mage.npc.extractors.wiki.crawl4ai.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
            
            with pytest.raises(RetryError) as exc_info:
                await extractor.extract_npc_data(url)
            
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
        
        with patch('voiceover_mage.npc.extractors.wiki.crawl4ai.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
            
            with pytest.raises(RetryError) as exc_info:
                await extractor.extract_npc_data(url)
            
            # Verify the original exception is an ExtractionError with the right message
            assert isinstance(exc_info.value.last_attempt.exception(), ExtractionError)
            assert "Failed to validate NPC data" in str(exc_info.value.last_attempt.exception())
    
    @pytest.mark.asyncio
    async def test_extract_npc_data_unexpected_exception(self, extractor):
        url = "https://oldschool.runescape.wiki/w/Bob"
        
        with patch('voiceover_mage.npc.extractors.wiki.crawl4ai.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler_class.side_effect = RuntimeError("Unexpected error")
            
            with pytest.raises(RetryError) as exc_info:
                await extractor.extract_npc_data(url)
            
            # Verify the original exception is an ExtractionError with the right message
            assert isinstance(exc_info.value.last_attempt.exception(), ExtractionError)
            assert "Unexpected error during extraction" in str(exc_info.value.last_attempt.exception())
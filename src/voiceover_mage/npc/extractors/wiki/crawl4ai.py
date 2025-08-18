# ABOUTME: Crawl4AI-based implementation of NPC data extraction
# ABOUTME: Uses crawl4ai library with LLM extraction for scraping RuneScape wiki

import json
import os

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig, LLMConfig, LLMExtractionStrategy
from tenacity import retry, stop_after_attempt

from voiceover_mage.npc.extractors.base import ExtractionError
from voiceover_mage.npc.extractors.wiki.base import BaseWikiNPCExtractor
from voiceover_mage.npc.models import RawNPCData


class Crawl4AINPCExtractor(BaseWikiNPCExtractor):
    """NPC data extractor using crawl4ai with LLM extraction."""

    def __init__(
        self, api_key: str | None = None, llm_provider: str = "gemini/gemini-2.5-flash-lite", headless: bool = True
    ):
        """Initialize the extractor.

        Args:
            api_key: API key for the LLM provider (defaults to GEMINI_API_KEY env var)
            llm_provider: LLM provider string for crawl4ai
            headless: Whether to run browser in headless mode
        """
        super().__init__()
        
        if not api_key and not os.getenv("GEMINI_API_KEY"):
            raise ExtractionError("API key required - set GEMINI_API_KEY or pass api_key parameter")

        self.llm_config = LLMConfig(provider=llm_provider, api_token=api_key or os.getenv("GEMINI_API_KEY"))
        self.headless = headless

    @retry(stop=stop_after_attempt(3))
    async def extract_npc_data(self, url: str) -> list[RawNPCData]:
        """Extract NPC data from the given URL using crawl4ai."""
        llm_strategy = LLMExtractionStrategy(
            llm_config=self.llm_config,
            schema=RawNPCData.model_json_schema(),
            extraction_type="schema",
            instruction=(
                f"You are provided with an NPC's web page. You must extract a single NPC data object "
                f"to get a comprehensive profile of the main NPC: {self._extract_npc_name_from_url(url)}"
            ),
            chunk_token_threshold=1000,
            overlap_rate=0.0,
            apply_chunking=False,
            input_format="markdown",
            extra_args={"temperature": 0.0, "max_tokens": 800},
        )

        crawl_config = CrawlerRunConfig(extraction_strategy=llm_strategy, cache_mode=CacheMode.BYPASS)
        browser_cfg = BrowserConfig(headless=self.headless)

        try:
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url, config=crawl_config)

                if not result:
                    raise ExtractionError("Crawling failed: No result returned")

                elif not result.success:
                    raise ExtractionError(f"Crawling failed: {result.error_message}")

                try:
                    data = json.loads(result.extracted_content)
                except json.JSONDecodeError as e:
                    raise ExtractionError(f"Failed to parse extracted content as JSON: {e}") from e

                npc_objects = []
                for item in data:
                    try:
                        npc_data = RawNPCData(**item)
                        npc_objects.append(npc_data)
                    except Exception as e:
                        raise ExtractionError(f"Failed to validate NPC data: {e}") from e

                return npc_objects

        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Unexpected error during extraction: {e}") from e

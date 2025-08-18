# ABOUTME: Crawl4AI-based implementation of NPC data extraction
# ABOUTME: Uses crawl4ai library with LLM extraction for scraping RuneScape wiki

import json
import os

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig, LLMConfig, LLMExtractionStrategy
from tenacity import retry, stop_after_attempt

from voiceover_mage.lib.logging import (
    get_logger,
    log_api_call,
    log_extraction_step,
    suppress_library_output,
)
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
        self.logger = get_logger(__name__)
        
        if not api_key and not os.getenv("GEMINI_API_KEY"):
            raise ExtractionError("API key required - set GEMINI_API_KEY or pass api_key parameter")

        self.llm_config = LLMConfig(provider=llm_provider, api_token=api_key or os.getenv("GEMINI_API_KEY"))
        self.headless = headless
        
        self.logger.info(
            "Initialized Crawl4AI extractor",
            llm_provider=llm_provider,
            headless=headless
        )

    @retry(stop=stop_after_attempt(3))
    @log_api_call("crawl4ai")
    @log_extraction_step("extract_npc_data")
    async def extract_npc_data(self, url: str) -> list[RawNPCData]:
        """Extract NPC data from the given URL using crawl4ai."""
        npc_name = self._extract_npc_name_from_url(url)
        
        self.logger.info(
            "Configuring LLM extraction strategy",
            npc_name=npc_name,
            url=url,
            llm_provider=self.llm_config.provider
        )
        
        llm_strategy = LLMExtractionStrategy(
            llm_config=self.llm_config,
            schema=RawNPCData.model_json_schema(),
            extraction_type="schema",
            instruction=(
                f"You are provided with an NPC's web page. You must extract a single NPC data object "
                f"to get a comprehensive profile of the main NPC: {npc_name}"
            ),
            apply_chunking=False,
            input_format="markdown",
            extra_args={"temperature": 0.1},
        )

        crawl_config = CrawlerRunConfig(extraction_strategy=llm_strategy, cache_mode=CacheMode.BYPASS)
        browser_cfg = BrowserConfig(headless=self.headless)

        try:
            self.logger.debug(
                "Starting web crawling",
                headless=self.headless,
                extraction_type="schema"
            )
            
            # Suppress all console output from crawl4ai
            with suppress_library_output():
                async with AsyncWebCrawler(config=browser_cfg) as crawler:
                    result = await crawler.arun(url=url, config=crawl_config)

                if not result:
                    self.logger.error("Crawling failed: No result returned", url=url)
                    raise ExtractionError("Crawling failed: No result returned")

                elif not result.success:
                    self.logger.error(
                        "Crawling failed with error",
                        url=url,
                        error_message=result.error_message
                    )
                    raise ExtractionError(f"Crawling failed: {result.error_message}")

                self.logger.debug(
                    "Crawling successful, parsing extracted content",
                    content_length=len(result.extracted_content) if result.extracted_content else 0
                )

                try:
                    data = json.loads(result.extracted_content)
                except json.JSONDecodeError as e:
                    self.logger.error(
                        "Failed to parse JSON from extracted content",
                        content_preview=result.extracted_content[:200] if result.extracted_content else None,
                        json_error=str(e)
                    )
                    raise ExtractionError(f"Failed to parse extracted content as JSON: {e}") from e

                self.logger.info(
                    "Successfully parsed extraction data",
                    data_items=len(data) if isinstance(data, list) else 1
                )

                npc_objects = []
                for i, item in enumerate(data if isinstance(data, list) else [data]):
                    try:
                        npc_data = RawNPCData(**item)
                        npc_objects.append(npc_data)
                        self.logger.debug(
                            "Validated NPC data object",
                            item_index=i,
                            npc_name=npc_data.name,
                            npc_race=npc_data.race
                        )
                    except Exception as e:
                        self.logger.error(
                            "Failed to validate NPC data",
                            item_index=i,
                            validation_error=str(e),
                            item_data=item
                        )
                        raise ExtractionError(f"Failed to validate NPC data: {e}") from e

                self.logger.info(
                    "Extraction completed successfully",
                    npc_count=len(npc_objects),
                    npc_names=[npc.name for npc in npc_objects]
                )
                return npc_objects

        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            self.logger.error(
                "Unexpected error during extraction",
                error=str(e),
                error_type=type(e).__name__,
                url=url
            )
            raise ExtractionError(f"Unexpected error during extraction: {e}") from e

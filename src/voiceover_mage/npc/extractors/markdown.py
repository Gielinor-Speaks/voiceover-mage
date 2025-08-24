# ABOUTME: Markdown-only NPC extractor using Crawl4AI with optional DSPy image analysis
# ABOUTME: Phase 1 implementation - extracts raw markdown and image URLs for caching

import re

import httpx
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from tenacity import retry, stop_after_attempt

from voiceover_mage.lib.logging import get_logger, log_extraction_step, suppress_library_output
from voiceover_mage.npc.extractors.base import ExtractionError, RawNPCExtractor
# Removed complex image models - keeping it simple for Phase 1
from voiceover_mage.npc.persistence import NPCRawExtraction


class MarkdownNPCExtractor(RawNPCExtractor):
    """NPC extractor that returns raw markdown content and image URLs.

    Can use either simple regex extraction or DSPy intelligent extraction for images.
    This is Phase 1 of the extraction pipeline.
    """

    def __init__(self, headless: bool = True, client: httpx.AsyncClient | None = None, use_dspy_images: bool = False):
        """Initialize the markdown extractor.

        Args:
            headless: Whether to run browser in headless mode
            client: HTTP client for wiki API calls (optional)
            use_dspy_images: Use DSPy intelligent image extraction instead of regex
        """
        self.headless = headless
        self.base_url = "https://oldschool.runescape.wiki"
        self.http_client = client or httpx.AsyncClient(
            headers={"User-Agent": "Gielinor-Speaks/1.0 (https://github.com/gielinor-speaks/)"}
        )
        self.use_dspy_images = use_dspy_images
        self.logger = get_logger(__name__)
        
        # Initialize DSPy image extractor if requested
        self.dspy_image_extractor = None
        if use_dspy_images:
            try:
                from voiceover_mage.npc.extractors.dspy_modules import ImageDetailExtractor
                self.dspy_image_extractor = ImageDetailExtractor()
                self.logger.info("Initialized DSPy ImageDetailExtractor")
            except ImportError as e:
                self.logger.warning("Failed to import DSPy modules, falling back to regex", error=str(e))
                self.use_dspy_images = False
        
        self.logger.info("Initialized MarkdownNPCExtractor", headless=headless, use_dspy_images=self.use_dspy_images)

    async def extract(self, npc_id: int) -> NPCRawExtraction:
        """Extract raw markdown and image URLs for the given NPC ID."""
        try:
            url = await self._get_npc_page_url(npc_id)
            npc_name = self._extract_npc_name_from_url(url) or f"NPC_{npc_id}"
            npc_variant = self._extract_npc_variant_from_url(url)

            markdown_content = await self._extract_markdown_content(url)
            chathead_url, image_url = await self._extract_image_urls(markdown_content, npc_name, npc_variant)

            extraction = NPCRawExtraction(
                npc_id=npc_id,
                npc_name=npc_name,
                wiki_url=url,
                raw_markdown=markdown_content,
                chathead_image_url=chathead_url,
                image_url=image_url,
                extraction_success=True,
                error_message=None,
            )

            self.logger.info(
                "Successfully extracted NPC data",
                npc_id=npc_id,
                npc_name=npc_name,
                markdown_length=len(markdown_content),
                has_chathead=bool(chathead_url),
                has_main_image=bool(image_url),
            )

            return extraction

        except Exception as e:
            self.logger.error("Failed to extract NPC data", npc_id=npc_id, error=str(e), error_type=type(e).__name__)

            # Return failed extraction record
            return NPCRawExtraction(
                npc_id=npc_id,
                npc_name=f"NPC_{npc_id}",
                wiki_url="",
                raw_markdown="",
                chathead_image_url=None,
                image_url=None,
                extraction_success=False,
                error_message=str(e),
            )

    @retry(stop=stop_after_attempt(3))
    @log_extraction_step("extract_markdown_content")
    async def _extract_markdown_content(self, url: str) -> str:
        """Extract raw markdown content from the wiki page."""
        crawl_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            exclude_all_images=False,  # Keep images in markdown for URL extraction
            process_iframes=True,  # Include iframe content
            wait_for_images=True,  # Wait for images to load
        )
        browser_cfg = BrowserConfig(headless=self.headless)

        try:
            with suppress_library_output():
                async with AsyncWebCrawler(config=browser_cfg) as crawler:
                    result = await crawler.arun(url=url, config=crawl_config)

            if not result or not result.success:
                error_msg = getattr(result, "error_message", "Unknown error") if result else "No result"
                raise ExtractionError(f"Failed to crawl page: {error_msg}")

            if not result.markdown:
                raise ExtractionError("No markdown content extracted")

            self.logger.debug("Successfully extracted markdown", url=url, markdown_length=len(result.markdown))

            return result.markdown

        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            self.logger.error("Unexpected error during markdown extraction", error=str(e), url=url)
            raise ExtractionError(f"Failed to extract markdown: {e}") from e

    async def _extract_image_urls(self, markdown: str, npc_name: str, npc_variant: str | None = None) -> tuple[str | None, str | None]:
        """Extract image URLs using either DSPy intelligent extraction or simple regex.
        
        Args:
            markdown: Raw markdown content
            npc_name: Name of the NPC for context
            npc_variant: Optional variant (e.g., 'Pete', 'Ardougne')
            
        Returns:
            Tuple of (chathead_url, image_url)
        """
        if self.use_dspy_images and self.dspy_image_extractor:
            return await self._extract_dspy_image_urls(markdown, npc_name, npc_variant)
        else:
            return await self._extract_simple_image_urls(markdown)
    
    async def _extract_dspy_image_urls(self, markdown: str, npc_name: str, npc_variant: str | None = None) -> tuple[str | None, str | None]:
        """Use DSPy module for intelligent image extraction."""
        try:
            visual_characteristics = self.dspy_image_extractor(markdown_content=markdown, npc_name=npc_name, npc_variant=npc_variant)
            
            self.logger.info(
                "DSPy image extraction completed",
                npc_name=npc_name,
                has_chathead=bool(visual_characteristics.chathead_image_url),
                has_main=bool(visual_characteristics.image_url),
                confidence=visual_characteristics.confidence_score,
                visual_archetype=visual_characteristics.visual_archetype,
                age_category=visual_characteristics.age_category,
                reasoning=visual_characteristics.reasoning[:100] + "..." if len(visual_characteristics.reasoning) > 100 else visual_characteristics.reasoning
            )
            
            return visual_characteristics.chathead_image_url, visual_characteristics.image_url
            
        except Exception as e:
            self.logger.error("DSPy image extraction failed, falling back to regex", error=str(e))
            return await self._extract_simple_image_urls(markdown)
    
    async def _extract_simple_image_urls(self, markdown: str) -> tuple[str | None, str | None]:
        """Fallback regex-based image extraction."""
        try:
            chathead_url = None
            image_url = None
            
            # Look for any chathead image
            chathead_pattern = r'(https://[^)\s]*chathead[^)\s]*\.(?:png|jpg|jpeg|webp)[^)\s]*)'
            chathead_match = re.search(chathead_pattern, markdown, re.IGNORECASE)
            if chathead_match:
                chathead_url = chathead_match.group(1)
            
            # Look for first thumbnail image that's not an icon or chathead
            thumb_matches = re.finditer(r'!\[\]\((https://[^)]*thumb/[^/]+\.png[^)]*)\)', markdown)
            for match in thumb_matches:
                candidate = match.group(1)
                if not any(skip in candidate.lower() for skip in ['chathead', 'icon', 'badge']):
                    image_url = candidate
                    break
            
            self.logger.debug(
                "Regex image extraction",
                has_chathead=bool(chathead_url),
                has_main=bool(image_url)
            )
            
            return chathead_url, image_url
            
        except Exception as e:
            self.logger.warning("Failed to extract image URLs", error=str(e))
            return None, None

    async def _get_npc_page_url(self, npc_id: int) -> str:
        """Get the wiki page for an NPC by ID."""
        lookup_url = self.base_url + f"/w/Special:Lookup?type=npc&id={npc_id}"

        self.logger.debug("Looking up NPC page URL", npc_id=npc_id, lookup_url=lookup_url)

        response = await self.http_client.get(
            lookup_url,
            follow_redirects=True,
        )
        response.raise_for_status()

        final_url = str(response.url)
        npc_name = self._extract_npc_name_from_url(final_url)

        self.logger.info(
            "Retrieved NPC page URL",
            npc_id=npc_id,
            npc_name=npc_name,
            final_url=final_url,
            redirects=response.history is not None,
        )

        return final_url

    @staticmethod
    def _extract_npc_name_from_url(url: str) -> str | None:
        """Extract the NPC name from the URL."""
        return MarkdownNPCExtractor._extract_npc_name_from_title(
            MarkdownNPCExtractor._extract_npc_page_title_from_url(url)
        )

    @staticmethod
    def _extract_npc_variant_from_url(url: str) -> str | None:
        """Extract the NPC variant from the URL."""
        return MarkdownNPCExtractor._extract_npc_variant_from_title(
            MarkdownNPCExtractor._extract_npc_page_title_from_url(url)
        )

    @staticmethod
    def _extract_npc_page_title_from_url(url: str | None) -> str | None:
        """Extract the page title from the URL."""
        if not url:
            return None
        # Regex to extract the page title from the url
        page_title = re.search(r"/w/(.*)", str(url))
        return page_title.group(1) if page_title else None

    @staticmethod
    def _extract_npc_name_from_title(title: str | None) -> str | None:
        """Extract the name of the NPC from the title."""
        # Regex to extract the name from the title
        # Example: "Bob#Variant" -> "Bob"
        if not title:
            return None
        name = re.search(r"(.*)#", title)
        return name.group(1) if name else title

    @staticmethod
    def _extract_npc_variant_from_title(title: str | None) -> str | None:
        """Extract the variant of the NPC from the title."""
        # Regex to extract the variant from the title
        # Example: "Bob#Variant" -> "Variant"
        if not title:
            return None
        variant = re.search(r"#(.*)", title)
        return variant.group(1) if variant else None


import re
from abc import ABC, abstractmethod

import httpx

from voiceover_mage.npc.models import RawNPCData


class BaseWikiNPCExtractor(ABC):
    """Base class for extracting NPCData from a wiki. This includes an httpx client for resolving
    npc id -> page url."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        # All extractors will likely use these items.
        self.base_url = "https://oldschool.runescape.wiki"
        self.api_url = f"{self.base_url}/api.php"
        self.http_client = client or httpx.AsyncClient(  # Allow for dependency injection
            headers={"User-Agent": "Gielinor-Speaks/1.0 (https://github.com/gielinor-speaks/)"}
        )

    @abstractmethod
    async def extract_npc_data(self, npc_id: int) -> RawNPCData:
        """Extract NPC data from the given NPC ID."""
        pass

    async def _get_npc_page_url(self, npc_id: int) -> str:
        """Get the wiki page for an NPC by ID."""
        response = await self.http_client.get(
            self.base_url + f"/w/Special:Lookup?type=npc&id={npc_id}",
            follow_redirects=True,
        )
        response.raise_for_status()
        return str(response.url)

    @staticmethod
    def _extract_npc_name_from_url(url: str) -> str | None:
        """Extract the NPC name from the URL."""
        return BaseWikiNPCExtractor._extract_npc_name_from_title(
            BaseWikiNPCExtractor._extract_npc_page_title_from_url(url)
        )

    @staticmethod
    def _extract_npc_variant_from_url(url: str) -> str | None:
        """Extract the NPC variant from the URL."""
        return BaseWikiNPCExtractor._extract_npc_variant_from_title(
            BaseWikiNPCExtractor._extract_npc_page_title_from_url(url)
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

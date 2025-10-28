# ABOUTME: Wiki page fetching and HTML processing utilities

"""
Utilities for fetching and processing OSRS Wiki pages.
Extracts main content and applies styling for dark theme compatibility.
"""

from __future__ import annotations

import html
from html.parser import HTMLParser

import httpx
from loguru import logger

from voiceover_mage.demo.constants.html_content import (
    WIKI_PAGE_STYLES,
    get_wiki_error_html,
    get_wiki_no_url_html,
)


class ContentExtractor(HTMLParser):
    """HTML parser to extract main content div from wiki pages."""

    def __init__(self):
        super().__init__()
        self.in_content = False
        self.content_html = []
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "div" and attrs_dict.get("id") == "content":
            self.in_content = True
            self.depth = 1
        elif self.in_content:
            self.depth += 1
            attrs_str = " ".join([f'{k}="{html.escape(v, quote=True)}"' for k, v in attrs])
            self.content_html.append(f"<{tag} {attrs_str}>")

    def handle_endtag(self, tag):
        if self.in_content:
            self.depth -= 1
            if self.depth == 0:
                self.in_content = False
            else:
                self.content_html.append(f"</{tag}>")

    def handle_data(self, data):
        if self.in_content and self.depth > 1:
            self.content_html.append(data)


async def fetch_wiki_html(wiki_url: str) -> str:
    """
    Fetch the wiki page HTML and extract just the main content with proper styling.

    Removes navigation, sidebars, and applies dark theme fixes.

    Args:
        wiki_url: URL of the OSRS Wiki page

    Returns:
        Styled HTML content ready for display, or error message HTML
    """
    if not wiki_url:
        return get_wiki_no_url_html()

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(wiki_url)
            response.raise_for_status()

            html = response.text

            # Extract just the main content div
            # The OSRS wiki uses <div id="content"> for the main content
            parser = ContentExtractor()
            parser.feed(html)
            content = "".join(parser.content_html)

            # Wrap with styling (respects light/dark mode)
            styled_html = f"""
            {WIKI_PAGE_STYLES}
            <base href="{wiki_url}" target="_blank">
            <div class="wiki-container">
                <div class="wiki-header">
                    <a href="{wiki_url}" target="_blank" class="wiki-button">
                        🔗 Open on OSRS Wiki
                    </a>
                </div>
                <div class="wiki-content">
                    {content if content else "<p>Could not extract main content</p>"}
                </div>
            </div>
            """

            return styled_html

    except Exception as e:
        logger.error(f"Failed to fetch wiki page {wiki_url}: {e}")
        return get_wiki_error_html(wiki_url, str(e))

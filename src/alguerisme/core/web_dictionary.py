"""Web dictionary abstraction for URL building and parsing."""

from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from alguerisme.configs.web_dictionary import WebDictionaryConfig


class WebDictionary:
    """Represents a web dictionary with URL templates and parsing rules."""

    def __init__(
        self,
        base_url: str = "https://www.algueres.net/",
        letters: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        index_url_template: str = "{base_url}/index.aspx?lletra={letter}&p={page}",
        entry_link_selector: str = "a[href*='/vocabols/']",
        entry_link_prefix: str = "/vocabols/",
        entry_link_suffix: str = ".aspx",
        content_selector: str = "#cntBody_pnlNews",
    ):
        """Initialize web dictionary."""
        self.base_url = base_url
        self.letters = letters
        self.index_url_template = index_url_template
        self.entry_link_selector = entry_link_selector
        self.entry_link_prefix = entry_link_prefix
        self.entry_link_suffix = entry_link_suffix
        self.content_selector = content_selector

    def build_index_url(self, letter: str, page: int) -> str:
        """Build URL for an index page."""
        return self.index_url_template.format(
            base_url=self.base_url,
            letter=letter.lower(),
            page=page,
        )

    def parse_page_urls(self, html: str) -> List[str]:
        """Parse vocabulary entry URLs from an index page's HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Limit search to content area (avoids navigation links, etc.)
        content_div = soup.select_one(self.content_selector)
        if not content_div:
            content_div = soup

        # Find all entry links
        all_links = content_div.select(self.entry_link_selector)

        # Convert to full URLs
        page_links = [
            urljoin(self.base_url, str(a["href"])) for a in all_links if a.get("href")
        ]

        # Build full URL prefix for filtering
        url_prefix = urljoin(self.base_url, self.entry_link_prefix)

        # Filter by prefix and suffix
        filtered = [
            link
            for link in page_links
            if link.startswith(url_prefix) and link.endswith(self.entry_link_suffix)
        ]

        return filtered

    def get_letters(self) -> List[str]:
        """Get list of letters to crawl."""
        return list(self.letters)

    @classmethod
    def from_config(cls, config: "WebDictionaryConfig") -> "WebDictionary":
        """Create WebDictionary from WebDictionaryConfig."""
        return cls(
            base_url=config.base_url,
            letters=config.letters,
            index_url_template=config.index_url_template,
            entry_link_selector=config.entry_link_selector,
            entry_link_prefix=config.entry_link_prefix,
            entry_link_suffix=config.entry_link_suffix,
            content_selector=config.content_selector,
        )

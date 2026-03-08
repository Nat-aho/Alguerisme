"""Core parser for extracting structured data from vocabol HTML."""

import logging
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from alguerisme.configs.parser import ParserConfig
from alguerisme.configs.web_dictionary import WebDictionaryConfig
from alguerisme.core.parser.models import ParsedVocabol

logger = logging.getLogger(__name__)


class VocabolParser:
    """Parser for extracting structured data from vocabol HTML entries."""

    def __init__(
        self,
        web_config: WebDictionaryConfig,
        parser_config: ParserConfig,
        base_url: str = "https://www.algueres.net/",
    ):
        """Initialize the parser with configuration.

        Parameters
        ----------
        web_config : WebDictionaryConfig
            Web dictionary configuration containing CSS selectors
        parser_config : ParserConfig
            Parser runtime options (parsing_version, concurrency)
        base_url : str
            Base URL for resolving relative URLs in images/audio

        """
        self.web_config = web_config
        self.parser_config = parser_config
        self.base_url = base_url.rstrip("/")

        logger.info(
            f"VocabolParser initialized with parsing version {parser_config.parsing_version}"
        )

    def parse(self, raw_html: str) -> ParsedVocabol:
        """Parse raw HTML into structured vocabol data.

        Parameters
        ----------
        raw_html : str
            Raw HTML content from vocabols_raw_html table

        Returns
        -------
        ParsedVocabol
            Parsed structured data (Pydantic model)

        """
        soup = BeautifulSoup(raw_html, "lxml")

        return ParsedVocabol(
            algueres_word=self._extract_text(soup, self.web_config.algueres_word_selector),
            algueres_definition=self._extract_text(
                soup, self.web_config.algueres_definition_selector
            ),
            catalan_word=self._extract_text(soup, self.web_config.catalan_word_selector),
            catalan_definition=self._extract_text(
                soup, self.web_config.catalan_definition_selector
            ),
            italian_word=self._extract_text(soup, self.web_config.italian_word_selector),
            italian_definition=self._extract_text(
                soup, self.web_config.italian_definition_selector
            ),
            image_urls=self._extract_image_urls(soup),
            audio_urls=self._extract_audio_urls(soup),
        )

    def _extract_text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """Extract and clean text from an element.

        Parameters
        ----------
        soup : BeautifulSoup
            BeautifulSoup object to search in
        selector : str
            CSS selector for the element

        Returns
        -------
        Optional[str]
            Cleaned text with whitespace normalized, or None if not found

        """
        element = soup.select_one(selector)
        if not element:
            return None

        # Join all text with single spaces, stripping each fragment
        return " ".join(element.stripped_strings)

    def _extract_image_urls(self, soup: BeautifulSoup) -> list[str]:
        """Extract image URLs from the HTML.

        Parameters
        ----------
        soup : BeautifulSoup
            BeautifulSoup object to search in

        Returns
        -------
        list[str]
            List of absolute image URLs (empty list if none found)

        """
        image_elements = soup.select(self.web_config.image_selector)
        urls = []

        for img in image_elements:
            src = img.get("src")
            if src and isinstance(src, str):
                # Convert to absolute URL
                absolute_url = urljoin(self.base_url, src)
                urls.append(absolute_url)

        return urls

    def _extract_audio_urls(self, soup: BeautifulSoup) -> list[str]:
        """Extract audio URLs from the HTML.

        Checks both <embed> tags and <audio> tags.

        Parameters
        ----------
        soup : BeautifulSoup
            BeautifulSoup object to search in

        Returns
        -------
        list[str]
            List of absolute audio URLs (empty list if none found)

        """
        urls = []

        # Extract from <embed> tags
        embed_elements = soup.select(self.web_config.audio_embed_selector)
        for embed in embed_elements:
            src = embed.get("src")
            if src and isinstance(src, str):
                absolute_url = urljoin(self.base_url, src)
                urls.append(absolute_url)

        # Extract from <audio> tags
        audio_elements = soup.select(self.web_config.audio_tag_selector)
        for audio in audio_elements:
            src = audio.get("src")
            if src and isinstance(src, str):
                absolute_url = urljoin(self.base_url, src)
                urls.append(absolute_url)

        return urls

    @classmethod
    def from_config(
        cls,
        web_config: WebDictionaryConfig,
        parser_config: ParserConfig,
        base_url: str = "https://www.algueres.net/",
    ) -> "VocabolParser":
        """Create VocabolParser from configuration.

        Parameters
        ----------
        web_config : WebDictionaryConfig
            Web dictionary configuration containing selectors
        parser_config : ParserConfig
            Parser runtime options
        base_url : str
            Base URL for resolving relative URLs

        Returns
        -------
        VocabolParser
            Initialized parser instance

        """
        return cls(web_config=web_config, parser_config=parser_config, base_url=base_url)

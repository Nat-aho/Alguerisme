"""Data models for crawler results."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class CrawlStatus(str, Enum):
    """Crawl status indicator."""

    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class URLWithLetter:
    """A URL with its associated letter."""

    url: str
    letter: str


@dataclass
class PageCrawlResult:
    """Result from fetching a single index page."""

    urls: Set[str]
    status_code: int
    page_number: int
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Whether the page was successfully fetched."""
        return 200 <= self.status_code < 300

    @classmethod
    def from_error(
        cls, page_number: int, error: str, status_code: int
    ) -> "PageCrawlResult":
        """Create an empty PageCrawlResult representing a failed fetch."""
        return cls(
            urls=set(),
            status_code=status_code,
            page_number=page_number,
            error=error,
        )


@dataclass
class LetterCrawlResult:
    """Result from crawling all pages for a single letter."""

    letter: str
    urls: Set[str]
    pages_crawled: int
    pages_successful: int
    stopped_reason: CrawlStatus

    @property
    def success(self) -> bool:
        """Whether the letter crawl was successful."""
        return self.stopped_reason == CrawlStatus.COMPLETED

    @property
    def url_count(self) -> int:
        """Number of URLs discovered."""
        return len(self.urls)

    def get_urls_with_letter(self) -> List[URLWithLetter]:
        """Get URLs paired with their letter."""
        return [URLWithLetter(url=url, letter=self.letter) for url in self.urls]

    @classmethod
    def from_error(cls, letter: str) -> "LetterCrawlResult":
        """Create a LetterCrawlResult representing a failed crawl."""
        return cls(
            letter=letter,
            urls=set(),
            pages_crawled=0,
            pages_successful=0,
            stopped_reason=CrawlStatus.ERROR,
        )


@dataclass
class CrawlResult:
    """Result from crawling multiple letters."""

    urls_by_letter: Dict[str, Set[str]]
    letters_crawled: List[str]
    letters_successful: int
    letters_failed: int
    total_pages: int
    letter_results: Dict[str, LetterCrawlResult] = field(default_factory=dict)

    @property
    def urls(self) -> Set[str]:
        """Set of all discovered URLs."""
        all_urls: Set[str] = set()
        for url_set in self.urls_by_letter.values():
            all_urls.update(url_set)
        return all_urls

    @property
    def success_rate(self) -> float:
        """Percentage of letters successfully crawled."""
        total = self.letters_successful + self.letters_failed
        return self.letters_successful / total if total > 0 else 0.0

    @property
    def url_count(self) -> int:
        """Total number of URLs discovered."""
        return len(self.urls)

    def summary(self) -> str:
        """Return a summary of the crawl."""
        return (
            f"Crawled {len(self.letters_crawled)} letters, "
            f"found {self.url_count} URLs across {self.total_pages} pages "
            f"(success rate: {self.success_rate:.1%})"
        )

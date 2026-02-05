"""Data models for crawler results."""

from dataclasses import dataclass
from typing import Optional, Set

from alguerisme.utils.alphabet import Letter


@dataclass
class PageCrawlResult:
    """Result from fetching a single index page."""

    letter: Letter
    page_number: int
    urls: Set[str]
    status_code: int
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Whether the page was successfully fetched."""
        return 200 <= self.status_code < 300

    @classmethod
    def from_error(
        cls, letter: Letter, page_number: int, error: str, status_code: int
    ) -> "PageCrawlResult":
        """Create an empty PageCrawlResult representing a failed fetch."""
        return cls(
            letter=letter,
            page_number=page_number,
            urls=set(),
            status_code=status_code,
            error=error,
        )


@dataclass
class CrawlServiceStats:
    """Statistics for a crawling session."""

    crawled_pages: int = 0
    urls_saved: int = 0
    urls_skipped: int = 0  # Already existed
    urls_failed: int = 0  # Failed to save

    @property
    def total_urls(self) -> int:
        """Total URLs processed."""
        return self.urls_saved + self.urls_skipped + self.urls_failed

    @property
    def success_rate(self) -> float:
        """Percentage of URLs successfully saved."""
        total = self.total_urls
        return (self.urls_saved + self.urls_skipped) / total if total > 0 else 0.0

    def summary(self) -> str:
        """Human-readable summary."""
        return (
            f"Crawled {self.total_urls} URLs, "
            f"saved {self.urls_saved} new, "
            f"{self.urls_skipped} already existed, "
            f"{self.urls_failed} failed"
        )

    @classmethod
    def empty(cls) -> "CrawlServiceStats":
        """Create an empty CrawlServiceStats instance."""
        return cls(urls_saved=0, urls_skipped=0, urls_failed=0)

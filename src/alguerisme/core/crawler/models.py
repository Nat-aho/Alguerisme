"""Data models for crawler results."""

from dataclasses import dataclass
from datetime import datetime
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

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "crawled_pages": self.crawled_pages,
            "urls_saved": self.urls_saved,
            "urls_skipped": self.urls_skipped,
            "urls_failed": self.urls_failed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CrawlServiceStats":
        """Create instance from dict."""
        return cls(
            crawled_pages=data.get("crawled_pages", 0),
            urls_saved=data.get("urls_saved", 0),
            urls_skipped=data.get("urls_skipped", 0),
            urls_failed=data.get("urls_failed", 0),
        )


@dataclass(frozen=True)
class CrawlMetrics:
    """Aggregated metrics from crawl results."""

    total_letters: int
    successful_count: int
    failed_count: int
    total_urls: int
    urls_saved: int
    urls_skipped: int
    urls_failed: int
    timestamp: str

    @classmethod
    def from_results(cls, results: list[CrawlServiceStats]) -> "CrawlMetrics":
        """Compute metrics from crawl results."""
        successful_stats = [r for r in results if isinstance(r, CrawlServiceStats)]

        total_letters = len(results)
        successful_count = len(successful_stats)
        failed_count = total_letters - successful_count

        total_urls = sum(s.total_urls for s in successful_stats)
        urls_saved = sum(s.urls_saved for s in successful_stats)
        urls_skipped = sum(s.urls_skipped for s in successful_stats)
        urls_failed = sum(s.urls_failed for s in successful_stats)

        return cls(
            total_letters=total_letters,
            successful_count=successful_count,
            failed_count=failed_count,
            total_urls=total_urls,
            urls_saved=urls_saved,
            urls_skipped=urls_skipped,
            urls_failed=urls_failed,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

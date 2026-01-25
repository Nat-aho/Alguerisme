"""Service layer models."""

from dataclasses import dataclass

from alguerisme.core.crawler import CrawlResult


@dataclass
class CrawlServiceResult:
    """Result from crawler service including persistence info.

    Combines the crawler result with information about
    what was saved to the database.
    """

    crawl_result: CrawlResult
    urls_saved: int
    urls_skipped: int  # Already existed
    urls_failed: int  # Failed to save

    @property
    def total_urls(self) -> int:
        """Total URLs processed (saved + skipped)."""
        return self.urls_saved + self.urls_skipped

    @property
    def success_rate(self) -> float:
        """Percentage of URLs successfully saved."""
        total = self.urls_saved + self.urls_skipped + self.urls_failed
        return (self.urls_saved + self.urls_skipped) / total if total > 0 else 0.0

    def summary(self) -> str:
        """Human-readable summary."""
        return (
            f"Crawled {self.crawl_result.url_count} URLs, "
            f"saved {self.urls_saved} new, "
            f"{self.urls_skipped} already existed, "
            f"{self.urls_failed} failed"
        )

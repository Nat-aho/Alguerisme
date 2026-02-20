"""Data models for collector results."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID


@dataclass
class CollectionResult:
    """Result from collecting HTML content from a single URL."""

    url: str
    entry_url_id: Optional[UUID]
    raw_html: Optional[str]
    http_status_code: int
    collected_at: datetime
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Whether the collection was successful."""
        return self.http_status_code == 200 and self.raw_html is not None

    @classmethod
    def from_error(
        cls,
        url: str,
        entry_url_id: Optional[UUID],
        error: str,
        status_code: int,
    ) -> "CollectionResult":
        """Create a CollectionResult representing a failed collection."""
        return cls(
            url=url,
            entry_url_id=entry_url_id,
            raw_html=None,
            http_status_code=status_code,
            collected_at=datetime.now(timezone.utc),
            error=error,
        )

    @classmethod
    def from_success(
        cls,
        url: str,
        entry_url_id: Optional[UUID],
        raw_html: str,
        status_code: int = 200,
    ) -> "CollectionResult":
        """Create a CollectionResult representing a successful collection."""
        return cls(
            url=url,
            entry_url_id=entry_url_id,
            raw_html=raw_html,
            http_status_code=status_code,
            collected_at=datetime.now(timezone.utc),
            error=None,
        )


@dataclass
class CollectionStats:
    """Statistics for a collection session."""

    urls_collected: int = 0  # New URLs (first time collection)
    urls_unchanged: int = 0  # No change detected (hash matched)
    urls_changed: int = 0  # Change detected → pending approval
    urls_failed: int = 0  # HTTP errors or collection failures

    @property
    def total_urls(self) -> int:
        """Total URLs processed."""
        return (
            self.urls_collected
            + self.urls_unchanged
            + self.urls_changed
            + self.urls_failed
        )

    @property
    def success_rate(self) -> float:
        """Percentage of URLs successfully processed."""
        total = self.total_urls
        if total == 0:
            return 0.0
        successful = self.urls_collected + self.urls_unchanged + self.urls_changed
        return successful / total

    def summary(self) -> str:
        """Human-readable summary."""
        return (
            f"Processed {self.total_urls} URLs: "
            f"{self.urls_collected} new, "
            f"{self.urls_unchanged} unchanged, "
            f"{self.urls_changed} changed (pending review), "
            f"{self.urls_failed} failed"
        )

    @classmethod
    def empty(cls) -> "CollectionStats":
        """Create an empty CollectionStats instance."""
        return cls(
            urls_collected=0,
            urls_unchanged=0,
            urls_changed=0,
            urls_failed=0
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "urls_collected": self.urls_collected,
            "urls_unchanged": self.urls_unchanged,
            "urls_changed": self.urls_changed,
            "urls_failed": self.urls_failed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CollectionStats":
        """Create instance from dict."""
        return cls(
            urls_collected=data.get("urls_collected", 0),
            urls_unchanged=data.get("urls_unchanged", 0),
            urls_changed=data.get("urls_changed", 0),
            urls_failed=data.get("urls_failed", 0),
        )


@dataclass
class LetterCollectionResult:
    """Result from collecting HTML for a single letter (task-level)."""

    letter: str
    status: str  # "success" | "failed"
    error: Optional[str] = None

    # Stats (meaningful when status="success", empty when "failed")
    urls_collected: int = 0
    urls_unchanged: int = 0
    urls_changed: int = 0
    urls_failed: int = 0

    @property
    def is_failed(self) -> bool:
        """Whether the letter collection failed."""
        return self.status == "failed"

    @property
    def total_urls(self) -> int:
        """Total URLs processed."""
        return (
            self.urls_collected
            + self.urls_unchanged
            + self.urls_changed
            + self.urls_failed
        )

    @classmethod
    def success(cls, letter: str, stats: CollectionStats) -> "LetterCollectionResult":
        """Create a successful result from CollectionStats."""
        return cls(
            letter=letter,
            status="success",
            urls_collected=stats.urls_collected,
            urls_unchanged=stats.urls_unchanged,
            urls_changed=stats.urls_changed,
            urls_failed=stats.urls_failed,
        )

    @classmethod
    def failed(cls, letter: str, error: str) -> "LetterCollectionResult":
        """Create a failed result."""
        return cls(
            letter=letter,
            status="failed",
            error=error,
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "letter": self.letter,
            "status": self.status,
            "error": self.error,
            "urls_collected": self.urls_collected,
            "urls_unchanged": self.urls_unchanged,
            "urls_changed": self.urls_changed,
            "urls_failed": self.urls_failed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LetterCollectionResult":
        """Create instance from dict."""
        return cls(
            letter=data["letter"],
            status=data["status"],
            error=data.get("error"),
            urls_collected=data.get("urls_collected", 0),
            urls_unchanged=data.get("urls_unchanged", 0),
            urls_changed=data.get("urls_changed", 0),
            urls_failed=data.get("urls_failed", 0),
        )


@dataclass(frozen=True)
class LetterCollectionResults:
    """Wrapper for collection results with convenient filtering properties."""

    results: list[LetterCollectionResult]

    @classmethod
    def from_results(
        cls, results: list[LetterCollectionResult]
    ) -> "LetterCollectionResults":
        """Create a LetterCollectionResults from a list of LetterCollectionResult."""
        return cls(results=results)

    @property
    def successful_results(self) -> list[LetterCollectionResult]:
        """List of successfully collected letter results."""
        return sorted(
            [r for r in self.results if not r.is_failed], key=lambda r: r.letter
        )

    @property
    def failed_results(self) -> list[LetterCollectionResult]:
        """List of failed letter results."""
        return sorted([r for r in self.results if r.is_failed], key=lambda r: r.letter)

    @property
    def success_letters(self) -> list[str]:
        """List of successfully collected letters."""
        return sorted([r.letter for r in self.results if not r.is_failed])

    @property
    def failed_letters(self) -> list[str]:
        """List of failed letters."""
        return sorted([r.letter for r in self.results if r.is_failed])

    @property
    def total_letters(self) -> int:
        """Total number of letters in results."""
        return len(self.results)


@dataclass(frozen=True)
class CollectionMetrics:
    """Aggregated metrics from collection results."""

    total_letters: int
    successful_count: int
    failed_count: int
    total_urls: int
    urls_collected: int
    urls_unchanged: int
    urls_changed: int
    urls_failed: int
    timestamp: str
    collection_type: str  # "new" | "update_check"

    @classmethod
    def from_results(
        cls, results: LetterCollectionResults, collection_type: str
    ) -> "CollectionMetrics":
        """Compute metrics from letter collection results."""
        successful_stats = results.successful_results
        failed_stats = results.failed_results

        total_letters = results.total_letters
        successful_count = len(successful_stats)
        failed_count = len(failed_stats)

        total_urls = sum(s.total_urls for s in successful_stats)
        urls_collected = sum(s.urls_collected for s in successful_stats)
        urls_unchanged = sum(s.urls_unchanged for s in successful_stats)
        urls_changed = sum(s.urls_changed for s in successful_stats)
        urls_failed = sum(s.urls_failed for s in successful_stats)

        return cls(
            total_letters=total_letters,
            successful_count=successful_count,
            failed_count=failed_count,
            total_urls=total_urls,
            urls_collected=urls_collected,
            urls_unchanged=urls_unchanged,
            urls_changed=urls_changed,
            urls_failed=urls_failed,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            collection_type=collection_type,
        )


@dataclass
class CollectionTaskResult:
    """Result from a collection task (Celery task wrapper).

    DEPRECATED: Use LetterCollectionResult instead for new code.
    """

    status: str  # "success" or "error"
    stats: CollectionStats
    total_urls: int
    message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for Celery."""
        return {
            "status": self.status,
            **self.stats.to_dict(),
            "total": self.total_urls,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CollectionTaskResult":
        """Create instance from dict."""
        stats = CollectionStats(
            urls_collected=data.get("urls_collected", 0),
            urls_unchanged=data.get("urls_unchanged", 0),
            urls_changed=data.get("urls_changed", 0),
            urls_failed=data.get("urls_failed", 0),
        )
        return cls(
            status=data.get("status", "error"),
            stats=stats,
            total_urls=data.get("total", 0),
            message=data.get("message"),
        )

    @classmethod
    def success(
        cls, stats: CollectionStats, total_urls: int, message: Optional[str] = None
    ) -> "CollectionTaskResult":
        """Create a successful task result."""
        return cls(
            status="success",
            stats=stats,
            total_urls=total_urls,
            message=message,
        )

    @classmethod
    def error(cls, message: str) -> "CollectionTaskResult":
        """Create an error task result."""
        return cls(
            status="error",
            stats=CollectionStats.empty(),
            total_urls=0,
            message=message,
        )


@dataclass
class ApplyChangesResult:
    """Result from applying approved HTML changes."""

    status: str  # "success" or "error"
    applied: int
    skipped: int
    errors: int
    message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for Celery."""
        return {
            "status": self.status,
            "applied": self.applied,
            "skipped": self.skipped,
            "errors": self.errors,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ApplyChangesResult":
        """Create instance from dict."""
        return cls(
            status=data.get("status", "error"),
            applied=data.get("applied", 0),
            skipped=data.get("skipped", 0),
            errors=data.get("errors", 0),
            message=data.get("message"),
        )

    @classmethod
    def success(
        cls, applied: int, skipped: int, errors: int, message: Optional[str] = None
    ) -> "ApplyChangesResult":
        """Create a successful result."""
        return cls(
            status="success",
            applied=applied,
            skipped=skipped,
            errors=errors,
            message=message,
        )

    @classmethod
    def error(cls, message: str) -> "ApplyChangesResult":
        """Create an error result."""
        return cls(
            status="error",
            applied=0,
            skipped=0,
            errors=0,
            message=message,
        )

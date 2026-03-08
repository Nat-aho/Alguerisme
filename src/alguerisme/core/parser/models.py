"""Data models for parsed vocabol entries."""

from typing import Optional

from pydantic import BaseModel, Field


class ParsedVocabol(BaseModel):
    """Pydantic model for parsed vocabol data (not a database model)."""

    algueres_word: Optional[str] = None
    algueres_definition: Optional[str] = None
    catalan_word: Optional[str] = None
    catalan_definition: Optional[str] = None
    italian_word: Optional[str] = None
    italian_definition: Optional[str] = None
    image_urls: list[str] = Field(default_factory=list)
    audio_urls: list[str] = Field(default_factory=list)

    def is_empty(self) -> bool:
        """Check if the parsed vocabol has any non-empty fields."""
        return not any(
            [
                self.algueres_word,
                self.algueres_definition,
                self.catalan_word,
                self.catalan_definition,
                self.italian_word,
                self.italian_definition,
                self.image_urls,
                self.audio_urls,
            ]
        )


class ParseStats(BaseModel):
    """Statistics for a parsing operation."""

    total_entries: int = 0
    parsed_successfully: int = 0
    entries_created: int = 0  # New parsed entries
    entries_updated: int = 0  # Re-parsed due to HTML updates
    parsing_failed: int = 0
    skipped_no_html: int = 0
    skipped_empty_result: int = 0

    @classmethod
    def empty(cls) -> "ParseStats":
        """Create an empty stats object."""
        return cls()

    def summary(self) -> str:
        """Generate a summary string of the parsing statistics."""
        details = [f"{self.parsed_successfully} parsed"]
        if self.entries_created > 0:
            details.append(f"{self.entries_created} new")
        if self.entries_updated > 0:
            details.append(f"{self.entries_updated} updated")
        if self.parsing_failed > 0:
            details.append(f"{self.parsing_failed} failed")
        if self.skipped_no_html > 0:
            details.append(f"{self.skipped_no_html} skipped (no HTML)")
        if self.skipped_empty_result > 0:
            details.append(f"{self.skipped_empty_result} skipped (empty)")

        return f"Parsing complete: {', '.join(details)}"


class LetterParseResult(BaseModel):
    """Result from parsing vocabols for a single letter."""

    letter: str
    success: bool
    stats: Optional[ParseStats] = None
    error: Optional[str] = None

    @classmethod
    def successful(cls, letter: str, stats: ParseStats) -> "LetterParseResult":
        """Create a successful result."""
        return cls(letter=letter, success=True, stats=stats)

    @classmethod
    def failed(cls, letter: str, error: str) -> "LetterParseResult":
        """Create a failed result."""
        return cls(letter=letter, success=False, error=error)

    def to_dict(self) -> dict:
        """Convert to dictionary for Celery serialization."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "LetterParseResult":
        """Create from dictionary after Celery deserialization."""
        return cls(**data)


class LetterParseResults(BaseModel):
    """Aggregated results from parsing multiple letters."""

    results: list[LetterParseResult]

    @classmethod
    def from_results(cls, results: list[LetterParseResult]) -> "LetterParseResults":
        """Create from list of letter results."""
        return cls(results=results)

    @property
    def successful_results(self) -> list[LetterParseResult]:
        """Get all successful parse results."""
        return [r for r in self.results if r.success]

    @property
    def failed_results(self) -> list[LetterParseResult]:
        """Get all failed parse results."""
        return [r for r in self.results if not r.success]

    @property
    def success_letters(self) -> list[str]:
        """Get list of successfully parsed letters."""
        return [r.letter for r in self.successful_results]

    @property
    def failed_letters(self) -> list[str]:
        """Get list of failed letters."""
        return [r.letter for r in self.failed_results]

    @property
    def total_parsed(self) -> int:
        """Total entries successfully parsed across all letters."""
        return sum(
            r.stats.parsed_successfully for r in self.successful_results if r.stats
        )

    @property
    def total_failed(self) -> int:
        """Total entries that failed parsing across all letters."""
        return sum(r.stats.parsing_failed for r in self.successful_results if r.stats)

    @property
    def total_skipped_no_html(self) -> int:
        """Total entries skipped due to no HTML across all letters."""
        return sum(r.stats.skipped_no_html for r in self.successful_results if r.stats)

    @property
    def total_skipped_empty(self) -> int:
        """Total entries skipped due to empty results across all letters."""
        return sum(
            r.stats.skipped_empty_result for r in self.successful_results if r.stats
        )

"""Data models for image collection operations."""

from typing import Optional

from pydantic import BaseModel


class ImageCollectionStats(BaseModel):
    """Statistics for an image collection operation."""

    total_vocabols_with_images: int = 0
    images_collected: int = 0
    images_failed: int = 0
    images_skipped_exists: int = 0

    @classmethod
    def empty(cls) -> "ImageCollectionStats":
        """Create an empty stats object."""
        return cls()

    def summary(self) -> str:
        """Generate a summary string of the collection statistics."""
        return (
            f"Image collection complete: "
            f"{self.images_collected} collected, "
            f"{self.images_failed} failed, "
            f"{self.images_skipped_exists} skipped (already exist)"
        )


class LetterImageCollectionResult(BaseModel):
    """Result from collecting images for a single letter."""

    letter: str
    success: bool
    stats: Optional[ImageCollectionStats] = None
    error: Optional[str] = None

    @classmethod
    def successful(
        cls, letter: str, stats: ImageCollectionStats
    ) -> "LetterImageCollectionResult":
        """Create a successful result."""
        return cls(letter=letter, success=True, stats=stats)

    @classmethod
    def failed(cls, letter: str, error: str) -> "LetterImageCollectionResult":
        """Create a failed result."""
        return cls(letter=letter, success=False, error=error)

    def to_dict(self) -> dict:
        """Convert to dictionary for Celery serialization."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "LetterImageCollectionResult":
        """Create from dictionary after Celery deserialization."""
        return cls(**data)


class LetterImageCollectionResults(BaseModel):
    """Aggregated results from collecting images for multiple letters."""

    results: list[LetterImageCollectionResult]

    @classmethod
    def from_results(
        cls, results: list[LetterImageCollectionResult]
    ) -> "LetterImageCollectionResults":
        """Create from list of letter results."""
        return cls(results=results)

    @property
    def successful_results(self) -> list[LetterImageCollectionResult]:
        """Get only successful results."""
        return [r for r in self.results if r.success]

    @property
    def failed_results(self) -> list[LetterImageCollectionResult]:
        """Get only failed results."""
        return [r for r in self.results if not r.success]

    @property
    def all_letters(self) -> list[str]:
        """Get all letters processed."""
        return [r.letter for r in self.results]

    @property
    def successful_letters(self) -> list[str]:
        """Get letters that succeeded."""
        return [r.letter for r in self.successful_results]

    @property
    def failed_letters(self) -> list[str]:
        """Get letters that failed."""
        return [r.letter for r in self.failed_results]

    @property
    def total_stats(self) -> ImageCollectionStats:
        """Aggregate statistics across all letters."""
        total = ImageCollectionStats.empty()
        for result in self.successful_results:
            if result.stats:
                total.total_vocabols_with_images += (
                    result.stats.total_vocabols_with_images
                )
                total.images_collected += result.stats.images_collected
                total.images_failed += result.stats.images_failed
                total.images_skipped_exists += result.stats.images_skipped_exists
        return total

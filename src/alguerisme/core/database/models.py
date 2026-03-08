"""Database models."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class EntryURLsBase(SQLModel):
    """Base model for EntryURLs with shared fields."""

    url: str = Field(unique=True, nullable=False, index=True)
    letter: str = Field(max_length=1, index=True, nullable=False)


class EntryURLsCreate(EntryURLsBase):
    """Model for creating a new URL entry.

    Used when inserting new URLs from crawler.
    Does not include id or discovered_at (auto-generated).
    """

    pass


class EntryURLsUpdate(SQLModel):
    """Model for updating an existing URL entry.

    All fields optional to allow partial updates.
    """

    url: Optional[str] = Field(default=None, unique=True, index=True)
    letter: Optional[str] = Field(default=None, max_length=1)


class EntryURLs(EntryURLsBase, table=True):
    """Database model for dictionary entry URLs fetched by the crawler."""

    __tablename__: str = "entry_urls"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# VocabolsRawHTML Models
# ============================================================================


class VocabolsRawHTMLBase(SQLModel):
    """Base model for VocabolsRawHTML with shared fields."""

    entry_url_id: uuid.UUID = Field(
        foreign_key="entry_urls.id", unique=True, index=True
    )  # One current version per URL
    url: str = Field(nullable=False, index=True)
    letter: str = Field(max_length=1, index=True, nullable=False)
    raw_html: Optional[str] = Field(default=None)
    content_hash: Optional[str] = Field(
        default=None, max_length=64, index=True
    )  # SHA256 hash
    http_status_code: Optional[int] = Field(default=None)
    error_message: Optional[str] = Field(default=None)


class VocabolsRawHTMLCreate(VocabolsRawHTMLBase):
    """Model for creating a new VocabolsRawHTML entry.

    Used when inserting new collected HTML.
    Does not include id, collected_at, or last_updated_at (auto-generated).
    """

    pass


class VocabolsRawHTMLUpdate(SQLModel):
    """Model for updating an existing VocabolsRawHTML entry.

    All fields optional to allow partial updates.
    """

    letter: Optional[str] = Field(default=None, max_length=1)
    raw_html: Optional[str] = Field(default=None)
    content_hash: Optional[str] = Field(default=None, max_length=64)
    http_status_code: Optional[int] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    last_updated_at: Optional[datetime] = Field(default=None)


class VocabolsRawHTML(VocabolsRawHTMLBase, table=True):
    """Database model for raw HTML content from vocabols dictionary entries.

    This is the production table - contains current/approved HTML that parser uses.
    """

    __tablename__: str = "vocabols_raw_html"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    collected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )  # Never changes
    last_updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )  # When content last changed


# ============================================================================
# VocabolsHtmlChanges Models (Change Detection & Approval Workflow)
# ============================================================================


class VocabolsHtmlChangesBase(SQLModel):
    """Base model for VocabolsHtmlChanges with shared fields."""

    entry_url_id: uuid.UUID = Field(foreign_key="entry_urls.id", index=True)
    url: str = Field(nullable=False, index=True)
    new_html: str = Field(nullable=False)  # New HTML to be applied
    new_hash: str = Field(nullable=False, max_length=64)  # SHA256 of new HTML
    old_html: Optional[str] = Field(default=None)  # Current HTML (for comparison)
    old_hash: Optional[str] = Field(default=None, max_length=64)  # SHA256 of old HTML
    change_type: str = Field(
        default="modified", max_length=20, index=True
    )  # ChangeType enum values: new, modified, size_change
    size_change_bytes: int = Field(default=0)
    size_change_pct: float = Field(default=0.0)
    status: str = Field(
        default="pending", max_length=20, index=True
    )  # ChangeStatus enum values: pending, approved, rejected
    reviewed_at: Optional[datetime] = Field(default=None)
    reviewed_by: Optional[str] = Field(default=None, max_length=50)


class VocabolsHtmlChangesCreate(VocabolsHtmlChangesBase):
    """Model for creating a new VocabolsHtmlChanges entry.

    Does not include id or detected_at (auto-generated).
    """

    pass


class VocabolsHtmlChangesUpdate(SQLModel):
    """Model for updating an existing VocabolsHtmlChanges entry."""

    status: Optional[str] = Field(default=None, max_length=20)
    reviewed_at: Optional[datetime] = Field(default=None)
    reviewed_by: Optional[str] = Field(default=None, max_length=50)
    new_html: Optional[str] = Field(default=None)
    new_hash: Optional[str] = Field(default=None, max_length=64)
    size_change_bytes: Optional[int] = Field(default=None)
    size_change_pct: Optional[float] = Field(default=None)


class VocabolsHtmlChanges(VocabolsHtmlChangesBase, table=True):
    """Database model for tracking HTML changes pending approval.

    This is the staging table - changes are reviewed here before applying to production.
    """

    __tablename__: str = "vocabols_html_changes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )


# ============================================================================
# ParsedVocabols Models
# ============================================================================


class ParsedVocabolsBase(SQLModel):
    """Base model for ParsedVocabols with shared fields."""

    entry_url_id: uuid.UUID = Field(
        foreign_key="entry_urls.id", unique=True, index=True
    )  # One parsed version per URL
    raw_html_id: uuid.UUID = Field(
        foreign_key="vocabols_raw_html.id", index=True
    )  # Link to source HTML for lineage

    url: str = Field(nullable=False, index=True)

    # Parsed text fields
    algueres_word: Optional[str] = Field(default=None, index=True)
    algueres_definition: Optional[str] = Field(default=None)
    catalan_word: Optional[str] = Field(default=None, index=True)
    catalan_definition: Optional[str] = Field(default=None)
    italian_word: Optional[str] = Field(default=None, index=True)
    italian_definition: Optional[str] = Field(default=None)

    # Media URLs - stored as JSONB
    # None = not yet parsed, [] = parsed but no media, ["url"] = has media
    image_urls: Optional[list[str]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    audio_urls: Optional[list[str]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # URL counts for easy filtering (derived from arrays above)
    image_url_count: int = Field(default=0, index=True)
    audio_url_count: int = Field(default=0, index=True)

    # Metadata
    parsing_errors: Optional[str] = Field(default=None)


class ParsedVocabolsCreate(ParsedVocabolsBase):
    """Model for creating a new ParsedVocabols entry.

    Used when inserting new parsed entries.
    Does not include id or parsed_at (auto-generated).
    """

    pass


class ParsedVocabolsUpdate(SQLModel):
    """Model for updating an existing ParsedVocabols entry.

    All fields optional to allow partial updates.
    """

    algueres_word: Optional[str] = Field(default=None)
    algueres_definition: Optional[str] = Field(default=None)
    catalan_word: Optional[str] = Field(default=None)
    catalan_definition: Optional[str] = Field(default=None)
    italian_word: Optional[str] = Field(default=None)
    italian_definition: Optional[str] = Field(default=None)
    image_urls: Optional[list[str]] = Field(default=None)
    audio_urls: Optional[list[str]] = Field(default=None)
    image_url_count: Optional[int] = Field(default=None)
    audio_url_count: Optional[int] = Field(default=None)
    parsing_errors: Optional[str] = Field(default=None)


class ParsedVocabols(ParsedVocabolsBase, table=True):
    """Database model for parsed vocabol entries.

    Contains structured data extracted from raw HTML.
    """

    __tablename__: str = "parsed_vocabols"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    parsed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )


# ============================================================================
# VocabolsImages Models (MinIO-backed image storage)
# ============================================================================


class VocabolsImagesBase(SQLModel):
    """Base model for VocabolsImages with shared fields."""

    parsed_vocabol_id: uuid.UUID = Field(
        foreign_key="parsed_vocabols.id", index=True
    )  # Multiple images per parsed vocabol allowed
    source_url: str = Field(nullable=False, index=True)
    s3_key: str = Field(nullable=False, index=True)  # MinIO object key path
    s3_bucket: str = Field(default="alguerisme-images")

    # Track which parsing version this image came from
    source_parsed_at: datetime = Field(
        nullable=False,
        index=True,
        description="parsed_vocabols.parsed_at at time of collection",
    )

    content_type: Optional[str] = Field(default=None, max_length=50)
    size_bytes: Optional[int] = Field(default=None)
    content_hash: Optional[str] = Field(
        default=None, max_length=64, index=True
    )  # SHA256 hash
    collection_status: str = Field(
        default="pending", max_length=20, index=True
    )  # pending, success, failed
    error_message: Optional[str] = Field(default=None)


class VocabolsImagesCreate(VocabolsImagesBase):
    """Model for creating a new VocabolsImages entry.

    Used when inserting new collected images.
    Does not include id or collected_at (auto-generated).
    """

    pass


class VocabolsImagesUpdate(SQLModel):
    """Model for updating an existing VocabolsImages entry.

    All fields optional to allow partial updates.
    """

    s3_key: Optional[str] = Field(default=None)
    s3_bucket: Optional[str] = Field(default=None)
    content_type: Optional[str] = Field(default=None)
    size_bytes: Optional[int] = Field(default=None)
    content_hash: Optional[str] = Field(default=None)
    collection_status: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)


class VocabolsImages(VocabolsImagesBase, table=True):
    """Database model for vocabol images stored in MinIO.

    Stores metadata and S3 keys for images, actual binary data is in MinIO.
    """

    __tablename__: str = "vocabols_images"
    __table_args__ = (
        UniqueConstraint(
            "parsed_vocabol_id",
            "source_url",
            name="uq_vocabol_image_url",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    collected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )


# ============================================================================
# Stats Models (Pydantic models for query results)
# ============================================================================


class ParsedVocabolsOverallStats(BaseModel):
    """Overall statistics for all parsed vocabols."""

    total: int
    with_images: int
    with_audio: int
    total_images: int
    total_audio: int
    with_errors: int


class ParsedVocabolsLetterStats(BaseModel):
    """Statistics for parsed vocabols for a specific letter."""

    letter: str
    total: int
    with_images: int
    with_audio: int
    avg_images: float
    avg_audio: float

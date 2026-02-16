"""Database models."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class EntryURLsBase(SQLModel):
    """Base model for EntryURLs with shared fields."""

    url: str = Field(unique=True, nullable=False, index=True)
    letter: Optional[str] = Field(default=None, max_length=1, index=True)


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

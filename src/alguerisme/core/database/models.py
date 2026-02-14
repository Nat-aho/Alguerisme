"""Database models."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class EntryURLsBase(SQLModel):
    """Base model for EntryURLs with shared fields."""

    url: str = Field(unique=True, nullable=False, index=True)
    letter: Optional[str] = Field(default=None, max_length=1)


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

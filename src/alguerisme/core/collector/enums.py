"""Enums for collector module."""

from enum import Enum


class ChangeStatus(str, Enum):
    """Status values for vocabols HTML changes."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CollectionStatus(str, Enum):
    """Status values for collection results."""

    COLLECTED = "collected"  # New URL, first time collection
    UNCHANGED = "unchanged"  # No change detected
    CHANGED = "changed"  # Change detected, pending review
    FAILED = "failed"  # Collection failed


class ChangeType(str, Enum):
    """Types of HTML changes detected."""

    NEW = "new"  # First time collection (shouldn't appear in changes table)
    MODIFIED = "modified"  # Content changed (< 20% size change)
    SIZE_CHANGE = "size_change"  # Significant size change (>= 20%)

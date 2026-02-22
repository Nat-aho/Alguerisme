"""Shared utilities for HTML collection services."""

import hashlib
import logging
from typing import NamedTuple

from alguerisme.core.collector.enums import ChangeType

logger = logging.getLogger(__name__)


class ChangeMetrics(NamedTuple):
    """Metrics for detected content changes."""

    size_old: int
    size_new: int
    size_change_bytes: int
    size_change_pct: float
    change_type: ChangeType


def calculate_content_hash(html: str) -> str:
    """Calculate SHA256 hash of HTML content.

    Parameters
    ----------
    html : str
        HTML content to hash

    Returns
    -------
    str
        Hexadecimal SHA256 hash

    """
    return hashlib.sha256(html.encode()).hexdigest()


def calculate_change_metrics(old_html: str, new_html: str) -> ChangeMetrics:
    """Calculate metrics for content change.

    Parameters
    ----------
    old_html : str
        Previous HTML content
    new_html : str
        New HTML content

    Returns
    -------
    ChangeMetrics
        Calculated change metrics including size differences and change type

    """
    size_old = len(old_html) if old_html else 0
    size_new = len(new_html)
    size_change_bytes = size_new - size_old
    size_change_pct = (size_change_bytes / size_old * 100) if size_old > 0 else 0

    # Determine change type based on size change
    if abs(size_change_pct) > 20:
        change_type = ChangeType.SIZE_CHANGE
    else:
        change_type = ChangeType.MODIFIED

    return ChangeMetrics(
        size_old=size_old,
        size_new=size_new,
        size_change_bytes=size_change_bytes,
        size_change_pct=size_change_pct,
        change_type=change_type,
    )

"""Collector module for fetching raw HTML from dictionary entries."""

from alguerisme.core.collector.enums import (
    ChangeStatus,
    ChangeType,
    CollectionStatus,
)
from alguerisme.core.collector.html_collector import HTMLCollector
from alguerisme.core.collector.html_collector_service import HTMLCollectorService
from alguerisme.core.collector.html_update_service import (
    HTMLUpdateCheckerService,
)
from alguerisme.core.collector.models import (
    ApplyChangesResult,
    CollectionMetrics,
    CollectionResult,
    CollectionStats,
    CollectionTaskResult,
    LetterCollectionResult,
)

__all__ = [
    "ApplyChangesResult",
    "ChangeStatus",
    "ChangeType",
    "CollectionMetrics",
    "CollectionResult",
    "CollectionStats",
    "CollectionStatus",
    "CollectionTaskResult",
    "HTMLCollector",
    "HTMLCollectorService",
    "HTMLUpdateCheckerService",
    "LetterCollectionResult",
]


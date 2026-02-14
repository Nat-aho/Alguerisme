"""Protocols for notification system."""

from typing import Protocol


class Reportable(Protocol):
    """Protocol for objects that can be sent as notifications."""

    def format_telegram(self) -> str:
        """Format report for Telegram."""
        ...

    def format_console(self) -> str:
        """Format report for console/logs."""
        ...

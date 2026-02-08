"""Generic notification manager for all report types."""

import asyncio
import logging
from enum import Enum

from alguerisme.configs.app_config import AppConfig
from alguerisme.notifications.protocols import Reportable
from alguerisme.notifications.telegram import TelegramNotifier

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Available notification channels."""

    CONSOLE = "console"
    TELEGRAM = "telegram"


class NotificationManager:
    """Generic notification manager - works with any Reportable object."""

    def __init__(self, config: AppConfig):
        """
        Initialize notification manager.

        Parameters
        ----------
        config : AppConfig
            Application configuration with notification settings
        """
        self.config = config

    def send(self, report: Reportable) -> dict:
        """Send report to all enabled notification channels."""
        # Run async send in sync context
        return asyncio.run(self._send_async(report))

    async def _send_async(self, report: Reportable) -> dict:
        """Async implementation of send."""
        results = {}

        self._log_to_console(report)
        results[NotificationChannel.CONSOLE] = True

        if self._telegram_enabled():
            results[NotificationChannel.TELEGRAM] = await self._send_telegram(report)
        else:
            results[NotificationChannel.TELEGRAM] = False

        return results

    def _log_to_console(self, report: Reportable) -> None:
        """Log report to console."""
        message = report.format_console()
        logger.info(message)

    def _telegram_enabled(self) -> bool:
        """Check if Telegram notifications are enabled."""
        return (
            self.config.notifications is not None
            and self.config.notifications.telegram_enabled
        )

    async def _send_telegram(self, report: Reportable) -> bool:
        """Send report via Telegram."""
        if not self.config.notifications:
            return False

        telegram_config = self.config.notifications.telegram
        if not telegram_config:
            return False

        try:
            message = report.format_telegram()

            notifier = TelegramNotifier(
                bot_token=telegram_config.bot_token,
                chat_id=telegram_config.chat_id,
                parse_mode=telegram_config.parse_mode,
            )

            success = await notifier.send(message)

            if success:
                logger.info("Telegram notification sent successfully")
            else:
                logger.warning("Failed to send Telegram notification")

            return success

        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}", exc_info=True)
            return False

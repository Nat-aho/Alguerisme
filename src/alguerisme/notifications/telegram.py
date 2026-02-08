"""Telegram notification service."""

import logging

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Simple Telegram bot notification service."""

    def __init__(self, bot_token: str, chat_id: str, parse_mode: str = "Markdown"):
        """Initialize Telegram notifier."""
        try:
            from telegram import Bot
            from telegram.error import TelegramError

            self._telegram_available = True
            self._TelegramError = TelegramError
        except ImportError:
            self._telegram_available = False
            logger.warning(
                "python-telegram-bot not installed. "
                "Install with: pip install python-telegram-bot"
            )
            return

        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id
        self.parse_mode = parse_mode

    async def send(self, message: str) -> bool:
        """Send a text message to Telegram."""
        if not self._telegram_available:
            logger.error("Cannot send Telegram message: library not available")
            return False

        try:
            await self.bot.send_message(
                chat_id=self.chat_id, text=message, parse_mode=self.parse_mode
            )
            logger.info(f"Telegram message sent to chat {self.chat_id}")
            return True

        except self._TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}")
            return False

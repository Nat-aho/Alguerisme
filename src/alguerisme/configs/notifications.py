"""Notification configuration models."""

from typing import Optional

from pydantic import BaseModel, Field

from alguerisme.utils.secrets import get_secret


class TelegramConfig(BaseModel):
    """Configuration for Telegram bot notifications."""

    chat_id: str = Field(
        default="", description="Telegram chat ID to send notifications to"
    )
    enabled: bool = Field(
        default=False, description="Whether Telegram notifications are enabled"
    )
    parse_mode: str = Field(
        default="Markdown", description="Parse mode for Telegram messages"
    )

    @property
    def bot_token(self) -> str:
        """Retrieve Telegram bot token from secrets."""
        return get_secret("telegram_bot_token")


class NotificationConfig(BaseModel):
    """Configuration for all notification services."""

    telegram: Optional[TelegramConfig] = Field(
        default=None, description="Telegram notification configuration"
    )

    @property
    def telegram_enabled(self) -> bool:
        """Check if Telegram notifications are enabled and configured."""
        if not self.telegram or not self.telegram.enabled:
            return False

        if not self.telegram.chat_id:
            return False

        try:
            token = self.telegram.bot_token
            return bool(token)
        except (KeyError, RuntimeError):
            return False

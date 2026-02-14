"""Notification configuration models."""

from typing import Optional

from pydantic import BaseModel, Field, PrivateAttr, SecretStr

from alguerisme.utils.secrets import get_secret


class TelegramConfig(BaseModel):
    """Configuration for Telegram bot notifications."""

    model_config = {"arbitrary_types_allowed": True}

    chat_id: str = Field(
        default="", description="Telegram chat ID to send notifications to"
    )
    enabled: bool = Field(
        default=False, description="Whether Telegram notifications are enabled"
    )
    parse_mode: str = Field(
        default="Markdown", description="Parse mode for Telegram messages"
    )

    _bot_token: SecretStr | None = PrivateAttr(default=None)

    @property
    def bot_token(self) -> str:
        """Retrieve Telegram bot token from secrets."""
        if not self.enabled:
            raise RuntimeError("Telegram notifications are disabled")
        if self._bot_token is None:
            self._bot_token = SecretStr(get_secret("telegram_bot_token"))
        return self._bot_token.get_secret_value()


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

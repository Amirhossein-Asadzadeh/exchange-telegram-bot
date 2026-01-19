from __future__ import annotations

from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Telegram
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    telegram_allowed_chat_ids: str = Field(alias="TELEGRAM_ALLOWED_CHAT_IDS", default="")
    telegram_admin_chat_id: str = Field(alias="TELEGRAM_ADMIN_CHAT_ID", default="")

    # Watcher
    watch_enabled: bool = Field(alias="WATCH_ENABLED", default=True)
    poll_interval_seconds: int = Field(alias="POLL_INTERVAL_SECONDS", default=15, ge=5, le=3600)
    pnl_threshold_usdt: float = Field(alias="PNL_THRESHOLD_USDT", default=0.5, ge=0.0)
    cooldown_seconds: int = Field(alias="COOLDOWN_SECONDS", default=60, ge=0, le=86400)

    # State
    state_path: str = Field(alias="STATE_PATH", default="./state.json")

    # Provider wiring
    exchange_provider_mode: str = Field(alias="EXCHANGE_PROVIDER_MODE", default="sdk")

    sdk_module: str = Field(alias="SDK_MODULE", default="exchange_client")
    sdk_factory: str = Field(alias="SDK_FACTORY")
    sdk_positions_call: str = Field(alias="SDK_POSITIONS_CALL")

    # Bitunix
    bitunix_api_key: str = Field(alias="BITUNIX_API_KEY")
    bitunix_api_secret: str = Field(alias="BITUNIX_API_SECRET")
    bitunix_base_url: str = Field(alias="BITUNIX_BASE_URL", default="https://fapi.bitunix.com")
    bitunix_margin_coin: str = Field(alias="BITUNIX_MARGIN_COIN", default="USDT")

    def allowed_chat_ids(self) -> List[int]:
        raw = [x.strip() for x in self.telegram_allowed_chat_ids.split(",") if x.strip()]
        out: List[int] = []
        for item in raw:
            try:
                out.append(int(item))
            except ValueError:
                continue
        return out

    def admin_chat_id(self) -> Optional[int]:
        if self.telegram_admin_chat_id.strip():
            try:
                return int(self.telegram_admin_chat_id.strip())
            except ValueError:
                return None
        ids = self.allowed_chat_ids()
        return ids[0] if ids else None

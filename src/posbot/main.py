from __future__ import annotations

import logging
from typing import List

from telegram.ext import Application

from posbot.config import Settings
from posbot.logger import setup_logging
from posbot.models import CrossingEvent
from posbot.provider import MockProvider, SdkProvider
from posbot.state_store import BotState, StateStore
from posbot.telegram_bot import TelegramBot
from posbot.watcher import Watcher

log = logging.getLogger("posbot.main")


def build_provider(settings: Settings):
    if settings.exchange_provider_mode.lower() == "mock":
        return MockProvider()

    return SdkProvider(
        module_name=settings.sdk_module,
        factory_path=settings.sdk_factory,
        positions_call=settings.sdk_positions_call,
        api_key=settings.bitunix_api_key,
        api_secret=settings.bitunix_api_secret,
        base_url=settings.bitunix_base_url,
        margin_coin=settings.bitunix_margin_coin,
    )


def main() -> None:
    setup_logging()
    settings = Settings()

    allowed_ids = settings.allowed_chat_ids()
    admin_id = settings.admin_chat_id()
    if not allowed_ids:
        raise RuntimeError("TELEGRAM_ALLOWED_CHAT_IDS is empty. Refusing to start (security).")

    state_store = StateStore(settings.state_path)
    state: BotState = state_store.load()

    # Initialize defaults from env only on fresh state
    if state.last_poll_ts == 0.0 and not state.positions:
        state.watch_enabled = settings.watch_enabled
        state.pnl_threshold = settings.pnl_threshold_usdt
        state.cooldown_seconds = settings.cooldown_seconds
        state_store.save(state)

    provider = build_provider(settings)
    app = Application.builder().token(settings.telegram_bot_token).build()

    def fetch_positions() -> List:
        return provider.get_positions()

    async def notify(ev: CrossingEvent) -> None:
        if admin_id is None:
            return
        title = "✅ LOSS → PROFIT" if ev.direction == "LOSS_TO_PROFIT" else "⚠️ PROFIT → LOSS"
        text = (
            f"{title}\n"
            f"{ev.symbol} {ev.side}\n"
            f"PNL: {ev.from_pnl:.4f} → {ev.to_pnl:.4f} USDT"
        )
        await app.bot.send_message(chat_id=admin_id, text=text)

    TelegramBot(
        application=app,
        state_store=state_store,
        state=state,
        allowed_chat_ids=allowed_ids,
        admin_chat_id=admin_id,
        fetch_positions=fetch_positions,
    )

    watcher = Watcher(
        state_store=state_store,
        state=state,
        fetch_positions=fetch_positions,
        notify=notify,
        poll_interval_seconds=settings.poll_interval_seconds,
    )

    async def _post_init(_: Application) -> None:
        watcher.start()
        log.info("Bot started. allowed_chat_ids=%s admin_chat_id=%s", allowed_ids, admin_id)

    async def _post_shutdown(_: Application) -> None:
        await watcher.stop()

    app.post_init = _post_init
    app.post_shutdown = _post_shutdown

    # ✅ run_polling باید سینک اجرا شود (نه await)
    app.run_polling()


if __name__ == "__main__":
    main()

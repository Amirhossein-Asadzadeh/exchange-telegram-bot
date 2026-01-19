from __future__ import annotations

import logging
import time
from typing import List, Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from posbot.models import Position
from posbot.state_store import BotState, StateStore

log = logging.getLogger("posbot.telegram")


def _is_allowed(chat_id: int, allowed: List[int]) -> bool:
    return chat_id in allowed


def _fmt_age(ts: float) -> str:
    if ts <= 0:
        return "never"
    delta = int(time.time() - ts)
    if delta < 60:
        return f"{delta}s ago"
    if delta < 3600:
        return f"{delta//60}m ago"
    return f"{delta//3600}h ago"


class TelegramBot:
    def __init__(
        self,
        *,
        application: Application,
        state_store: StateStore,
        state: BotState,
        allowed_chat_ids: List[int],
        admin_chat_id: Optional[int],
        fetch_positions,
    ) -> None:
        self.app = application
        self.state_store = state_store
        self.state = state
        self.allowed_chat_ids = allowed_chat_ids
        self.admin_chat_id = admin_chat_id
        self.fetch_positions = fetch_positions

        self._register_handlers()

    def _register_handlers(self) -> None:
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("positions", self.cmd_positions))
        self.app.add_handler(CommandHandler("watch", self.cmd_watch))
        self.app.add_handler(CommandHandler("threshold", self.cmd_threshold))
        self.app.add_handler(CommandHandler("cooldown", self.cmd_cooldown))
        self.app.add_handler(CommandHandler("status", self.cmd_status))

    async def _guard(self, update: Update) -> bool:
        chat_id = update.effective_chat.id if update.effective_chat else 0
        if not self.allowed_chat_ids:
            # If no allowlist is set, hard-deny (safer default)
            await update.message.reply_text("Access denied: allowlist is empty.")
            return False
        if not _is_allowed(chat_id, self.allowed_chat_ids):
            await update.message.reply_text("Access denied.")
            return False
        return True

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        await update.message.reply_text(
            "posbot is running.\nUse /positions, /watch, /threshold, /cooldown, /status"
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        await update.message.reply_text(
            "\n".join(
                [
                    "/positions - show open positions (snapshot)",
                    "/watch on|off - enable/disable watcher alerts",
                    "/threshold <usdt> - hysteresis threshold (e.g. 0.5)",
                    "/cooldown <seconds> - per-position alert cooldown",
                    "/status - bot status + last poll + last error",
                ]
            )
        )

    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return

        try:
            positions: List[Position] = self.fetch_positions()
        except Exception as e:
            await update.message.reply_text(f"Failed to fetch positions: {type(e).__name__}: {e}")
            return

        if not positions:
            await update.message.reply_text("No open positions (or provider returned empty).")
            return

        lines = ["<b>Open positions</b>"]
        for p in positions[:30]:
            pnl = p.unrealized_pnl
            lines.append(
                f"• <code>{p.symbol}</code> {p.side} | PNL: <b>{pnl:.4f}</b> USDT"
            )
        if len(positions) > 30:
            lines.append(f"... +{len(positions)-30} more")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    async def cmd_watch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return

        if not context.args:
            status = "on" if self.state.watch_enabled else "off"
            await update.message.reply_text(f"watch is {status}. Use: /watch on|off")
            return

        arg = context.args[0].lower()
        if arg not in {"on", "off"}:
            await update.message.reply_text("Invalid. Use: /watch on|off")
            return

        self.state.watch_enabled = (arg == "on")
        self.state_store.save(self.state)
        await update.message.reply_text(f"watch set to {arg}")

    async def cmd_threshold(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return

        if not context.args:
            await update.message.reply_text(f"threshold is {self.state.pnl_threshold}. Use: /threshold 0.5")
            return

        try:
            val = float(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid number. Example: /threshold 0.5")
            return

        if val < 0:
            await update.message.reply_text("threshold must be >= 0")
            return

        self.state.pnl_threshold = val
        self.state_store.save(self.state)
        await update.message.reply_text(f"threshold set to {val}")

    async def cmd_cooldown(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return

        if not context.args:
            await update.message.reply_text(
                f"cooldown is {self.state.cooldown_seconds}s. Use: /cooldown 600"
            )
            return

        try:
            val = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid integer. Example: /cooldown 600")
            return

        if val < 0:
            await update.message.reply_text("cooldown must be >= 0")
            return

        self.state.cooldown_seconds = val
        self.state_store.save(self.state)
        await update.message.reply_text(f"cooldown set to {val}s")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return

        watch = "on" if self.state.watch_enabled else "off"
        msg = "\n".join(
            [
                f"watch: {watch}",
                f"threshold: {self.state.pnl_threshold}",
                f"cooldown: {self.state.cooldown_seconds}s",
                f"last poll: {_fmt_age(self.state.last_poll_ts)}",
                f"last error: {self.state.last_error or '-'}",
                f"tracked positions: {len(self.state.positions)}",
            ]
        )
        await update.message.reply_text(msg)

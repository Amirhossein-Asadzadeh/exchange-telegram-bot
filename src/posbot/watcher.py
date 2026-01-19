from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, List, Optional

from posbot.models import CrossingEvent, Position
from posbot.state_store import BotState, PositionState, StateStore

log = logging.getLogger("posbot.watcher")


def detect_crossing(
    prev_pnl: float,
    now_pnl: float,
    threshold: float,
) -> Optional[str]:
    """
    Hysteresis crossing:
      - LOSS_TO_PROFIT when prev <= -T and now >= +T
      - PROFIT_TO_LOSS when prev >= +T and now <= -T
    """
    t = float(threshold)
    if prev_pnl <= -t and now_pnl >= +t:
        return "LOSS_TO_PROFIT"
    if prev_pnl >= +t and now_pnl <= -t:
        return "PROFIT_TO_LOSS"
    return None


class Watcher:
    def __init__(
        self,
        *,
        state_store: StateStore,
        state: BotState,
        fetch_positions: Callable[[], List[Position]],
        notify: Callable[[CrossingEvent], "asyncio.Future[None]"],
        poll_interval_seconds: int,
    ) -> None:
        self.state_store = state_store
        self.state = state
        self.fetch_positions = fetch_positions
        self.notify = notify
        self.poll_interval_seconds = poll_interval_seconds

        self._task: Optional[asyncio.Task[None]] = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self.run(), name="watcher")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await asyncio.wait([self._task], timeout=5)

    async def run(self) -> None:
        log.info("Watcher started. poll_interval=%ss", self.poll_interval_seconds)
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                log.exception("Watcher tick failed: %s", msg)
                self.state_store.touch_error(self.state, msg)
            await asyncio.sleep(self.poll_interval_seconds)

    async def _tick(self) -> None:
        if not self.state.watch_enabled:
            return

        now = time.time()
        positions = self.fetch_positions()
        self.state.last_poll_ts = now
        self.state.last_error = ""
        seen_keys = set()

        for pos in positions:
            key = pos.key
            seen_keys.add(key)

            ps = self.state.positions.get(key) or PositionState()
            prev = float(ps.last_pnl)
            cur = float(pos.unrealized_pnl)

            ps.last_seen_ts = now

            direction = detect_crossing(prev, cur, threshold=self.state.pnl_threshold)
            if direction:
                if (now - ps.last_alert_ts) >= float(self.state.cooldown_seconds):
                    ev = CrossingEvent(
                        position_key=key,
                        symbol=pos.symbol,
                        side=pos.side,
                        from_pnl=prev,
                        to_pnl=cur,
                        direction=direction,
                    )
                    await self.notify(ev)
                    ps.last_alert_ts = now
                else:
                    log.info("Suppressed alert due to cooldown. key=%s", key)

            ps.last_pnl = cur
            self.state.positions[key] = ps

        # Optional: you can clean up stale positions here if needed (not required for MVP)

        self.state_store.save(self.state)
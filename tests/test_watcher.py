from __future__ import annotations

import asyncio

from posbot.models import Position
from posbot.state_store import BotState, StateStore
from posbot.watcher import Watcher


class SeqProvider:
    def __init__(self, seq: list[list[Position]]):
        self.seq = seq
        self.i = 0

    def get_positions(self) -> list[Position]:
        out = self.seq[self.i]
        self.i = min(self.i + 1, len(self.seq) - 1)
        return out


def test_profit_to_loss_crossing_triggers_once(tmp_path, monkeypatch):
    provider = SeqProvider(
        [
            [Position(symbol="BTCUSDT", side="LONG", unrealized_pnl=+10.0)],
            [Position(symbol="BTCUSDT", side="LONG", unrealized_pnl=-10.0)],
        ]
    )

    events = []

    async def notify(ev):
        events.append(ev)

    # کنترل زمان
    t = {"now": 0.0}
    monkeypatch.setattr("posbot.watcher.time.time", lambda: t["now"])

    state = BotState(watch_enabled=True, pnl_threshold=1.0, cooldown_seconds=0)
    store = StateStore(str(tmp_path / "state.json"))

    w = Watcher(
        state_store=store,
        state=state,
        fetch_positions=provider.get_positions,
        notify=notify,
        poll_interval_seconds=999,
    )

    asyncio.run(w._tick())  # baseline
    t["now"] = 1.0
    asyncio.run(w._tick())  # crossing => alert

    assert len(events) == 1
    assert events[0].direction == "PROFIT_TO_LOSS"


def test_no_alert_without_crossing(tmp_path, monkeypatch):
    provider = SeqProvider(
        [
            [Position(symbol="BTCUSDT", side="LONG", unrealized_pnl=-100.0)],
            [Position(symbol="BTCUSDT", side="LONG", unrealized_pnl=-200.0)],
        ]
    )

    events = []

    async def notify(ev):
        events.append(ev)

    t = {"now": 0.0}
    monkeypatch.setattr("posbot.watcher.time.time", lambda: t["now"])

    state = BotState(watch_enabled=True, pnl_threshold=1.0, cooldown_seconds=0)
    store = StateStore(str(tmp_path / "state.json"))

    w = Watcher(
        state_store=store,
        state=state,
        fetch_positions=provider.get_positions,
        notify=notify,
        poll_interval_seconds=999,
    )

    asyncio.run(w._tick())
    t["now"] = 1.0
    asyncio.run(w._tick())

    assert events == []


def test_cooldown_blocks_spam(tmp_path, monkeypatch):
    provider = SeqProvider(
        [
            [Position(symbol="BTCUSDT", side="LONG", unrealized_pnl=+10.0)],
            [Position(symbol="BTCUSDT", side="LONG", unrealized_pnl=-10.0)],
            [Position(symbol="BTCUSDT", side="LONG", unrealized_pnl=+10.0)],
            [Position(symbol="BTCUSDT", side="LONG", unrealized_pnl=-10.0)],
        ]
    )

    events = []

    async def notify(ev):
        events.append(ev)

    # زمان fake اما واقعی‌نما
    base = 1_700_000_000.0
    t = {"now": base}
    monkeypatch.setattr("posbot.watcher.time.time", lambda: t["now"])

    state = BotState(
        watch_enabled=True,
        pnl_threshold=1.0,
        cooldown_seconds=600,
    )
    store = StateStore(str(tmp_path / "state.json"))

    w = Watcher(
        state_store=store,
        state=state,
        fetch_positions=provider.get_positions,
        notify=notify,
        poll_interval_seconds=999,
    )

    asyncio.run(w._tick())        # baseline
    t["now"] = base + 1
    asyncio.run(w._tick())        # crossing => alert
    t["now"] = base + 2
    asyncio.run(w._tick())        # cooldown => blocked
    t["now"] = base + 3
    asyncio.run(w._tick())        # cooldown => blocked

    assert len(events) == 1



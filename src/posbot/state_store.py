from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class PositionState:
    last_pnl: float = 0.0
    last_alert_ts: float = 0.0
    last_seen_ts: float = 0.0


@dataclass
class BotState:
    positions: Dict[str, PositionState] = field(default_factory=dict)
    watch_enabled: bool = True
    pnl_threshold: float = 0.5
    cooldown_seconds: int = 600
    last_poll_ts: float = 0.0
    last_error: str = ""


class StateStore:
    def __init__(self, path: str) -> None:
        self.path = path

    def load(self) -> BotState:
        if not os.path.exists(self.path):
            return BotState()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            return BotState()

        state = BotState()
        state.watch_enabled = bool(raw.get("watch_enabled", True))
        state.pnl_threshold = float(raw.get("pnl_threshold", 0.5))
        state.cooldown_seconds = int(raw.get("cooldown_seconds", 600))
        state.last_poll_ts = float(raw.get("last_poll_ts", 0.0))
        state.last_error = str(raw.get("last_error", ""))

        pos_raw = raw.get("positions", {}) if isinstance(raw.get("positions", {}), dict) else {}
        for key, val in pos_raw.items():
            if not isinstance(val, dict):
                continue
            state.positions[key] = PositionState(
                last_pnl=float(val.get("last_pnl", 0.0)),
                last_alert_ts=float(val.get("last_alert_ts", 0.0)),
                last_seen_ts=float(val.get("last_seen_ts", 0.0)),
            )
        return state

    def save(self, state: BotState) -> None:
        payload = {
            "watch_enabled": state.watch_enabled,
            "pnl_threshold": state.pnl_threshold,
            "cooldown_seconds": state.cooldown_seconds,
            "last_poll_ts": state.last_poll_ts,
            "last_error": state.last_error,
            "positions": {
                k: {
                    "last_pnl": v.last_pnl,
                    "last_alert_ts": v.last_alert_ts,
                    "last_seen_ts": v.last_seen_ts,
                }
                for k, v in state.positions.items()
            },
        }
        self._atomic_write_json(payload)

    def touch_error(self, state: BotState, msg: str) -> None:
        state.last_error = msg[:400]
        state.last_poll_ts = time.time()
        self.save(state)

    def _atomic_write_json(self, payload: dict) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix="state_", suffix=".json", dir=os.path.dirname(self.path) or ".")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.path)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

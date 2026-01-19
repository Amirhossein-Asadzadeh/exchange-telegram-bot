from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Position:
    symbol: str
    side: str  # "LONG"/"SHORT" or similar
    unrealized_pnl: float
    qty: Optional[float] = None
    entry_price: Optional[float] = None
    mark_price: Optional[float] = None

    @property
    def key(self) -> str:
        return f"{self.symbol}:{self.side}".upper()


@dataclass(frozen=True)
class CrossingEvent:
    position_key: str
    symbol: str
    side: str
    from_pnl: float
    to_pnl: float
    direction: str  # "LOSS_TO_PROFIT" | "PROFIT_TO_LOSS"
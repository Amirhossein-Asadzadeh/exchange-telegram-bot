from __future__ import annotations
import inspect

import inspect
import importlib
import logging
from typing import Any, Callable, List, Protocol

from posbot.models import Position

log = logging.getLogger("posbot.provider")


class ExchangeProvider(Protocol):
    def get_positions(self) -> List[Position]: ...


def _import_from_path(path: str) -> Any:
    if ":" in path:
        mod, attr = path.split(":", 1)
        module = importlib.import_module(mod)
        return getattr(module, attr)
    return importlib.import_module(path)


class SdkProvider:
    def __init__(
        self,
        module_name: str,
        factory_path: str,
        positions_call: str,
        api_key: str,
        api_secret: str,
        base_url: str,
        margin_coin: str,
    ) -> None:
        self.module_name = module_name
        self.factory_path = factory_path
        self.positions_call = positions_call
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.margin_coin = margin_coin

        self.client = self._build_client()

    def _construct_client(self, factory_obj: Any) -> Any:
        sig = inspect.signature(factory_obj)
        params = sig.parameters
        kwargs: dict[str, Any] = {}

        if "api_key" in params:
            kwargs["api_key"] = self.api_key
        if "secret_key" in params:
            kwargs["secret_key"] = self.api_secret
        if "config" in params:
            mod = importlib.import_module("exchange_client.adapters.bitunix")
            BitunixConfig = getattr(mod, "BitunixConfig")
            kwargs["config"] = BitunixConfig(base_url=self.base_url)

        return factory_obj(**kwargs)

    def _build_client(self) -> Any:
        importlib.import_module(self.module_name)
        factory_obj = _import_from_path(self.factory_path)
        return self._construct_client(factory_obj)

    def get_positions(self) -> List[Position]:
        fn: Callable[..., Any] = getattr(self.client, self.positions_call)

        sig = inspect.signature(fn)
        params = list(sig.parameters.values())

        # if the first positional parameter is margin_coin, pass it; otherwise call with no args
        if params and params[0].name in {"margin_coin", "marginCoin"}:
            raw = fn(self.margin_coin)
        else:
            raw = fn()

        if isinstance(raw, dict):
            for key in ("data", "result", "account"):
                if key in raw:
                    raw = raw[key]
                    break

            if isinstance(raw, dict):
                if "positions" in raw:
                    raw = raw["positions"]
                elif "positionList" in raw:
                    raw = raw["positionList"]
                elif "list" in raw:
                    raw = raw["list"]
                else:
                    raw = []
            # اگر raw["data"] خودش list بود، همینطور می‌ماند (دقیقاً کیس Bitunix)


        out: List[Position] = []
        for item in raw or []:
            symbol = str(item.get("symbol", ""))
            pnl = float(
                item.get("unrealizedPnl")
                or item.get("unrealizedPNL")
                or item.get("unrealizedProfit")
                or 0
            )

            side = str(item.get("side", "UNKNOWN"))
            out.append(Position(symbol=symbol, side=side, unrealized_pnl=pnl))

        return out


class MockProvider:
    def __init__(self) -> None:
        self._tick = 0

    def get_positions(self) -> List[Position]:
        self._tick += 1
        pnl = -1.0 + 0.2 * (self._tick % 15)
        return [Position(symbol="BTCUSDT", side="LONG", unrealized_pnl=pnl)]

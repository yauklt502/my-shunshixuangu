"""Market data service — overview, quotes, klines."""

from __future__ import annotations

from typing import Optional

from src.common import BarPeriod, Environment

from .eastmoney_adapter import EastmoneyAdapter
from .pipeline import DataPipeline, get_active_source, list_sources, set_active_source

__all__ = [
    "get_active_source",
    "get_klines",
    "get_market_overview",
    "get_quote",
    "list_sources",
    "set_active_source",
]


def get_market_overview(source: Optional[str] = None) -> dict:
    src = source or get_active_source()
    if src == "eastmoney":
        return EastmoneyAdapter().fetch_market_overview()
    return {"index_sh": None, "breadth_up": None, "breadth_down": None, "north_flow": None, "source": src}


def get_quote(symbol: str, source: Optional[str] = None) -> Optional[dict]:
    src = source or get_active_source()
    if src == "eastmoney":
        q = EastmoneyAdapter().fetch_quote(symbol)
        if q:
            q["source"] = src
        return q
    pipeline = DataPipeline(Environment.LIVE, primary=src)
    bar = pipeline.get_realtime_bar(symbol, BarPeriod.DAILY)
    if not bar:
        return None
    return {
        "symbol": symbol,
        "price": bar.close,
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "volume": bar.volume,
        "source": src,
    }


def get_klines(symbol: str, period: str = "daily", limit: int = 120, source: Optional[str] = None) -> list:
    src = source or get_active_source()
    pipeline = DataPipeline(Environment.LIVE, primary=src)
    bars = pipeline.get_historical(symbol, BarPeriod(period), limit=limit)
    return [b.to_dict() for b in bars]

"""Market data service — overview, quotes, klines."""

from __future__ import annotations

from typing import Optional

from src.common import BarPeriod, Environment

from .eastmoney_adapter import EastmoneyAdapter
from .mock_adapter import MockDataSource
from .pipeline import SOURCE_REGISTRY, DataPipeline, get_active_source, list_sources, set_active_source

__all__ = [
    "check_data_source_health",
    "get_active_source",
    "get_klines",
    "get_market_overview",
    "get_quote",
    "list_sources",
    "set_active_source",
]


def check_data_source_health(source: Optional[str] = None) -> dict:
    src = source or get_active_source()
    labels = {item["id"]: item["name"] for item in list_sources()}
    name = labels.get(src, src)
    if src not in SOURCE_REGISTRY:
        return {"ok": False, "source": src, "name": name, "message": f"未知数据源: {src}"}

    adapter = MockDataSource() if src == "mock" else SOURCE_REGISTRY[src]()
    ok = adapter.health_check()
    detail = ""
    if src == "eastmoney" and not ok:
        detail = "东方财富接口无响应，请检查网络或稍后重试"
    elif src == "tushare" and not ok:
        detail = "Tushare 未配置 Token，请在环境变量 TUSHARE_TOKEN 中设置"
    elif not ok:
        detail = f"{name} 暂不可用"

    return {
        "ok": ok,
        "source": src,
        "name": name,
        "message": "连接正常" if ok else detail or f"{name} 连接失败",
    }


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

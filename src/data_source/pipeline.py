"""Data source registry and pipeline factory."""

from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional

from src.common import BarPeriod, Environment, KlineBar

from .base import DataSource
from .cache import DataCache
from .eastmoney_adapter import EastmoneyAdapter
from .failover import FailoverDataSource
from .mock_adapter import MockDataSource
from .mootdx_adapter import MootdxAdapter
from .ths_adapter import ThsAdapter
from .tushare_adapter import TushareAdapter

SOURCE_REGISTRY: dict[str, type[DataSource]] = {
    "eastmoney": EastmoneyAdapter,
    "tushare": TushareAdapter,
    "mootdx": MootdxAdapter,
    "ths": ThsAdapter,
    "mock": MockDataSource,
}

# Module-level active source (can be switched via API)
_active_source: str = os.environ.get("DATA_SOURCE", "eastmoney")


def list_sources() -> list[dict]:
    return [
        {"id": "eastmoney", "name": "东方财富实时", "realtime": True},
        {"id": "tushare", "name": "Tushare", "realtime": False},
        {"id": "mootdx", "name": "Mootdx", "realtime": True},
        {"id": "ths", "name": "同花顺", "realtime": True},
        {"id": "mock", "name": "本地模拟", "realtime": False},
    ]


def get_active_source() -> str:
    return _active_source


def set_active_source(source_id: str) -> bool:
    global _active_source
    if source_id not in SOURCE_REGISTRY:
        return False
    _active_source = source_id
    os.environ["DATA_SOURCE"] = source_id
    return True


def build_pipeline(
    environment: Environment,
    primary: Optional[str] = None,
    cache: Optional[DataCache] = None,
) -> FailoverDataSource:
    cache = cache or DataCache()
    primary = primary or _active_source

    adapters: List[DataSource] = []
    if primary in SOURCE_REGISTRY:
        adapters.append(SOURCE_REGISTRY[primary](cache))

    fallback_order = ["eastmoney", "mootdx", "tushare", "ths", "mock"]
    if environment == Environment.BACKTEST:
        fallback_order = ["tushare", "eastmoney", "mootdx", "ths", "mock"]

    for name in fallback_order:
        if name != primary and name in SOURCE_REGISTRY:
            adapters.append(SOURCE_REGISTRY[name](cache))

    return FailoverDataSource(adapters)


class DataPipeline:
    """Backtest and live pipelines are strictly isolated."""

    def __init__(
        self,
        environment: Environment,
        cache: Optional[DataCache] = None,
        primary: Optional[str] = None,
    ):
        self.environment = environment
        self._source = build_pipeline(environment, primary, cache)

    def get_historical(
        self,
        symbol: str,
        period: BarPeriod,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[KlineBar]:
        if self.environment == Environment.LIVE and end is None:
            end = datetime.now()
        return self._source.fetch_klines(symbol, period, start, end, limit)

    def get_realtime_bar(self, symbol: str, period: BarPeriod) -> Optional[KlineBar]:
        if self.environment == Environment.BACKTEST:
            raise RuntimeError("Backtest pipeline cannot access realtime data")
        return self._source.fetch_realtime_bar(symbol, period)

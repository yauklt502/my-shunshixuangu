"""Isolated data pipelines for backtest vs live — prevents future-function leakage."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from src.common import BarPeriod, Environment, KlineBar

from .base import DataSource
from .cache import DataCache
from .failover import FailoverDataSource
from .mock_adapter import MockDataSource
from .mootdx_adapter import MootdxAdapter
from .tushare_adapter import TushareAdapter


class DataPipeline:
    """Backtest and live pipelines are strictly isolated."""

    def __init__(self, environment: Environment, cache: Optional[DataCache] = None):
        self.environment = environment
        cache = cache or DataCache()
        if environment == Environment.BACKTEST:
            # Backtest: historical only, mock fallback for offline dev
            self._source: DataSource = FailoverDataSource(
                [TushareAdapter(cache), MootdxAdapter(cache), MockDataSource()]
            )
        else:
            # Live: realtime stream sources
            self._source: DataSource = FailoverDataSource(
                [MootdxAdapter(cache), TushareAdapter(cache)]
            )

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

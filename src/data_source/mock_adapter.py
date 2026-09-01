"""Mock data source for backtest demos without external APIs."""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from typing import List, Optional

from src.common import BarPeriod, KlineBar

from .base import DataSource


class MockDataSource(DataSource):
    name = "mock"

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    def fetch_klines(
        self,
        symbol: str,
        period: BarPeriod,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[KlineBar]:
        start = start or datetime.now() - timedelta(days=limit)
        price = 10.0 + self._rng.uniform(0, 20)
        bars: List[KlineBar] = []
        for i in range(limit):
            ts = start + timedelta(days=i)
            if end and ts > end:
                break
            drift = math.sin(i / 15) * 0.3
            change = self._rng.uniform(-0.02, 0.02) + drift * 0.01
            open_p = price
            close_p = max(0.01, price * (1 + change))
            high_p = max(open_p, close_p) * (1 + self._rng.uniform(0, 0.01))
            low_p = min(open_p, close_p) * (1 - self._rng.uniform(0, 0.01))
            vol = self._rng.uniform(1e6, 5e6)
            bars.append(
                KlineBar(
                    symbol=symbol,
                    timestamp=ts,
                    open=round(open_p, 2),
                    high=round(high_p, 2),
                    low=round(low_p, 2),
                    close=round(close_p, 2),
                    volume=round(vol, 0),
                    period=period,
                )
            )
            price = close_p
        return bars

    def fetch_realtime_bar(self, symbol: str, period: BarPeriod) -> Optional[KlineBar]:
        bars = self.fetch_klines(symbol, period, limit=1)
        return bars[-1] if bars else None

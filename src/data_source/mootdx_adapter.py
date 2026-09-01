"""Mootdx data adapter."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from src.common import BarPeriod, KlineBar

from .base import DataSource
from .cache import DataCache


class MootdxAdapter(DataSource):
    name = "mootdx"

    def __init__(self, cache: Optional[DataCache] = None):
        self.cache = cache or DataCache()
        self._client = None
        try:
            from mootdx.quotes import Quotes

            self._client = Quotes.factory(market="std")
        except ImportError:
            pass

    def fetch_klines(
        self,
        symbol: str,
        period: BarPeriod,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[KlineBar]:
        params = {
            "symbol": symbol,
            "period": period.value,
            "start": start,
            "end": end,
            "limit": limit,
        }
        cached = self.cache.get("mootdx_klines", params)
        if cached:
            return [self._dict_to_bar(d) for d in cached]

        if not self._client:
            return []

        freq_map = {
            BarPeriod.MIN1: 8,
            BarPeriod.MIN5: 0,
            BarPeriod.MIN60: 1,
            BarPeriod.DAILY: 4,
        }
        freq = freq_map.get(period, 4)
        df = self._client.bars(symbol=symbol, frequency=freq, offset=limit)
        if df is None or df.empty:
            return []

        bars: List[KlineBar] = []
        for _, row in df.iterrows():
            ts = row.get("datetime") or row.get("date")
            if isinstance(ts, str):
                timestamp = datetime.fromisoformat(ts.replace(" ", "T")[:19])
            else:
                timestamp = datetime.now()
            bars.append(
                KlineBar(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("vol", row.get("volume", 0))),
                    period=period,
                )
            )
        self.cache.set("mootdx_klines", params, [b.to_dict() for b in bars])
        return bars

    def fetch_realtime_bar(self, symbol: str, period: BarPeriod) -> Optional[KlineBar]:
        bars = self.fetch_klines(symbol, period, limit=1)
        return bars[-1] if bars else None

    def _dict_to_bar(self, d: dict) -> KlineBar:
        return KlineBar(
            symbol=d["symbol"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            open=d["open"],
            high=d["high"],
            low=d["low"],
            close=d["close"],
            volume=d["volume"],
            period=BarPeriod(d["period"]),
            indicators=d.get("indicators", {}),
        )

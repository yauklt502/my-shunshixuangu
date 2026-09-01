"""Tushare data adapter (requires tushare token in env)."""

from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional

from src.common import BarPeriod, KlineBar

from .base import DataSource
from .cache import DataCache


class TushareAdapter(DataSource):
    name = "tushare"

    def __init__(self, cache: Optional[DataCache] = None):
        self.cache = cache or DataCache()
        self._pro = None
        token = os.environ.get("TUSHARE_TOKEN")
        if token:
            try:
                import tushare as ts

                ts.set_token(token)
                self._pro = ts.pro_api()
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
        cached = self.cache.get("tushare_klines", params)
        if cached:
            return [self._dict_to_bar(d) for d in cached]

        if not self._pro:
            return []

        ts_code = self._to_ts_code(symbol)
        start_str = start.strftime("%Y%m%d") if start else None
        end_str = end.strftime("%Y%m%d") if end else None

        if period == BarPeriod.DAILY:
            df = self._pro.daily(ts_code=ts_code, start_date=start_str, end_date=end_str)
        else:
            return []

        if df is None or df.empty:
            return []

        bars: List[KlineBar] = []
        for _, row in df.tail(limit).iterrows():
            bars.append(
                KlineBar(
                    symbol=symbol,
                    timestamp=datetime.strptime(str(row["trade_date"]), "%Y%m%d"),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["vol"]),
                    period=period,
                )
            )
        self.cache.set("tushare_klines", params, [b.to_dict() for b in bars])
        return bars

    def fetch_realtime_bar(self, symbol: str, period: BarPeriod) -> Optional[KlineBar]:
        bars = self.fetch_klines(symbol, period, limit=1)
        return bars[-1] if bars else None

    def _to_ts_code(self, symbol: str) -> str:
        if symbol.endswith(".SH") or symbol.endswith(".SZ"):
            return symbol
        if symbol.startswith("6"):
            return f"{symbol}.SH"
        return f"{symbol}.SZ"

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

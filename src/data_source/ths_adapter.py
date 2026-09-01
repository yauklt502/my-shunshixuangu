"""同花顺 iFinD / 开放平台 HTTP 适配器（需配置 THS_API_URL）."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import List, Optional

from src.common import BarPeriod, KlineBar

from .base import DataSource
from .cache import DataCache


class ThsAdapter(DataSource):
    name = "ths"

    def __init__(self, cache: Optional[DataCache] = None):
        self.cache = cache or DataCache()
        self.api_url = os.environ.get("THS_API_URL", "").rstrip("/")
        self.api_token = os.environ.get("THS_API_TOKEN", "")

    def health_check(self) -> bool:
        return bool(self.api_url)

    def fetch_klines(
        self,
        symbol: str,
        period: BarPeriod,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[KlineBar]:
        if not self.api_url:
            return []

        params = {"symbol": symbol, "period": period.value, "limit": limit}
        cached = self.cache.get("ths_klines", params)
        if cached:
            return [self._to_bar(d) for d in cached]

        query = urllib.parse.urlencode(params)
        url = f"{self.api_url}/klines?{query}"
        try:
            req = urllib.request.Request(url)
            if self.api_token:
                req.add_header("Authorization", f"Bearer {self.api_token}")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            return []

        items = data if isinstance(data, list) else data.get("data", [])
        bars = [self._to_bar(item) for item in items[:limit]]
        self.cache.set("ths_klines", params, [b.to_dict() for b in bars])
        return bars

    def fetch_realtime_bar(self, symbol: str, period: BarPeriod) -> Optional[KlineBar]:
        bars = self.fetch_klines(symbol, period, limit=1)
        return bars[-1] if bars else None

    def _to_bar(self, d: dict) -> KlineBar:
        ts = d.get("timestamp") or d.get("trade_date")
        if isinstance(ts, str):
            timestamp = datetime.fromisoformat(ts.replace(" ", "T")[:19])
        else:
            timestamp = datetime.now()
        return KlineBar(
            symbol=d.get("symbol", ""),
            timestamp=timestamp,
            open=float(d["open"]),
            high=float(d["high"]),
            low=float(d["low"]),
            close=float(d["close"]),
            volume=float(d.get("volume", d.get("vol", 0))),
            period=BarPeriod(d.get("period", "daily")),
        )

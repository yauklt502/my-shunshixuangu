"""东方财富 (East Money) 实时行情与 K 线适配器."""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime
from typing import List, Optional

from src.common import BarPeriod, KlineBar

from .base import DataSource
from .cache import DataCache

logger = logging.getLogger(__name__)

# klt: 1=1min 5=5min 15=15min 30=30min 60=60min 101=day 102=week 103=month
KLT_MAP = {
    BarPeriod.MIN1: "1",
    BarPeriod.MIN5: "5",
    BarPeriod.MIN60: "60",
    BarPeriod.DAILY: "101",
}

KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
QUOTE_URL = "https://push2.eastmoney.com/api/qt/stock/get"
INDEX_URL = "https://push2.eastmoney.com/api/qt/stock/get"
BREADTH_URL = "https://push2.eastmoney.com/api/qt/clist/get"
NORTH_URL = "https://push2.eastmoney.com/api/qt/kamt/get"


class EastmoneyAdapter(DataSource):
    name = "eastmoney"

    def __init__(self, cache: Optional[DataCache] = None):
        self.cache = cache or DataCache(ttl_seconds=15)

    def health_check(self) -> bool:
        try:
            self._http_get(QUOTE_URL, {"secid": "1.000001", "fields": "f43,f169,f170"})
            return True
        except Exception:
            return False

    @staticmethod
    def to_secid(symbol: str) -> str:
        code = symbol.split(".")[0]
        if symbol.endswith(".SH") or code.startswith(("5", "6", "9")):
            return f"1.{code}"
        return f"0.{code}"

    def fetch_klines(
        self,
        symbol: str,
        period: BarPeriod,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[KlineBar]:
        params = {"symbol": symbol, "period": period.value, "limit": limit}
        cached = self.cache.get("em_klines", params)
        if cached:
            return [self._dict_to_bar(d) for d in cached]

        secid = self.to_secid(symbol)
        klt = KLT_MAP.get(period, "101")
        query = {
            "secid": secid,
            "klt": klt,
            "fqt": "1",
            "lmt": str(limit),
            "end": "20500101",
            "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        }
        try:
            data = self._http_get(KLINE_URL, query)
        except Exception as e:
            logger.warning("Eastmoney klines failed: %s", e)
            return []

        klines = data.get("data", {}).get("klines") or []
        bars: List[KlineBar] = []
        for row in klines:
            parts = row.split(",")
            if len(parts) < 6:
                continue
            ts = datetime.strptime(parts[0], "%Y-%m-%d")
            bars.append(
                KlineBar(
                    symbol=symbol,
                    timestamp=ts,
                    open=float(parts[1]),
                    close=float(parts[2]),
                    high=float(parts[3]),
                    low=float(parts[4]),
                    volume=float(parts[5]),
                    period=period,
                )
            )
        self.cache.set("em_klines", params, [b.to_dict() for b in bars])
        return bars

    def fetch_realtime_bar(self, symbol: str, period: BarPeriod) -> Optional[KlineBar]:
        quote = self.fetch_quote(symbol)
        if not quote:
            bars = self.fetch_klines(symbol, period, limit=1)
            return bars[-1] if bars else None
        return KlineBar(
            symbol=symbol,
            timestamp=datetime.now(),
            open=quote["open"],
            high=quote["high"],
            low=quote["low"],
            close=quote["price"],
            volume=quote["volume"],
            period=period,
        )

    def fetch_quote(self, symbol: str) -> Optional[dict]:
        secid = self.to_secid(symbol)
        fields = "f43,f44,f45,f46,f47,f48,f57,f58,f60,f169,f170"
        try:
            data = self._http_get(QUOTE_URL, {"secid": secid, "fields": fields})
        except Exception:
            return None
        item = data.get("data")
        if not item:
            return None
        price = item.get("f43")
        if price is None or price == "-":
            return None
        scale = 100.0
        return {
            "symbol": symbol,
            "name": item.get("f58", ""),
            "price": float(price) / scale,
            "open": float(item.get("f46", 0) or 0) / scale,
            "high": float(item.get("f44", 0) or 0) / scale,
            "low": float(item.get("f45", 0) or 0) / scale,
            "volume": float(item.get("f47", 0) or 0),
            "change_pct": float(item.get("f170", 0) or 0) / 100,
        }

    def fetch_market_overview(self) -> dict:
        overview = {"index_sh": None, "breadth_up": None, "breadth_down": None, "north_flow": None}
        try:
            idx = self._http_get(INDEX_URL, {"secid": "1.000001", "fields": "f43,f169,f170,f58"})
            d = idx.get("data") or {}
            if d.get("f43"):
                overview["index_sh"] = {
                    "name": d.get("f58", "上证指数"),
                    "price": float(d["f43"]) / 100,
                    "change_pct": float(d.get("f170", 0) or 0) / 100,
                }
        except Exception as e:
            logger.warning("Eastmoney index failed: %s", e)

        try:
            breadth = self._http_get(
                BREADTH_URL,
                {
                    "pn": "1",
                    "pz": "5000",
                    "po": "1",
                    "np": "1",
                    "fltt": "2",
                    "invt": "2",
                    "fid": "f3",
                    "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                    "fields": "f3,f12,f14",
                },
            )
            items = breadth.get("data", {}).get("diff") or []
            up = sum(1 for i in items if float(i.get("f3", 0) or 0) > 0)
            down = sum(1 for i in items if float(i.get("f3", 0) or 0) < 0)
            overview["breadth_up"] = up
            overview["breadth_down"] = down
        except Exception as e:
            logger.warning("Eastmoney breadth failed: %s", e)

        try:
            north = self._http_get(NORTH_URL, {"fields1": "f1,f2,f3,f4", "fields2": "f51,f52,f53,f54,f55,f56"})
            d = north.get("data") or {}
            # f52: 北向资金净流入（万元）
            flow = d.get("f52")
            if flow is not None:
                overview["north_flow"] = float(flow) / 1e4  # 转为亿
        except Exception as e:
            logger.warning("Eastmoney north flow failed: %s", e)

        return overview

    def _http_get(self, url: str, params: dict) -> dict:
        qs = urllib.parse.urlencode(params)
        req = urllib.request.Request(
            f"{url}?{qs}",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://quote.eastmoney.com/",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())

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

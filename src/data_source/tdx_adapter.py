"""通达信 TDX 行情适配器 — 基于 tdx-mcp / eltdx 直连通达信服务器."""

from __future__ import annotations

import logging
import re
import threading
from datetime import datetime
from typing import List, Optional

from src.common import BarPeriod, KlineBar

from .base import DataSource
from .cache import DataCache

logger = logging.getLogger(__name__)

PERIOD_MAP = {
    BarPeriod.MIN1: "1min",
    BarPeriod.MIN5: "5min",
    BarPeriod.MIN60: "60min",
    BarPeriod.DAILY: "day",
}

_client = None
_client_lock = threading.Lock()


def _get_client():
    """复用 eltdx 连接（与 tdx-mcp 相同后端）."""
    global _client
    with _client_lock:
        if _client is None:
            try:
                from eltdx.client import TdxClient

                _client = TdxClient(timeout=10.0, probe_hosts=True, pool_size=2)
                _client.connect()
            except ImportError as exc:
                raise RuntimeError("请安装通达信数据源: pip install 'eltdx>=0.5.0,<1.0'") from exc
        return _client


def normalize_tdx_code(code: str) -> str:
    """统一为 eltdx 格式 sh600519 / sz000001."""
    try:
        from eltdx.protocol.unit import add_prefix

        return add_prefix(code.strip())
    except ImportError:
        pass

    code = code.strip()
    prefix = code[:2].lower()
    if prefix in ("sz", "sh", "bj"):
        return code[:2].lower() + code[2:].zfill(6)[-6:]
    if "." in code:
        parts = code.rsplit(".", 1)
        c, m = parts[0].zfill(6), parts[1].upper()
        return ("sh" if m.startswith("SH") else "sz") + c
    c = re.sub(r"\D", "", code).zfill(6)[-6:]
    if c.startswith("6"):
        return f"sh{c}"
    if c.startswith(("4", "8", "9")):
        return f"bj{c}"
    return f"sz{c}"


def to_plain_symbol(tdx_code: str) -> str:
    tdx_code = tdx_code.strip().lower()
    if tdx_code[:2] in ("sh", "sz", "bj"):
        return tdx_code[2:]
    return re.sub(r"\D", "", tdx_code).zfill(6)[-6:]


class TdxAdapter(DataSource):
    """通达信 TCP 行情 — 同源 https://github.com/Neoooo0909/tdx-mcp."""

    name = "tdx"

    def __init__(self, cache: Optional[DataCache] = None):
        self.cache = cache or DataCache(ttl_seconds=10)
        self._available: Optional[bool] = None

    def health_check(self) -> bool:
        try:
            client = _get_client()
            quotes = client.get_quote("sz000001")
            ok = bool(quotes and quotes[0].last_price > 0)
            self._available = ok
            return ok
        except Exception as e:
            logger.warning("TDX health check failed: %s", e)
            self._available = False
            return False

    def fetch_klines(
        self,
        symbol: str,
        period: BarPeriod,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[KlineBar]:
        tdx_code = normalize_tdx_code(symbol)
        period_str = PERIOD_MAP.get(period, "day")
        params = {"symbol": tdx_code, "period": period_str, "limit": limit}
        cached = self.cache.get("tdx_klines", params)
        if cached:
            return [self._dict_to_bar(d) for d in cached]

        try:
            client = _get_client()
            if period == BarPeriod.DAILY and limit <= 800:
                resp = client.get_adjusted_kline(period_str, tdx_code, adjust="qfq", start=0, count=limit)
            else:
                resp = client.get_kline(period_str, tdx_code, start=0, count=min(limit, 800))
        except Exception as e:
            logger.warning("TDX klines failed %s: %s", tdx_code, e)
            return []

        plain = to_plain_symbol(tdx_code)
        bars: List[KlineBar] = []
        for item in resp.items or []:
            ts = item.time
            if ts.tzinfo:
                ts = ts.replace(tzinfo=None)
            if start and ts < start:
                continue
            if end and ts > end:
                continue
            bars.append(
                KlineBar(
                    symbol=plain,
                    timestamp=ts,
                    open=float(item.open_price),
                    high=float(item.high_price),
                    low=float(item.low_price),
                    close=float(item.close_price),
                    volume=float(item.volume),
                    period=period,
                )
            )
        bars.sort(key=lambda b: b.timestamp)
        if len(bars) > limit:
            bars = bars[-limit:]
        self.cache.set("tdx_klines", params, [b.to_dict() for b in bars])
        return bars

    def fetch_realtime_bar(self, symbol: str, period: BarPeriod) -> Optional[KlineBar]:
        quote = self.fetch_quote(symbol)
        if quote:
            return KlineBar(
                symbol=to_plain_symbol(normalize_tdx_code(symbol)),
                timestamp=datetime.now(),
                open=quote["open"],
                high=quote["high"],
                low=quote["low"],
                close=quote["price"],
                volume=quote.get("volume", 0),
                period=period,
            )
        bars = self.fetch_klines(symbol, period, limit=1)
        return bars[-1] if bars else None

    def fetch_quote(self, symbol: str) -> Optional[dict]:
        tdx_code = normalize_tdx_code(symbol)
        try:
            client = _get_client()
            quotes = client.get_quote(tdx_code)
            if not quotes:
                return None
            q = quotes[0]
            prev = q.last_close_price or q.last_price
            change_pct = ((q.last_price - prev) / prev * 100) if prev else 0.0
            return {
                "symbol": to_plain_symbol(tdx_code),
                "name": q.code,
                "price": q.last_price,
                "open": q.open_price,
                "high": q.high_price,
                "low": q.low_price,
                "volume": float(q.total_hand),
                "amount": q.amount,
                "change_pct": round(change_pct, 2),
            }
        except Exception as e:
            logger.warning("TDX quote failed %s: %s", tdx_code, e)
            return None

    def fetch_market_overview(self) -> dict:
        overview = {
            "index_sh": None,
            "breadth_up": None,
            "breadth_down": None,
            "north_flow": None,
            "source": "tdx",
        }
        try:
            client = _get_client()
            quotes = client.get_quote("sh000001")
            if quotes:
                q = quotes[0]
                prev = q.last_close_price or q.last_price
                chg = ((q.last_price - prev) / prev * 100) if prev else 0.0
                overview["index_sh"] = {
                    "name": "上证指数",
                    "price": round(q.last_price, 2),
                    "change_pct": round(chg, 2),
                }
        except Exception as e:
            logger.warning("TDX index overview failed: %s", e)
        return overview

    def fetch_stock_list(self, limit: int = 100) -> List[dict]:
        """从通达信拉取 A 股列表（分页，避免全量扫描过慢）."""
        try:
            client = _get_client()
            stocks: List[dict] = []
            per_exchange = max(limit // 2, 30)
            for exchange in ("sh", "sz"):
                page = client.get_codes(exchange, start=0, limit=per_exchange)
                for item in page.items or []:
                    fc = item.full_code
                    if not fc or "ST" in (item.name or ""):
                        continue
                    code = to_plain_symbol(fc)
                    if code.startswith("688"):
                        continue
                    prev = item.last_price or 0
                    stocks.append(
                        {
                            "code": code,
                            "name": item.name or code,
                            "price": prev,
                            "change_pct": 0.0,
                        }
                    )
                    if len(stocks) >= limit:
                        break
                if len(stocks) >= limit:
                    break
            return stocks[:limit]
        except Exception as e:
            logger.warning("TDX stock list failed: %s", e)
            return []

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

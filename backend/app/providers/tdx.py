from __future__ import annotations

import threading
from typing import Any

from app.config import settings
from app.providers.base import MarketProvider, normalize_code, to_tdx_code


class TdxProvider(MarketProvider):
    name = "tdx"
    display_name = "通达信 (eltdx TCP)"

    def __init__(self) -> None:
        self._client = None
        self._lock = threading.Lock()

    def _get_client(self):
        from eltdx import TdxClient

        with self._lock:
            if self._client is not None:
                return self._client
            kwargs: dict[str, Any] = {
                "timeout": settings.tdx_timeout,
                "probe_hosts": settings.tdx_probe,
                "server_count": 1,
                "connections_per_server": 1,
            }
            if settings.tdx_host and not settings.tdx_probe:
                kwargs["host"] = settings.tdx_host
            self._client = TdxClient(**kwargs)
            self._client.__enter__()
            return self._client

    def close(self) -> None:
        with self._lock:
            if self._client is not None:
                try:
                    self._client.__exit__(None, None, None)
                except Exception:
                    pass
                self._client = None

    def health(self) -> dict[str, Any]:
        try:
            c = self._get_client()
            q = c.helpers.full_quotes("sz000001")
            return {
                "ok": bool(q),
                "provider": self.name,
                "detail": f"quotes={len(q) if q else 0}",
                "host": settings.tdx_host,
            }
        except Exception as e:
            return {"ok": False, "provider": self.name, "detail": str(e)}

    def limit_up_pool(self, trade_date: str) -> list[dict[str, Any]]:
        raise NotImplementedError("TDX pool delegated to eastmoney")

    def _quote_obj(self, code: str):
        c = self._get_client()
        qs = c.helpers.full_quotes(to_tdx_code(code))
        if not qs:
            raise RuntimeError(f"no quote for {code}")
        return qs[0]

    def quote(self, code: str) -> dict[str, Any]:
        q = self._quote_obj(code)
        m, pure = normalize_code(code)
        pre = float(q.pre_close_price or 0)
        last = float(q.last_price or 0)
        chg = float(getattr(q, "change_pct", 0) or 0)
        if not chg and pre:
            chg = (last - pre) / pre * 100
        return {
            "code": pure,
            "market": m,
            "name": "",
            "price": last,
            "pre_close": pre,
            "open": float(q.open_price or 0),
            "high": float(q.high_price or 0),
            "low": float(q.low_price or 0),
            "change_pct": round(chg, 2),
            "amount": float(q.amount or 0),
            "volume": float(q.total_hand or 0),
            "source": self.name,
        }

    def depth(self, code: str) -> dict[str, Any]:
        q = self._quote_obj(code)
        buys = [{"price": float(x.price), "volume": float(x.volume)} for x in (q.buy_levels or [])]
        sells = [{"price": float(x.price), "volume": float(x.volume)} for x in (q.sell_levels or [])]
        m, pure = normalize_code(code)
        return {"code": pure, "market": m, "bids": buys, "asks": sells, "source": self.name}

    def daily_bars(self, code: str, count: int = 120) -> list[dict[str, Any]]:
        c = self._get_client()
        series = c.bars.get(to_tdx_code(code), period="day", count=count)
        return [
            {
                "date": b.time.strftime("%Y-%m-%d") if b.time else "",
                "open": float(b.open),
                "high": float(b.high),
                "low": float(b.low),
                "close": float(b.close),
                "volume": float(getattr(b, "volume_lots", 0) or 0),
                "amount": float(getattr(b, "amount", 0) or 0),
            }
            for b in series.bars
        ]

    def minute_bars(self, code: str, period: str = "1m") -> list[dict[str, Any]]:
        pts = self.intraday(code)
        step = 5 if str(period).startswith("5") else 1
        if step == 1:
            return [
                {
                    "time": x["time"],
                    "open": x["price"],
                    "high": x["price"],
                    "low": x["price"],
                    "close": x["price"],
                    "volume": x["volume"],
                }
                for x in pts
            ]
        out: list[dict[str, Any]] = []
        bucket: list[dict[str, Any]] = []
        for i, p in enumerate(pts):
            bucket.append(p)
            if len(bucket) == step or i == len(pts) - 1:
                prices = [float(x["price"]) for x in bucket]
                out.append(
                    {
                        "time": bucket[-1]["time"],
                        "open": prices[0],
                        "high": max(prices),
                        "low": min(prices),
                        "close": prices[-1],
                        "volume": sum(float(x["volume"]) for x in bucket),
                    }
                )
                bucket = []
        return out

    def intraday(self, code: str) -> list[dict[str, Any]]:
        c = self._get_client()
        series = c.minutes.today(to_tdx_code(code))
        points = getattr(series, "points", ()) or ()
        return [
            {
                "time": getattr(p, "time_label", None) or "",
                "price": float(p.price),
                "avg_price": float(getattr(p, "avg_price", 0) or 0),
                "volume": float(getattr(p, "volume", 0) or 0),
            }
            for p in points
        ]
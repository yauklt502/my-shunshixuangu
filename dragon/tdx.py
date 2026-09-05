"""通达信 7709 行情：日K、1m/5m、当日分时、五档盘口。

数据层是 eltdx（eltdx-mcp / tdx-mcp 同一套 7709 协议）。
主站默认 115.238.90.165:7709。
"""

from __future__ import annotations

import threading
from datetime import date, datetime
from typing import Any

from dragon.config import TDX_HOST

PERIODS = ("1m", "5m", "day")


def to_tdx_code(code: str) -> str:
    raw = (code or "").strip().lower()
    if raw.startswith(("sh", "sz", "bj")) and len(raw) >= 8:
        return raw
    digits = "".join(ch for ch in raw if ch.isdigit()).zfill(6)
    if digits.startswith(("5", "6", "9")):
        return "sh" + digits
    if digits.startswith(("4", "8")):
        return "bj" + digits
    return "sz" + digits


def ymd(value: str | None) -> str | None:
    if not value:
        return None
    s = "".join(ch for ch in str(value) if ch.isdigit())
    if len(s) == 8:
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    if len(str(value)) >= 10 and str(value)[4] == "-":
        return str(value)[:10]
    return None


def _iso(ts: datetime | date | None) -> str:
    if ts is None:
        return ""
    if isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%d %H:%M")
    return ts.isoformat()


def _levels(rows) -> list[dict[str, float | int]]:
    out = []
    for lv in rows or []:
        out.append({"price": float(lv.price), "volume": int(lv.volume)})
    return out


def pack_bar(bar) -> dict[str, Any]:
    return {
        "time": _iso(getattr(bar, "time", None)),
        "open": float(bar.open),
        "high": float(bar.high),
        "low": float(bar.low),
        "close": float(bar.close),
        "volume": float(getattr(bar, "volume_lots", 0) or getattr(bar, "volume_raw", 0) or 0),
        "amount": float(getattr(bar, "amount", 0) or 0),
    }


def pack_minute(series) -> dict[str, Any]:
    points = []
    for p in getattr(series, "points", ()) or ():
        points.append(
            {
                "time": p.time_label or _iso(p.time),
                "price": float(p.price),
                "avg": float(p.avg_price) if p.avg_price is not None else None,
                "volume": int(p.volume or 0),
            }
        )
    td = getattr(series, "trading_date", None)
    return {
        "date": td.isoformat() if td else None,
        "prev_close": float(series.prev_close) if getattr(series, "prev_close", None) else None,
        "open": float(series.open_price) if getattr(series, "open_price", None) else None,
        "points": points,
    }


def pack_quote(rec) -> dict[str, Any]:
    last = float(getattr(rec, "last_price", 0) or 0)
    prev = float(getattr(rec, "last_close_price", 0) or getattr(rec, "pre_close_price", 0) or 0)
    chg = last - prev if prev else 0.0
    pct = (chg / prev * 100.0) if prev else None
    return {
        "code": getattr(rec, "code", ""),
        "last": last,
        "prev_close": prev,
        "open": float(getattr(rec, "open_price", 0) or 0),
        "high": float(getattr(rec, "high_price", 0) or 0),
        "low": float(getattr(rec, "low_price", 0) or 0),
        "change": round(chg, 4),
        "change_pct": round(pct, 2) if pct is not None else None,
        "amount": float(getattr(rec, "amount", 0) or 0),
        "volume": int(getattr(rec, "total_hand", 0) or 0),
        "bids": _levels(getattr(rec, "buy_levels", ())),
        "asks": _levels(getattr(rec, "sell_levels", ())),
    }


class TdxFeed:
    def __init__(self, host: str = TDX_HOST):
        self.host = host
        self._client = None
        self._lock = threading.Lock()

    def _open(self):
        from eltdx import TdxClient

        if self._client is not None:
            return self._client
        client = TdxClient(host=self.host, timeout=8, probe_hosts=False)
        client.__enter__()
        self._client = client
        return client

    def _reset(self) -> None:
        client = self._client
        self._client = None
        if client is None:
            return
        try:
            client.__exit__(None, None, None)
        except Exception:
            pass

    def call(self, fn):
        with self._lock:
            try:
                return fn(self._open())
            except Exception:
                self._reset()
                return fn(self._open())

    def ping(self) -> dict[str, Any]:
        def _fn(c):
            c.bars.get("sh000001", period="day", count=1, kind="index")
            return True

        try:
            self.call(_fn)
            return {"ok": True, "host": self.host}
        except Exception as exc:
            return {"ok": False, "host": self.host, "error": str(exc)}

    def kline(self, code: str, period: str = "day", count: int = 180) -> dict[str, Any]:
        if period not in PERIODS:
            raise ValueError(f"period 只能是 {PERIODS}")
        full = to_tdx_code(code)
        count = max(1, min(int(count), 800))

        def _fn(c):
            return c.bars.get(full, period=period, count=count)

        series = self.call(_fn)
        return {
            "ok": True,
            "code": series.code,
            "tdx_code": series.full_code,
            "period": series.period_name,
            "bars": [pack_bar(b) for b in series.bars],
        }

    def minute(self, code: str, trade_date: str | None = None) -> dict[str, Any]:
        full = to_tdx_code(code)
        day = ymd(trade_date)

        def _fn(c):
            if day:
                return c.minutes.history(full, day)
            return c.minutes.today(full)

        series = self.call(_fn)
        packed = pack_minute(series)
        packed.update({"ok": True, "code": series.code, "tdx_code": series.full_code})
        return packed

    def depth(self, code: str) -> dict[str, Any]:
        full = to_tdx_code(code)

        def _fn(c):
            page = c.quotes.get_depth(full)
            recs = getattr(page, "records", ()) or ()
            if recs:
                return recs[0]
            snaps = c.quotes.get_snapshots(full)
            return snaps[0] if snaps else None

        rec = self.call(_fn)
        if rec is None:
            return {"ok": False, "error": "没有盘口"}
        out = pack_quote(rec)
        out["ok"] = True
        out["tdx_code"] = getattr(rec, "full_code", full)
        return out

    def bundle(self, code: str, trade_date: str | None = None) -> dict[str, Any]:
        full = to_tdx_code(code)
        day = ymd(trade_date)

        def _fn(c):
            kline = c.bars.get(full, period="day", count=180)
            try:
                minute = c.minutes.history(full, day) if day else c.minutes.today(full)
            except Exception:
                minute = c.minutes.today(full)
            rec = None
            page = c.quotes.get_depth(full)
            recs = getattr(page, "records", ()) or ()
            if recs:
                rec = recs[0]
            else:
                snaps = c.quotes.get_snapshots(full)
                rec = snaps[0] if snaps else None
            return kline, minute, rec

        kline, minute, rec = self.call(_fn)
        quote = pack_quote(rec) if rec else None
        return {
            "ok": True,
            "host": self.host,
            "source": "tdx-7709 / eltdx",
            "code": kline.code,
            "tdx_code": kline.full_code,
            "quote": quote,
            "kline": {"period": "day", "bars": [pack_bar(b) for b in kline.bars]},
            "minute": pack_minute(minute),
        }


FEED = TdxFeed()

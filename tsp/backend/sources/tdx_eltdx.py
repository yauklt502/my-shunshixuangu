"""通达信 eltdx TCP：五档、1m/5m、日K、分时。"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from backend.config import TDX_HOST, TDX_TIMEOUT
from backend.sources import eastmoney as em

_lock = threading.Lock()
_client = None


def tdx_symbol(code: str) -> str:
    c = em.plain(code)
    if c.startswith(("6", "9")):
        return f"sh{c}"
    if c.startswith(("4", "8")):
        return f"bj{c}"
    return f"sz{c}"


def get_client():
    global _client
    with _lock:
        if _client is None:
            from eltdx import TdxClient

            host = TDX_HOST
            if ":" not in host:
                host = f"{host}:7709"
            _client = TdxClient(host=host, timeout=TDX_TIMEOUT)
        return _client


def _sync_health() -> dict[str, Any]:
    try:
        c = get_client()
        snaps = c.quotes.get_snapshots([tdx_symbol("000001")])
        ok = bool(snaps and float(getattr(snaps[0], "last_price", 0) or 0) > 0)
        return {
            "ok": ok,
            "name": "通达信(eltdx)",
            "detail": f"{TDX_HOST} {'连通' if ok else '无报价'}",
            "host": TDX_HOST,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "name": "通达信(eltdx)", "detail": str(exc), "host": TDX_HOST}


async def health() -> dict[str, Any]:
    return await asyncio.to_thread(_sync_health)


def _sync_depth(code: str) -> dict[str, Any]:
    c = get_client()
    page = c.quotes.get_depth([tdx_symbol(code)])
    rec = page.records[0] if page and getattr(page, "records", None) else None
    if not rec:
        return {"code": em.plain(code), "bids": [], "asks": []}
    return {
        "code": em.plain(code),
        "price": float(rec.last_price or 0),
        "pre_close": float(rec.last_close_price or 0),
        "open": float(rec.open_price or 0),
        "high": float(rec.high_price or 0),
        "low": float(rec.low_price or 0),
        "amount": float(rec.amount or 0),
        "volume": float(rec.total_hand or 0),
        "bids": [{"price": float(x.price), "volume": float(x.volume)} for x in (rec.buy_levels or ())],
        "asks": [{"price": float(x.price), "volume": float(x.volume)} for x in (rec.sell_levels or ())],
        "source": "tdx",
    }


async def depth(code: str) -> dict[str, Any]:
    return await asyncio.to_thread(_sync_depth, code)


def _sync_kline(code: str, period: str, count: int) -> list[dict[str, Any]]:
    c = get_client()
    period_map = {"day": "day", "1min": "1min", "5min": "5min", "1m": "1min", "5m": "5min"}
    p = period_map.get(period, period)
    series = c.bars.get(tdx_symbol(code), period=p, count=count, adjust="qfq")
    out: list[dict[str, Any]] = []
    for bar in series.bars or []:
        t = bar.time
        if hasattr(t, "strftime"):
            time_s = t.strftime("%Y-%m-%d") if p == "day" else t.strftime("%Y-%m-%d %H:%M")
        else:
            time_s = str(t)
        out.append(
            {
                "time": time_s,
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": float(getattr(bar, "volume_lots", None) or getattr(bar, "volume_hand", 0) or 0),
                "amount": float(bar.amount or 0),
            }
        )
    return out


async def kline(code: str, period: str = "day", count: int = 120) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_sync_kline, code, period, count)


async def kline_day(code: str, count: int = 120) -> list[dict[str, Any]]:
    return await kline(code, "day", count)


def _sync_minute(code: str) -> dict[str, Any]:
    c = get_client()
    series = c.minutes.today(tdx_symbol(code))
    points = [
        {
            "time": getattr(p, "time_label", None) or getattr(p, "time_str", ""),
            "price": float(p.price or 0),
            "avg": float(p.avg_price or 0),
            "volume": float(p.volume or 0),
        }
        for p in (series.points or [])
    ]
    pre = float(getattr(series, "prev_close", 0) or 0)
    if not pre and points:
        pre = points[0]["price"]
    return {
        "code": em.plain(code),
        "name": "",
        "pre_close": pre,
        "points": points,
        "source": "tdx",
    }


async def minute_today(code: str) -> dict[str, Any]:
    return await asyncio.to_thread(_sync_minute, code)


async def quotes(codes: list[str]) -> dict[str, dict[str, Any]]:
    def _sync() -> dict[str, dict[str, Any]]:
        c = get_client()
        out: dict[str, dict[str, Any]] = {}
        mapped = [tdx_symbol(x) for x in codes]
        for i in range(0, len(mapped), 40):
            try:
                snaps = c.quotes.get_snapshots(mapped[i : i + 40])
            except Exception:  # noqa: BLE001
                continue
            for s in snaps or []:
                code = em.plain(getattr(s, "code", ""))
                price = float(getattr(s, "last_price", 0) or 0)
                pre = float(getattr(s, "pre_close_price", 0) or getattr(s, "pre_close", 0) or 0)
                out[code] = {
                    "code": code,
                    "name": "",
                    "price": price,
                    "change_pct": ((price / pre) - 1) * 100 if pre else 0.0,
                    "open": float(getattr(s, "open_price", 0) or 0),
                    "high": float(getattr(s, "high_price", 0) or 0),
                    "low": float(getattr(s, "low_price", 0) or 0),
                    "pre_close": pre,
                    "turnover": 0.0,
                }
        return out

    return await asyncio.to_thread(_sync)


async def market_bundle(date: str) -> dict[str, Any]:
    base = await em.market_bundle(date)
    codes = [x["code"] for x in (base.get("limit_up") or []) if x.get("code")]
    codes += [x["code"] for x in (base.get("broken") or []) if x.get("code")]
    q = await quotes(list(dict.fromkeys(codes))[:80])
    for row in base.get("limit_up") or []:
        qq = q.get(row["code"])
        if qq and qq.get("price"):
            row["price"] = qq["price"]
            row["change_pct"] = qq["change_pct"]
    base["source"] = "tdx"
    base["tdx_host"] = TDX_HOST
    return base


async def board_members(board_code: str, limit: int = 60) -> list[dict[str, Any]]:
    members = await em.board_members(board_code, limit)
    q = await quotes([m["code"] for m in members])
    for m in members:
        qq = q.get(m["code"])
        if qq and qq.get("price"):
            m["price"] = qq["price"]
            m["change_pct"] = qq["change_pct"]
    return members
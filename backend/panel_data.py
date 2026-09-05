"""个股浮窗：日K / 分时 / 1m·5m / 五档 — 指定通达信 eltdx TCP。"""
from __future__ import annotations

import os
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

CN_TZ = timezone(timedelta(hours=8))
# TSP 实测主站
TDX_HOST = os.environ.get("TDX_HOST", "115.238.90.165:7709")
TDX_TIMEOUT = float(os.environ.get("TDX_TIMEOUT", "8"))

_lock = threading.Lock()
_client = None
_client_err: Exception | None = None


def plain(code: str) -> str:
    return re.sub(r"\D", "", str(code)).zfill(6)[-6:]


def tdx_symbol(code: str) -> str:
    c = plain(code)
    if c.startswith(("6", "9")):
        return f"sh{c}"
    if c.startswith(("4", "8")):
        return f"bj{c}"
    return f"sz{c}"


def get_client():
    """懒加载 eltdx TdxClient，失败抛错（浮窗不静默回退）。"""
    global _client, _client_err
    with _lock:
        if _client is not None:
            return _client
        try:
            from eltdx import TdxClient  # type: ignore

            host = TDX_HOST
            if ":" not in host:
                host = f"{host}:7709"
            _client = TdxClient(host=host, timeout=TDX_TIMEOUT)
            # 轻量连通探测
            snaps = _client.quotes.get_snapshots([tdx_symbol("000001")])
            if not snaps:
                raise RuntimeError("通达信无快照返回")
            _client_err = None
            return _client
        except Exception as exc:  # noqa: BLE001
            _client = None
            _client_err = exc
            raise RuntimeError(f"通达信 TCP 连接失败 ({TDX_HOST}): {exc}") from exc


def tdx_available() -> bool:
    try:
        get_client()
        return True
    except Exception:
        return False


def tdx_kline(code: str, period: str = "day", count: int = 120) -> list[dict]:
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
            }
        )
    return out


def tdx_minute(code: str) -> dict:
    c = get_client()
    series = c.minutes.today(tdx_symbol(code))
    points = []
    for p in getattr(series, "points", None) or []:
        points.append(
            {
                "time": getattr(p, "time_label", None) or getattr(p, "time_str", "") or str(getattr(p, "time", "")),
                "price": float(getattr(p, "price", 0) or 0),
                "avg": float(getattr(p, "avg_price", 0) or 0),
                "volume": float(getattr(p, "volume", 0) or 0),
            }
        )
    pre = float(getattr(series, "prev_close", 0) or getattr(series, "pre_close", 0) or 0)
    return {"code": plain(code), "pre_close": pre, "points": points, "source": "tdx"}


def tdx_depth(code: str) -> dict:
    c = get_client()
    page = c.quotes.get_depth([tdx_symbol(code)])
    rec = page.records[0] if page and getattr(page, "records", None) else None
    if not rec:
        # fallback snapshots
        snaps = c.quotes.get_snapshots([tdx_symbol(code)]) or []
        snap = snaps[0] if snaps else None
        if not snap:
            return {"code": plain(code), "asks": [], "bids": [], "price": 0, "pre_close": 0, "source": "tdx"}
        return {
            "code": plain(code),
            "price": float(getattr(snap, "last_price", 0) or 0),
            "pre_close": float(getattr(snap, "pre_close_price", 0) or getattr(snap, "pre_close", 0) or 0),
            "asks": [],
            "bids": [],
            "source": "tdx",
            "tdx_host": TDX_HOST,
        }
    return {
        "code": plain(code),
        "price": float(rec.last_price or 0),
        "pre_close": float(rec.last_close_price or 0),
        "asks": [{"price": float(x.price), "volume": float(x.volume)} for x in (rec.sell_levels or ())],
        "bids": [{"price": float(x.price), "volume": float(x.volume)} for x in (rec.buy_levels or ())],
        "source": "tdx",
        "tdx_host": TDX_HOST,
    }


def build_panel(code: str, source: str = "tdx") -> dict[str, Any]:
    """浮窗专用：强制通达信 TCP，不用东财冒充。"""
    code = plain(code)
    errors: list[str] = []
    out: dict[str, Any] = {
        "ok": True,
        "code": code,
        "source": "tdx",
        "tdx_host": TDX_HOST,
        "tdxConnected": False,
        "daySource": "tdx",
    }
    try:
        get_client()
        out["tdxConnected"] = True
    except Exception as exc:  # noqa: BLE001
        out["ok"] = False
        out["errors"] = [str(exc)]
        out["day"] = []
        out["minute"] = {"code": code, "points": [], "pre_close": 0}
        out["m1"], out["m5"] = [], []
        out["depth"] = {"code": code, "asks": [], "bids": [], "price": 0, "pre_close": 0}
        return out

    try:
        out["day"] = tdx_kline(code, "day", 120)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"day:{exc}")
        out["day"] = []

    try:
        out["minute"] = tdx_minute(code)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"minute:{exc}")
        out["minute"] = {"code": code, "points": [], "pre_close": 0}

    try:
        out["m1"] = tdx_kline(code, "1min", 240)
        out["m5"] = tdx_kline(code, "5min", 120)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"intra:{exc}")
        out["m1"], out["m5"] = [], []

    try:
        out["depth"] = tdx_depth(code)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"depth:{exc}")
        out["depth"] = {"code": code, "asks": [], "bids": [], "price": 0, "pre_close": 0}

    out["errors"] = errors
    return out


def recent_trade_dates(limit: int = 40) -> list[dict[str, str]]:
    out = []
    d = datetime.now(CN_TZ).date()
    while len(out) < limit:
        if d.weekday() < 5:
            out.append({"date": d.strftime("%Y%m%d"), "label": d.strftime("%Y-%m-%d %a")})
        d -= timedelta(days=1)
    return out

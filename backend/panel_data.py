"""个股浮窗数据：日K / 分时 / 1m·5m / 五档。优先通达信 TCP，失败回退东方财富。"""
from __future__ import annotations

import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any  # noqa: F401

import httpx

CN_TZ = timezone(timedelta(hours=8))
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
TDX_HOST = os.environ.get("TDX_HOST", "115.238.90.165:7709")
TDX_TIMEOUT = float(os.environ.get("TDX_TIMEOUT", "8"))


def plain(code: str) -> str:
    return re.sub(r"\D", "", str(code)).zfill(6)[-6:]


def secid(code: str) -> str:
    c = plain(code)
    return f"1.{c}" if c.startswith(("6", "9")) else f"0.{c}"


def fnum(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "" or v == "-":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=12,
        headers={"User-Agent": UA, "Referer": "https://quote.eastmoney.com/"},
        follow_redirects=True,
    )


def em_kline_day(code: str, count: int = 120) -> list[dict]:
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={secid(code)}&fields1=f1,f2,f3,f4,f5,f6"
        "&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&end=20500101"
        f"&lmt={count}"
    )
    with _client() as c:
        r = c.get(url)
        r.raise_for_status()
        rows = ((r.json().get("data") or {}).get("klines")) or []
    out = []
    for row in rows:
        p = str(row).split(",")
        if len(p) < 6:
            continue
        out.append(
            {
                "time": p[0],
                "open": fnum(p[1]),
                "close": fnum(p[2]),
                "high": fnum(p[3]),
                "low": fnum(p[4]),
                "volume": fnum(p[5]),
            }
        )
    return out


def em_kline_min(code: str, klt: int, count: int) -> list[dict]:
    """klt=1 → 1分钟, klt=5 → 5分钟."""
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={secid(code)}&fields1=f1,f2,f3,f4,f5,f6"
        f"&fields2=f51,f52,f53,f54,f55,f56,f57&klt={klt}&fqt=1&end=20500101"
        f"&lmt={count}"
    )
    with _client() as c:
        r = c.get(url)
        r.raise_for_status()
        rows = ((r.json().get("data") or {}).get("klines")) or []
    out = []
    for row in rows:
        p = str(row).split(",")
        if len(p) < 6:
            continue
        out.append(
            {
                "time": p[0],
                "open": fnum(p[1]),
                "close": fnum(p[2]),
                "high": fnum(p[3]),
                "low": fnum(p[4]),
                "volume": fnum(p[5]),
            }
        )
    return out


def em_minute_today(code: str) -> dict:
    url = (
        "https://push2.eastmoney.com/api/qt/stock/trends2/get"
        f"?secid={secid(code)}"
        "&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13"
        "&fields2=f51,f52,f53,f54,f55,f56,f57,f58&iscr=0&ndays=1"
    )
    with _client() as c:
        r = c.get(url)
        r.raise_for_status()
        data = r.json().get("data") or {}
    points = []
    for row in data.get("trends") or []:
        p = str(row).split(",")
        if len(p) < 5:
            continue
        points.append(
            {
                "time": p[0][-5:] if " " in p[0] else p[0],
                "price": fnum(p[1]),
                "avg": fnum(p[2]),
                "volume": fnum(p[5]) if len(p) > 5 else fnum(p[3]),
            }
        )
    return {
        "code": plain(code),
        "pre_close": fnum(data.get("preClose") or data.get("prePrice")),
        "points": points,
        "source": "eastmoney",
    }


def em_depth(code: str) -> dict:
    url = (
        "https://push2.eastmoney.com/api/qt/stock/get"
        f"?secid={secid(code)}&fields=f43,f57,f58,f60,f169,f170,"
        "f19,f20,f17,f18,f15,f16,f13,f14,f11,f12,"
        "f39,f40,f37,f38,f35,f36,f33,f34,f31,f32"
        f"&ut=fa5fd1943c7b386f172d6893dbfba10b&_={int(time.time()*1000)}"
    )
    with _client() as c:
        r = c.get(url)
        r.raise_for_status()
        d = (r.json().get("data") or {})
    # prices often *100 on this endpoint when fltt not set — detect
    def px(v):
        n = fnum(v)
        return n / 100 if n > 1000 else n

    asks = []
    bids = []
    ask_pairs = [(d.get("f39"), d.get("f40")), (d.get("f37"), d.get("f38")), (d.get("f35"), d.get("f36")), (d.get("f33"), d.get("f34")), (d.get("f31"), d.get("f32"))]
    bid_pairs = [(d.get("f19"), d.get("f20")), (d.get("f17"), d.get("f18")), (d.get("f15"), d.get("f16")), (d.get("f13"), d.get("f14")), (d.get("f11"), d.get("f12"))]
    for price, vol in ask_pairs:
        if price:
            asks.append({"price": px(price), "volume": fnum(vol)})
    for price, vol in bid_pairs:
        if price:
            bids.append({"price": px(price), "volume": fnum(vol)})
    return {
        "code": plain(code),
        "name": str(d.get("f58") or ""),
        "price": px(d.get("f43")),
        "pre_close": px(d.get("f60")),
        "asks": asks,
        "bids": bids,
        "source": "eastmoney",
    }


# ---------- optional 通达信 eltdx ----------
_tdx = None
_tdx_err = None


def tdx_available() -> bool:
    global _tdx, _tdx_err
    if _tdx is not None:
        return True
    if _tdx_err is not None and "import" in str(_tdx_err).lower():
        return False
    try:
        from eltdx import TdxClient  # type: ignore

        host = TDX_HOST
        if ":" in host:
            h, p = host.rsplit(":", 1)
            client = TdxClient(host=h, port=int(p), timeout=TDX_TIMEOUT)
        else:
            client = TdxClient(host=host, timeout=TDX_TIMEOUT)
        # light ping via quotes
        client.quotes.get_snapshots(["sh000001"])
        _tdx = client
        return True
    except Exception as exc:  # noqa: BLE001
        _tdx_err = exc
        return False


def tdx_symbol(code: str) -> str:
    c = plain(code)
    return f"sh{c}" if c.startswith(("6", "9")) else f"sz{c}"


def tdx_kline(code: str, period: str = "day", count: int = 120) -> list[dict]:
    if not tdx_available():
        raise RuntimeError(f"tdx unavailable: {_tdx_err}")
    bars = _tdx.bars.get(tdx_symbol(code), period=period, count=count)  # type: ignore[union-attr]
    out = []
    for bar in bars or []:
        ts = getattr(bar, "time", None) or getattr(bar, "datetime", None) or ""
        time_s = str(ts)
        out.append(
            {
                "time": time_s,
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": float(getattr(bar, "volume", 0) or 0),
            }
        )
    return out


def tdx_minute(code: str) -> dict:
    if not tdx_available():
        raise RuntimeError(f"tdx unavailable: {_tdx_err}")
    series = _tdx.minutes.today(tdx_symbol(code))  # type: ignore[union-attr]
    points = [
        {
            "time": getattr(p, "time_label", None) or getattr(p, "time_str", "") or "",
            "price": float(p.price or 0),
            "avg": float(getattr(p, "avg_price", 0) or 0),
            "volume": float(getattr(p, "volume", 0) or 0),
        }
        for p in (getattr(series, "points", None) or [])
    ]
    pre = float(getattr(series, "prev_close", 0) or 0)
    return {"code": plain(code), "pre_close": pre, "points": points, "source": "tdx"}


def tdx_depth(code: str) -> dict:
    if not tdx_available():
        raise RuntimeError(f"tdx unavailable: {_tdx_err}")
    snap = (_tdx.quotes.get_snapshots([tdx_symbol(code)]) or [None])[0]  # type: ignore[union-attr]
    if not snap:
        raise RuntimeError("tdx depth empty")
    asks, bids = [], []
    for i in range(1, 6):
        ap = getattr(snap, f"ask_price_{i}", None) or getattr(snap, f"ask{i}", None)
        av = getattr(snap, f"ask_vol_{i}", None) or getattr(snap, f"ask_volume_{i}", None)
        bp = getattr(snap, f"bid_price_{i}", None) or getattr(snap, f"bid{i}", None)
        bv = getattr(snap, f"bid_vol_{i}", None) or getattr(snap, f"bid_volume_{i}", None)
        if ap:
            asks.append({"price": float(ap), "volume": float(av or 0)})
        if bp:
            bids.append({"price": float(bp), "volume": float(bv or 0)})
    return {
        "code": plain(code),
        "price": float(getattr(snap, "last_price", 0) or 0),
        "pre_close": float(getattr(snap, "pre_close_price", 0) or getattr(snap, "pre_close", 0) or 0),
        "asks": asks,
        "bids": bids,
        "source": "tdx",
        "tdx_host": TDX_HOST,
    }


def build_panel(code: str, source: str = "tdx") -> dict[str, Any]:
    code = plain(code)
    prefer_tdx = source in {"tdx", "tongdaxin", "tongdaxin_tcp"}
    errors: list[str] = []
    out: dict[str, Any] = {"ok": True, "code": code, "source": source, "tdx_host": TDX_HOST}

    # day
    try:
        if prefer_tdx and tdx_available():
            out["day"] = tdx_kline(code, "day", 120)
            out["daySource"] = "tdx"
        else:
            out["day"] = em_kline_day(code, 120)
            out["daySource"] = "eastmoney"
    except Exception as exc:  # noqa: BLE001
        errors.append(f"day:{exc}")
        try:
            out["day"] = em_kline_day(code, 120)
            out["daySource"] = "eastmoney"
        except Exception as exc2:  # noqa: BLE001
            errors.append(f"day_fallback:{exc2}")
            out["day"] = []

    # minute
    try:
        if prefer_tdx and tdx_available():
            out["minute"] = tdx_minute(code)
        else:
            out["minute"] = em_minute_today(code)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"minute:{exc}")
        try:
            out["minute"] = em_minute_today(code)
        except Exception as exc2:  # noqa: BLE001
            errors.append(f"minute_fallback:{exc2}")
            out["minute"] = {"code": code, "points": [], "pre_close": 0}

    # 1m / 5m
    try:
        if prefer_tdx and tdx_available():
            out["m1"] = tdx_kline(code, "1min", 240)
            out["m5"] = tdx_kline(code, "5min", 120)
            out["intraSource"] = "tdx"
        else:
            out["m1"] = em_kline_min(code, 1, 240)
            out["m5"] = em_kline_min(code, 5, 120)
            out["intraSource"] = "eastmoney"
    except Exception as exc:  # noqa: BLE001
        errors.append(f"intra:{exc}")
        try:
            out["m1"] = em_kline_min(code, 1, 240)
            out["m5"] = em_kline_min(code, 5, 120)
            out["intraSource"] = "eastmoney"
        except Exception as exc2:  # noqa: BLE001
            errors.append(f"intra_fallback:{exc2}")
            out["m1"], out["m5"] = [], []

    # depth
    try:
        if prefer_tdx and tdx_available():
            out["depth"] = tdx_depth(code)
        else:
            out["depth"] = em_depth(code)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"depth:{exc}")
        try:
            out["depth"] = em_depth(code)
        except Exception as exc2:  # noqa: BLE001
            errors.append(f"depth_fallback:{exc2}")
            out["depth"] = {"code": code, "asks": [], "bids": [], "price": 0, "pre_close": 0}

    out["errors"] = errors
    out["tdxConnected"] = tdx_available()
    return out


def recent_trade_dates(limit: int = 40) -> list[dict[str, str]]:
    """简易交易日列表（跳过周末；复盘用）。"""
    out = []
    d = datetime.now(CN_TZ).date()
    while len(out) < limit:
        if d.weekday() < 5:
            s = d.strftime("%Y%m%d")
            out.append({"date": s, "label": d.strftime("%Y-%m-%d %a")})
        d -= timedelta(days=1)
    return out


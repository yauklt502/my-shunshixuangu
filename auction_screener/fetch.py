"""东方财富：昨涨停池 + 分时 09:30 竞价 + 流通A股。"""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

CST = timezone(timedelta(hours=8))
CTX = ssl.create_default_context()
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
ZT_URL = (
    "https://push2ex.eastmoney.com/getTopicZTPool"
    "?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
    "&Pageindex=0&pagesize=200&sort=lbc:desc&date={date}"
)
SNAP_URL = (
    "https://push2.eastmoney.com/api/qt/stock/get"
    "?secid={secid}&ut=fa5fd1943c7b386f172d6893dbfba10b"
    "&fields=f57,f58,f60,f84,f85"
)
TREND_HOSTS = (
    "push2his.eastmoney.com",
    "82.push2his.eastmoney.com",
    "99.push2his.eastmoney.com",
)
TREND_PATH = (
    "/api/qt/stock/trends2/get?fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13"
    "&fields2=f51,f52,f53,f54,f55,f56,f57,f58"
    "&ut=fa5fd1943c7b386f172d6893dbfba10b&ndays={ndays}&iscr=0&secid={secid}"
)


def http_json(url: str, *, retries: int = 3, referer: str = "https://quote.eastmoney.com/") -> Any:
    last: Exception | None = None
    delay = 0.25
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer})
            with urllib.request.urlopen(req, timeout=12, context=CTX) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last = exc
            time.sleep(delay)
            delay = min(delay * 2, 2.0)
    raise RuntimeError(f"request failed: {url}") from last


def yyyymmdd(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")


def secid(code: str) -> str:
    code = code.split(".")[0]
    return ("1." if code.startswith(("6", "9")) else "0.") + code


def latest_zt_date(now: datetime | None = None) -> tuple[str, list[dict[str, Any]]]:
    now = now or datetime.now(CST)
    last_err: Exception | None = None
    for i in range(1, 12):
        day = yyyymmdd(now - timedelta(days=i))
        try:
            data = http_json(ZT_URL.format(date=day))
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            continue
        pool = (data.get("data") or {}).get("pool") or []
        if pool:
            return day, pool
    raise RuntimeError(f"no zt pool in last 11 days: {last_err}")


def parse_trend_bar(bar: str) -> dict[str, float]:
    parts = bar.split(",")
    open_px = float(parts[1] or 0)
    close_px = float(parts[2] or 0)
    px = open_px if open_px > 0 else close_px
    return {
        "px": px,
        "vol_lots": float(parts[5] or 0),
        "amt": float(parts[6] or 0),
    }


def fetch_trends(code: str, ndays: int = 5) -> dict[str, Any]:
    sid = secid(code)
    last: Exception | None = None
    for host in TREND_HOSTS:
        try:
            data = http_json("https://" + host + TREND_PATH.format(ndays=ndays, secid=sid))
            payload = data.get("data") or {}
            trends = payload.get("trends") or []
            if trends:
                return payload
        except Exception as exc:  # noqa: BLE001
            last = exc
            continue
    raise RuntimeError(f"trends failed {code}: {last}")


def auction_from_trends(payload: dict[str, Any]) -> dict[str, Any] | None:
    trends = payload.get("trends") or []
    first: dict[str, str] = {}
    daily_lots: dict[str, float] = {}
    for bar in trends:
        day = bar.split(",")[0].split(" ")[0]
        parsed = parse_trend_bar(bar)
        if day not in first:
            first[day] = bar
        daily_lots[day] = daily_lots.get(day, 0.0) + parsed["vol_lots"]
    days = sorted(first)
    if len(days) < 2:
        return None
    today, yest = days[-1], days[-2]
    today_a = parse_trend_bar(first[today])
    yest_a = parse_trend_bar(first[yest])
    finished = [d for d in days if d != today]
    avg5 = 0.0
    if finished:
        avg5 = sum(daily_lots[d] for d in finished[-5:]) / min(5, len(finished))
    prev_close = float(payload.get("prePrice") or 0)
    return {
        "today": today,
        "yesterday": yest,
        "today_auction": today_a,
        "yest_auction": yest_a,
        "avg5_lots": avg5,
        "prev_close": prev_close,
    }


def fetch_free_float(code: str) -> float:
    """流通A股（股）。近似自由流通股。"""
    data = http_json(SNAP_URL.format(secid=secid(code)))
    payload = data.get("data") or {}
    return float(payload.get("f85") or 0)

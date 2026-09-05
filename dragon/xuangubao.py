"""选股宝涨停池：有近三个月首封时间、炸板、换手，适合回测。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from dragon.themes import plate_theme
from dragon.timeutil import CN

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
CACHE = Path(__file__).resolve().parent.parent / "data" / "xgb"


def _cache_path(pool: str, date: str) -> Path:
    return CACHE / f"{pool}_{date}.json"


async def fetch_pool(client: httpx.AsyncClient, pool: str, date: str, *, use_cache: bool = True) -> list[dict]:
    path = _cache_path(pool, date)
    if use_cache and path.exists():
        return json.loads(path.read_text("utf-8"))
    url = f"https://flash-api.xuangubao.cn/api/pool/detail?pool_name={pool}&date={date}"
    r = await client.get(
        url,
        headers={"User-Agent": UA, "Referer": "https://xuangubao.cn/", "Accept": "application/json"},
        timeout=20.0,
    )
    r.raise_for_status()
    payload = r.json()
    rows = payload.get("data") or []
    if not isinstance(rows, list):
        rows = []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False), "utf-8")
    return rows


def ts_to_fbt(ts: int | float | None) -> int:
    try:
        n = int(ts or 0)
    except (TypeError, ValueError):
        return 0
    if n <= 0:
        return 0
    dt = datetime.fromtimestamp(n, CN)
    return dt.hour * 10000 + dt.minute * 100 + dt.second


def code_of(symbol: str) -> str:
    return (symbol or "").split(".")[0].zfill(6)


def themes_of(item: dict) -> list[str]:
    plates = ((item.get("surge_reason") or {}).get("related_plates")) or []
    names = [plate_theme(p.get("plate_name")) for p in plates]
    names = [n for n in names if n and n not in {"其他", "ST股"}]
    return list(dict.fromkeys(names)) or ["其他"]


def normalize_xgb(item: dict) -> dict[str, Any] | None:
    name = str(item.get("stock_chi_name") or "")
    if "ST" in name.upper():
        return None
    if item.get("is_new_stock"):
        return None
    code = code_of(str(item.get("symbol") or ""))
    if not code.isdigit():
        return None
    hs = float(item.get("turnover_ratio") or 0.0) * 100.0
    circ = float(item.get("non_restricted_capital") or 0.0)
    amount = hs / 100.0 * circ if circ else 0.0
    themes = themes_of(item)
    theme = themes[0]
    return {
        "code": code,
        "name": name,
        "industry": theme,
        "theme": theme,
        "themes": themes,
        "price": float(item.get("price") or 0.0),
        "change_pct": float(item.get("change_percent") or 0.0) * 100.0,
        "amount": amount,
        "circ_mv": circ,
        "turnover": hs,
        "boards": int(item.get("limit_up_days") or 1),
        "first_seal": ts_to_fbt(item.get("first_limit_up")),
        "open_count": int(item.get("break_limit_up_times") or 0),
        "seal_fund": float(item.get("buy_lock_volume_ratio") or 0.0) * circ,
        "volume_ratio": float(item.get("volume_bias_ratio") or 0.0) or None,
        "sealed": True,
        "symbol": str(item.get("symbol") or ""),
    }


def next_day_map(rows: list[dict]) -> dict[str, dict]:
    """T+1 的 yesterday_limit_up：key=code，change_percent 是次日涨跌。"""
    out: dict[str, dict] = {}
    for item in rows:
        code = code_of(str(item.get("symbol") or ""))
        if not code.isdigit():
            continue
        chg = float(item.get("change_percent") or 0.0) * 100.0
        out[code] = {
            "next_pct": round(chg, 3),
            "next_price": float(item.get("price") or 0.0),
            "next_zt": bool(item.get("first_limit_up")) and chg >= 9.0,
            "next_boards": int(item.get("limit_up_days") or 0),
        }
    return out

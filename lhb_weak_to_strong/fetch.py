"""Data fetch layer — akshare public LHB APIs with local JSON cache."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "lhb_cache"


def _ensure_cache() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def _cache_path(name: str) -> Path:
    return _ensure_cache() / name


def _read_cache(name: str, max_age_hours: float | None = 12) -> Any | None:
    path = _cache_path(name)
    if not path.exists():
        return None
    if max_age_hours is not None:
        age_h = (time.time() - path.stat().st_mtime) / 3600
        if age_h > max_age_hours:
            return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_cache(name: str, payload: Any) -> None:
    path = _cache_path(name)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)


def normalize_date(trade_date: str) -> tuple[str, str]:
    """Return (YYYY-MM-DD, YYYYMMDD)."""
    raw = trade_date.strip().replace("/", "-")
    if len(raw) == 8 and raw.isdigit():
        iso = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
        return iso, raw
    dt = datetime.strptime(raw, "%Y-%m-%d")
    return dt.strftime("%Y-%m-%d"), dt.strftime("%Y%m%d")


def fetch_lhb_detail(start_date: str, end_date: str | None = None, use_cache: bool = True) -> pd.DataFrame:
    """Fetch Eastmoney LHB detail table for a date range."""
    import akshare as ak

    start_iso, start_ymd = normalize_date(start_date)
    end_iso, end_ymd = normalize_date(end_date or start_date)
    cache_name = f"detail_{start_ymd}_{end_ymd}.json"

    if use_cache:
        cached = _read_cache(cache_name)
        if cached is not None:
            df = pd.DataFrame(cached)
            if not df.empty and "上榜日" in df.columns:
                sample = df["上榜日"].iloc[0]
                if isinstance(sample, (int, float)) or (isinstance(sample, str) and sample.isdigit() and len(sample) > 10):
                    df["上榜日"] = pd.to_datetime(df["上榜日"], unit="ms").dt.strftime("%Y-%m-%d")
                else:
                    df["上榜日"] = pd.to_datetime(df["上榜日"]).dt.strftime("%Y-%m-%d")
            return df

    df = ak.stock_lhb_detail_em(start_date=start_ymd, end_date=end_ymd)
    # Normalize date to ISO string so JSON cache never stores ms timestamps
    if "上榜日" in df.columns:
        df = df.copy()
        df["上榜日"] = pd.to_datetime(df["上榜日"]).dt.strftime("%Y-%m-%d")
    records = df.to_dict(orient="records")
    _write_cache(cache_name, records)
    return pd.DataFrame(records)


def fetch_buy_seats(symbol: str, trade_date: str, use_cache: bool = True) -> pd.DataFrame:
    """Fetch buy-side top seats for one stock on LHB date."""
    import akshare as ak

    _, ymd = normalize_date(trade_date)
    code = symbol.split(".")[0]
    cache_name = f"seats_buy_{code}_{ymd}.json"

    if use_cache:
        cached = _read_cache(cache_name, max_age_hours=72)
        if cached is not None:
            return pd.DataFrame(cached)

    df = ak.stock_lhb_stock_detail_em(symbol=code, date=ymd, flag="买入")
    records = df.to_dict(orient="records")
    _write_cache(cache_name, records)
    time.sleep(0.12)
    return pd.DataFrame(records)


def seat_quality(buy_df: pd.DataFrame) -> dict[str, Any]:
    """Classify buy seats into institution / northbound / hot-money."""
    if buy_df is None or buy_df.empty:
        return {
            "n_inst": 0,
            "n_north": 0,
            "n_hot": 0,
            "inst_net": 0.0,
            "north_net": 0.0,
            "hot_net": 0.0,
            "buy_seats": [],
        }

    names = buy_df["交易营业部名称"].astype(str)
    inst_mask = names.str.contains("机构", na=False)
    north_mask = names.str.contains("股通|沪股通|深股通", na=False, regex=True)
    hot_mask = ~(inst_mask | north_mask)

    def _sum(mask: pd.Series) -> float:
        if "净额" not in buy_df.columns:
            return 0.0
        return float(buy_df.loc[mask, "净额"].fillna(0).sum())

    seats = []
    for _, row in buy_df.iterrows():
        name = str(row.get("交易营业部名称", ""))
        if "机构" in name:
            kind = "机构"
        elif "股通" in name:
            kind = "北向"
        else:
            kind = "游资/营业部"
        seats.append(
            {
                "name": name,
                "kind": kind,
                "buy": float(row.get("买入金额") or 0),
                "sell": float(row.get("卖出金额") or 0),
                "net": float(row.get("净额") or 0),
            }
        )

    return {
        "n_inst": int(inst_mask.sum()),
        "n_north": int(north_mask.sum()),
        "n_hot": int(hot_mask.sum()),
        "inst_net": _sum(inst_mask),
        "north_net": _sum(north_mask),
        "hot_net": _sum(hot_mask),
        "buy_seats": seats,
    }

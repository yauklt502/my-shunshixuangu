#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resume failed Tencent downloads; fall back to Sina daily kline."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

from download_data import (
    DATA,
    HEADERS,
    INDEX_CODES,
    TENCENT_KLINE,
    _tencent_symbol,
    fetch_kline,
)

SINA_KLINE = (
    "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "CN_MarketData.getKLineData"
)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def fetch_kline_sina(symbol: str, count: int = 820, session: requests.Session | None = None) -> pd.DataFrame:
    s = session or _session()
    last_err = None
    for attempt in range(4):
        try:
            r = s.get(
                SINA_KLINE,
                params={"symbol": symbol, "scale": 240, "ma": "no", "datalen": count},
                timeout=20,
            )
            r.raise_for_status()
            rows = r.json()
            if not isinstance(rows, list) or not rows:
                return pd.DataFrame()
            recs = []
            for row in rows:
                vol = float(row.get("volume") or 0)
                close = float(row["close"])
                recs.append(
                    {
                        "date": pd.to_datetime(str(row["day"])[:10]),
                        "open": float(row["open"]),
                        "close": close,
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        # Sina volume is shares; store as 手 to match Tencent
                        "volume": vol / 100.0,
                        "amount": close * vol,
                    }
                )
            return pd.DataFrame(recs)
        except Exception as e:
            last_err = e
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"sina {symbol}: {last_err}")


def fetch_any(symbol: str, count: int = 820) -> pd.DataFrame:
    try:
        df = fetch_kline(symbol, count=count)
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    time.sleep(0.2)
    return fetch_kline_sina(symbol, count=count)


def missing_codes() -> pd.DataFrame:
    meta = pd.read_csv(DATA / "meta.csv", dtype={"code": str})
    prices = pd.read_parquet(DATA / "prices.parquet")
    have = set(prices["code"].astype(str).str.zfill(6))
    # keep stocks with too-few bars as missing
    counts = prices.groupby(prices["code"].astype(str).str.zfill(6)).size()
    thin = set(counts[counts < 80].index)
    need = meta[~meta["code"].isin(have - thin)].copy()
    return need


def retry_missing(max_workers: int = 4, count: int = 820) -> None:
    prices = pd.read_parquet(DATA / "prices.parquet")
    need = missing_codes()
    print(f"retry {len(need)} stocks; already have {prices['code'].nunique()}")
    frames = [prices]
    failed = []

    def _one(row):
        code, name, symbol = row["code"], row["name"], row["symbol"]
        df = fetch_any(symbol, count=count)
        if df is None or df.empty:
            return None
        df["code"] = code
        df["name"] = name
        df["symbol"] = symbol
        time.sleep(0.15)
        return df

    rows = need.to_dict("records")
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_one, r): r["code"] for r in rows}
        for f in tqdm(as_completed(futs), total=len(futs), desc="retry"):
            code = futs[f]
            try:
                df = f.result()
                if df is None or df.empty:
                    failed.append(code)
                else:
                    frames.append(df)
            except Exception:
                failed.append(code)

    # indices
    idx_frames = []
    for sym, name in INDEX_CODES.items():
        try:
            df = fetch_any(sym, count=count)
            if df is not None and not df.empty:
                df["code"] = sym
                df["name"] = name
                df["symbol"] = sym
                idx_frames.append(df)
                print("index ok", sym, len(df))
            else:
                print("index empty", sym)
        except Exception as e:
            print("index fail", sym, e)
        time.sleep(0.3)

    out = pd.concat(frames, ignore_index=True)
    out["code"] = out["code"].astype(str)
    out = out.drop_duplicates(["code", "date"], keep="last")
    out.to_parquet(DATA / "prices.parquet", index=False)
    if idx_frames:
        index = pd.concat(idx_frames, ignore_index=True)
        index.to_parquet(DATA / "index.parquet", index=False)
    pd.Series(failed, name="code").to_csv(DATA / "download_failed.csv", index=False)
    print(
        f"now stocks={out['code'].nunique()} rows={len(out)} "
        f"still_failed={len(failed)} cyb={out['code'].str.startswith('300').sum()}"
    )
    print("unique cyb", out.loc[out["code"].str.startswith("300"), "code"].nunique())
    print("unique 002", out.loc[out["code"].str.startswith("002"), "code"].nunique())
    print("unique 000", out.loc[out["code"].str.startswith("000"), "code"].nunique())


if __name__ == "__main__":
    retry_missing()

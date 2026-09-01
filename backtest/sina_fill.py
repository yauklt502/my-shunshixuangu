#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn/",
}
SINA_KLINE = (
    "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "CN_MarketData.getKLineData"
)
INDEX_CODES = {
    "sh000001": "上证指数",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
    "sh000300": "沪深300",
}


def sina_bars(symbol: str, count: int = 820) -> pd.DataFrame:
    last = None
    for attempt in range(5):
        try:
            r = requests.get(
                SINA_KLINE,
                params={"symbol": symbol, "scale": 240, "ma": "no", "datalen": count},
                timeout=20,
                headers=HEADERS,
            )
            r.raise_for_status()
            rows = r.json()
            if not isinstance(rows, list) or not rows:
                return pd.DataFrame()
            recs = []
            for row in rows:
                vol = float(row.get("volume") or 0)  # 股
                close = float(row["close"])
                recs.append(
                    {
                        "date": pd.to_datetime(str(row["day"])[:10]),
                        "open": float(row["open"]),
                        "close": close,
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "volume": vol / 100.0,  # 手，与腾讯对齐
                        "amount": close * vol,
                    }
                )
            return pd.DataFrame(recs)
        except Exception as e:
            last = e
            time.sleep(0.4 * (attempt + 1))
    raise RuntimeError(f"{symbol}: {last}")


def main():
    meta = pd.read_csv(DATA / "meta.csv", dtype={"code": str})
    prices = pd.read_parquet(DATA / "prices.parquet")
    prices["code"] = prices["code"].astype(str).str.zfill(6)
    counts = prices.groupby("code").size()
    good = set(counts[counts >= 80].index)
    need = meta[~meta["code"].isin(good)].copy()
    print(f"need {len(need)}  have_good {len(good)}")

    frames = [prices[prices["code"].isin(good)]]
    failed = []

    def one(row):
        df = sina_bars(row["symbol"])
        if df.empty:
            return None
        df["code"] = row["code"]
        df["name"] = row["name"]
        df["symbol"] = row["symbol"]
        return df

    rows = need.to_dict("records")
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(one, r): r["code"] for r in rows}
        for f in tqdm(as_completed(futs), total=len(futs), desc="sina"):
            code = futs[f]
            try:
                df = f.result()
                if df is None or df.empty:
                    failed.append(code)
                else:
                    frames.append(df)
            except Exception:
                failed.append(code)

    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(["code", "date"], keep="last")
    out.to_parquet(DATA / "prices.parquet", index=False)

    idx_frames = []
    for sym, name in INDEX_CODES.items():
        df = sina_bars(sym)
        df["code"] = sym
        df["name"] = name
        df["symbol"] = sym
        idx_frames.append(df)
        print("index", sym, len(df), df["date"].min() if len(df) else None)
    pd.concat(idx_frames, ignore_index=True).to_parquet(DATA / "index.parquet", index=False)
    pd.Series(failed, name="code").to_csv(DATA / "download_failed.csv", index=False)
    print(
        "stocks", out["code"].nunique(),
        "cyb", out.loc[out["code"].str.startswith("300"), "code"].nunique(),
        "002", out.loc[out["code"].str.startswith("002"), "code"].nunique(),
        "000", out.loc[out["code"].str.startswith("000"), "code"].nunique(),
        "failed", len(failed),
    )


if __name__ == "__main__":
    main()

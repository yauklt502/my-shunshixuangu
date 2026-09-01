#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download A-share daily bars (qfq) via Tencent + stock list via Sina."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn/",
}
SINA_LIST = (
    "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "Market_Center.getHQNodeData"
)
SINA_COUNT = (
    "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "Market_Center.getHQNodeStockCount"
)
TENCENT_KLINE = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

VALID_PREFIX = ("000", "001", "002", "300", "600", "601", "603", "605", "688")
INDEX_CODES = {
    "sh000001": "上证指数",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
    "sh000300": "沪深300",
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def fetch_stock_list(session: requests.Session | None = None) -> pd.DataFrame:
    s = session or _session()
    r = s.get(SINA_COUNT, params={"node": "hs_a"}, timeout=20)
    r.raise_for_status()
    total = int(str(r.text).replace('"', "").strip())
    page_size = 80
    pages = (total + page_size - 1) // page_size
    rows: list[dict] = []
    for page in range(1, pages + 1):
        for attempt in range(4):
            try:
                rr = s.get(
                    SINA_LIST,
                    params={
                        "page": page,
                        "num": page_size,
                        "sort": "symbol",
                        "asc": 1,
                        "node": "hs_a",
                        "symbol": "",
                        "_s_r_a": "page",
                    },
                    timeout=25,
                )
                rr.raise_for_status()
                batch = rr.json()
                if isinstance(batch, list):
                    rows.extend(batch)
                break
            except Exception:
                time.sleep(0.6 * (attempt + 1))
        time.sleep(0.05)
    df = pd.DataFrame(rows)
    df["code"] = df["code"].astype(str).str.zfill(6)
    df["symbol"] = df["symbol"].astype(str)
    df = df[df["code"].str.startswith(VALID_PREFIX)].copy()
    df = df[~df["name"].astype(str).str.contains("ST|退", na=False)]
    df = df.drop_duplicates("code")
    out = df[["code", "name", "symbol"]].reset_index(drop=True)
    out.to_csv(DATA / "meta.csv", index=False, encoding="utf-8-sig")
    return out


def _tencent_symbol(code: str) -> str:
    if code.startswith("6") or code.startswith("9"):
        return f"sh{code}"
    return f"sz{code}"


def fetch_kline(symbol: str, count: int = 820, session: requests.Session | None = None) -> pd.DataFrame:
    s = session or _session()
    last_err = None
    for attempt in range(5):
        try:
            r = s.get(
                TENCENT_KLINE,
                params={"param": f"{symbol},day,,,{count},qfq"},
                timeout=20,
            )
            r.raise_for_status()
            payload = r.json()
            block = (payload.get("data") or {}).get(symbol) or {}
            rows = block.get("qfqday") or block.get("day") or []
            if not rows:
                return pd.DataFrame()
            recs = []
            for row in rows:
                # Tencent: date, open, close, high, low, volume(手)
                recs.append(
                    {
                        "date": row[0][:10],
                        "open": float(row[1]),
                        "close": float(row[2]),
                        "high": float(row[3]),
                        "low": float(row[4]),
                        "volume": float(row[5]) if row[5] not in ("", None) else 0.0,
                    }
                )
            df = pd.DataFrame(recs)
            df["date"] = pd.to_datetime(df["date"])
            df["amount"] = df["close"] * df["volume"] * 100.0  # 元；volume 为手
            return df
        except Exception as e:
            last_err = e
            time.sleep(0.4 * (attempt + 1))
    raise RuntimeError(f"{symbol}: {last_err}")


def download_all(max_workers: int = 16, count: int = 820) -> None:
    meta = fetch_stock_list()
    print(f"universe: {len(meta)} stocks")
    tasks = []
    for _, row in meta.iterrows():
        tasks.append((row["code"], _tencent_symbol(row["code"]), row["name"]))
    for idx_sym, idx_name in INDEX_CODES.items():
        tasks.append((idx_sym[-6:] if False else idx_sym, idx_sym, idx_name))

    frames: list[pd.DataFrame] = []
    failed: list[str] = []

    def _one(item):
        code, symbol, name = item
        df = fetch_kline(symbol, count=count)
        if df.empty:
            return None
        df["code"] = code if not str(code).startswith(("sh", "sz")) else code
        # keep index codes as sh000001 / sz399001
        if symbol in INDEX_CODES:
            df["code"] = symbol
        else:
            df["code"] = code
        df["name"] = name
        df["symbol"] = symbol
        return df

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_one, t): t[0] for t in tasks}
        for f in tqdm(as_completed(futs), total=len(futs), desc="download"):
            key = futs[f]
            try:
                df = f.result()
                if df is None or df.empty:
                    failed.append(str(key))
                else:
                    frames.append(df)
            except Exception:
                failed.append(str(key))

    if not frames:
        raise SystemExit("no kline data downloaded")

    prices = pd.concat(frames, ignore_index=True)
    idx_mask = prices["code"].isin(INDEX_CODES.keys())
    index_df = prices.loc[idx_mask].copy()
    stock_df = prices.loc[~idx_mask].copy()

    stock_df.to_parquet(DATA / "prices.parquet", index=False)
    index_df.to_parquet(DATA / "index.parquet", index=False)
    pd.Series(failed, name="code").to_csv(DATA / "download_failed.csv", index=False)
    print(
        f"saved stocks={stock_df['code'].nunique()} rows={len(stock_df)} "
        f"index={index_df['code'].nunique()} failed={len(failed)}"
    )
    print(stock_df["date"].min(), "->", stock_df["date"].max())


if __name__ == "__main__":
    download_all()

#!/usr/bin/env python3
"""Download Eastmoney limit-up pools and Tencent daily K-lines for backtests."""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/",
}

SESSION_LOCAL = {}


def session() -> requests.Session:
    import threading

    tid = threading.get_ident()
    if tid not in SESSION_LOCAL:
        s = requests.Session()
        s.headers.update(HEADERS)
        SESSION_LOCAL[tid] = s
    return SESSION_LOCAL[tid]


def get_json(url: str, params: dict | None = None, retries: int = 5, timeout: int = 15):
    last = None
    for i in range(retries):
        try:
            r = session().get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(0.4 * (2**i))
    raise RuntimeError(f"GET failed {url} {params}: {last}")


def trade_dates(start: str, end: str) -> list[str]:
    """YYYYMMDD list from Sina trading calendar."""
    import akshare as ak

    cal = ak.tool_trade_date_hist_sina()
    cal["trade_date"] = pd.to_datetime(cal["trade_date"])
    lo = pd.Timestamp(start)
    hi = pd.Timestamp(end)
    mask = (cal["trade_date"] >= lo) & (cal["trade_date"] <= hi)
    return cal.loc[mask, "trade_date"].dt.strftime("%Y%m%d").tolist()


def fetch_zt_pool(date: str) -> pd.DataFrame:
    url = "https://push2ex.eastmoney.com/getTopicZTPool"
    params = {
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "dpt": "wz.ztzt",
        "Pageindex": "0",
        "pagesize": "10000",
        "sort": "fbt:asc",
        "date": date,
    }
    data_json = get_json(url, params)
    if not data_json or data_json.get("data") is None:
        return pd.DataFrame()
    pool = data_json["data"].get("pool") or []
    if not pool:
        return pd.DataFrame()
    df = pd.DataFrame(pool)
    stats = df["zttj"].apply(lambda x: x if isinstance(x, dict) else {})
    df = pd.DataFrame(
        {
            "date": date,
            "code": df["c"].astype(str).str.zfill(6),
            "name": df["n"],
            "close": df["p"] / 1000.0,
            "pct": pd.to_numeric(df["zdp"], errors="coerce"),
            "amount": pd.to_numeric(df["amount"], errors="coerce"),
            "float_mv": pd.to_numeric(df["ltsz"], errors="coerce"),
            "total_mv": pd.to_numeric(df["tshare"], errors="coerce"),
            "turnover": pd.to_numeric(df["hs"], errors="coerce"),
            "board_n": pd.to_numeric(df["lbc"], errors="coerce"),
            "first_seal": df["fbt"].astype(str).str.zfill(6),
            "last_seal": df["lbt"].astype(str).str.zfill(6),
            "seal_money": pd.to_numeric(df["fund"], errors="coerce"),
            "break_n": pd.to_numeric(df["zbc"], errors="coerce"),
            "industry": df["hy"].astype(str) if "hy" in df.columns else "",
            "stat_days": stats.apply(lambda x: x.get("days")),
            "stat_ct": stats.apply(lambda x: x.get("ct")),
        }
    )
    return df


def download_zt(start: str, end: str, workers: int = 8) -> pd.DataFrame:
    out = DATA / "zt_pool.parquet"
    dates = trade_dates(start, end)
    have = set()
    frames = []
    if out.exists():
        old = pd.read_parquet(out)
        have = set(old["date"].astype(str).unique())
        frames.append(old)
        print(f"cache {len(have)} days, need {len(dates)}")
    missing = [d for d in dates if d not in have]
    print(f"download zt pool: {len(missing)} days")
    rows = []
    if missing:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(fetch_zt_pool, d): d for d in missing}
            for i, fut in enumerate(as_completed(futs), 1):
                d = futs[fut]
                try:
                    df = fut.result()
                    if df is not None and len(df):
                        rows.append(df)
                    if i % 50 == 0:
                        print(f"  zt {i}/{len(missing)} last={d} rows={0 if df is None else len(df)}")
                except Exception as exc:  # noqa: BLE001
                    print(f"  FAIL {d}: {exc}")
    if rows:
        frames.append(pd.concat(rows, ignore_index=True))
    if not frames:
        return pd.DataFrame()
    all_df = pd.concat(frames, ignore_index=True)
    all_df = all_df.drop_duplicates(["date", "code"], keep="last")
    all_df.to_parquet(out, index=False)
    print(f"saved {out} n={len(all_df)}")
    return all_df


def to_tx_symbol(code: str) -> str | None:
    code = str(code).zfill(6)
    if code.startswith(("000", "001", "002", "003", "300", "301")):
        return f"sz{code}"
    if code.startswith(("600", "601", "603", "605", "688", "689")):
        return f"sh{code}"
    return None


def fetch_kline(code: str, ndays: int = 900) -> pd.DataFrame:
    sym = to_tx_symbol(code)
    if not sym:
        return pd.DataFrame()
    url = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"
    payload = get_json(url, {"param": f"{sym},day,,,{ndays}"})
    node = (payload.get("data") or {}).get(sym) or {}
    days = node.get("day") or node.get("qfqday") or []
    if not days:
        return pd.DataFrame()
    recs = []
    for row in days:
        recs.append(
            {
                "code": str(code).zfill(6),
                "date": str(row[0]).replace("-", ""),
                "open": float(row[1]),
                "close": float(row[2]),
                "high": float(row[3]),
                "low": float(row[4]),
                "volume": float(row[5]) if len(row) > 5 and row[5] not in ("", None) else 0.0,
            }
        )
    return pd.DataFrame(recs)


def download_klines(codes: list[str], workers: int = 16, ndays: int = 900) -> pd.DataFrame:
    out = DATA / "kline.parquet"
    have = set()
    frames = []
    if out.exists():
        old = pd.read_parquet(out)
        have = set(old["code"].astype(str).str.zfill(6).unique())
        frames.append(old)
        print(f"kline cache stocks={len(have)}")
    missing = [c for c in codes if str(c).zfill(6) not in have]
    print(f"download kline: {len(missing)} stocks")
    rows = []
    if missing:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(fetch_kline, c, ndays): c for c in missing}
            for i, fut in enumerate(as_completed(futs), 1):
                c = futs[fut]
                try:
                    df = fut.result()
                    if df is not None and len(df):
                        rows.append(df)
                    if i % 100 == 0:
                        print(f"  kline {i}/{len(missing)} last={c} n={0 if df is None else len(df)}")
                except Exception as exc:  # noqa: BLE001
                    print(f"  FAIL {c}: {exc}")
    if rows:
        frames.append(pd.concat(rows, ignore_index=True))
    if not frames:
        return pd.DataFrame()
    all_df = pd.concat(frames, ignore_index=True)
    all_df["code"] = all_df["code"].astype(str).str.zfill(6)
    all_df = all_df.drop_duplicates(["code", "date"], keep="last")
    all_df.to_parquet(out, index=False)
    print(f"saved {out} n={len(all_df)}")
    return all_df


def download_index(ndays: int = 900) -> pd.DataFrame:
    url = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"
    payload = get_json(url, {"param": f"sh000001,day,,,{ndays}"})
    days = (payload.get("data") or {}).get("sh000001", {}).get("day") or []
    df = pd.DataFrame(days, columns=["date", "open", "close", "high", "low", "volume"][: len(days[0])])
    df["date"] = df["date"].astype(str).str.replace("-", "", regex=False)
    for col in ["open", "close", "high", "low"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    out = DATA / "index_sh.parquet"
    df.to_parquet(out, index=False)
    print(f"saved {out} n={len(df)}")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="20240101")
    ap.add_argument("--end", default=datetime.now().strftime("%Y%m%d"))
    ap.add_argument("--zt-workers", type=int, default=8)
    ap.add_argument("--kline-workers", type=int, default=16)
    args = ap.parse_args()

    zt = download_zt(args.start, args.end, workers=args.zt_workers)
    download_index()
    codes = sorted(zt["code"].astype(str).str.zfill(6).unique().tolist()) if len(zt) else []
    # always include a few majors in case zt is empty
    codes = sorted(set(codes) | {"000001", "600519", "300750"})
    download_klines(codes, workers=args.kline_workers)
    meta = {
        "start": args.start,
        "end": args.end,
        "zt_rows": int(len(zt)),
        "zt_days": int(zt["date"].nunique()) if len(zt) else 0,
        "codes": len(codes),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }
    (DATA / "download_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""下载回测数据（腾讯日K + 可选东财近端涨停池）。

东财 push2his / 历史涨停池在本环境不稳定，故：
1) 新浪拉主板名单
2) 腾讯拉日K
3) 回测脚本用日K识别昨日涨停；近端东财池可补充炸板/封板时间
"""

from __future__ import annotations

import argparse
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CST = timezone(timedelta(hours=8))
CTX = ssl.create_default_context()
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

SINA_LIST = (
    "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "Market_Center.getHQNodeData?page={page}&num=100&sort=symbol&asc=1&node={node}"
)
TX_KLINE = (
    "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    "?param={symbol},day,{start},{end},640,qfq"
)
ZT_URL = (
    "https://push2ex.eastmoney.com/getTopicZTPool"
    "?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
    "&Pageindex=0&pagesize=200&sort=lbc:desc&date={date}"
)


def http_bytes(url: str, *, referer: str, retries: int = 4) -> bytes:
    last: Exception | None = None
    delay = 0.25
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer})
            with urllib.request.urlopen(req, timeout=20, context=CTX) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last = exc
            time.sleep(delay)
            delay = min(delay * 2, 2.5)
    raise RuntimeError(f"request failed: {url}") from last


def http_json(url: str, *, referer: str, retries: int = 4) -> Any:
    return json.loads(http_bytes(url, referer=referer, retries=retries).decode("utf-8", "replace"))


def is_main_code(code: str) -> bool:
    code = str(code).zfill(6)
    if code.startswith(("300", "301", "688", "689", "8", "4", "200", "900")):
        return False
    return code.startswith(("60", "000", "001", "002", "003"))


def tx_symbol(code: str) -> str:
    code = str(code).zfill(6)
    return ("sh" if code.startswith(("5", "6", "9")) else "sz") + code


def fetch_sina_node(node: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for page in range(1, 80):
        url = SINA_LIST.format(page=page, node=node)
        raw = http_bytes(url, referer="https://finance.sina.com.cn/")
        text = raw.decode("gbk", "replace").strip()
        if not text or text == "null":
            break
        data = json.loads(text)
        if not data:
            break
        for x in data:
            code = str(x.get("code") or "").zfill(6)
            name = str(x.get("name") or "")
            if not is_main_code(code):
                continue
            if "ST" in name.upper() or "退" in name:
                continue
            rows.append(
                {
                    "code": code,
                    "name": name,
                    "nmc": float(x.get("nmc") or 0),  # 万元
                }
            )
        if len(data) < 100:
            break
        time.sleep(0.05)
    return pd.DataFrame(rows).drop_duplicates("code")


def download_stock_list() -> pd.DataFrame:
    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / "stock_list.csv"
    frames = [fetch_sina_node("sh_a"), fetch_sina_node("sz_a")]
    df = pd.concat(frames, ignore_index=True).drop_duplicates("code")
    df.to_csv(out, index=False)
    print(f"stock_list {len(df)} -> {out}")
    return df


def fetch_tx_kline(code: str, start: str, end: str) -> pd.DataFrame:
    # tencent wants YYYY-MM-DD
    s = f"{start[:4]}-{start[4:6]}-{start[6:8]}"
    e = f"{end[:4]}-{end[4:6]}-{end[6:8]}"
    url = TX_KLINE.format(symbol=tx_symbol(code), start=s, end=e)
    data = http_json(url, referer="https://finance.qq.com/")
    node = (data.get("data") or {}).get(tx_symbol(code)) or {}
    bars = node.get("qfqday") or node.get("day") or []
    rows = []
    for b in bars:
        # date, open, close, high, low, volume
        rows.append(
            {
                "code": code,
                "date": str(b[0]).replace("-", ""),
                "open": float(b[1]),
                "close": float(b[2]),
                "high": float(b[3]),
                "low": float(b[4]),
                "volume": float(b[5]),
            }
        )
    return pd.DataFrame(rows)


def download_klines(codes: list[str], start: str, end: str, workers: int = 16) -> pd.DataFrame:
    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / "kline.parquet"
    frames: list[pd.DataFrame] = []
    have: set[str] = set()
    if out.exists():
        old = pd.read_parquet(out)
        old["code"] = old["code"].astype(str).str.zfill(6)
        # 若覆盖区间足够则复用
        if str(old["date"].min()) <= start and str(old["date"].max()) >= end:
            print(f"kline cache hit {old['code'].nunique()} {old['date'].min()}-{old['date'].max()}")
            return old
        have = set(old["code"].unique())
        frames.append(old)
    need = [c for c in codes if c not in have]
    print(f"tencent kline download {len(need)}/{len(codes)}")
    done = 0
    ok = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_tx_kline, c, start, end): c for c in need}
        for fut in as_completed(futs):
            c = futs[fut]
            done += 1
            try:
                df = fut.result()
                if not df.empty:
                    frames.append(df)
                    ok += 1
            except Exception as exc:  # noqa: BLE001
                if done <= 5 or done % 100 == 0:
                    print(f"\nfail {c}: {exc}")
            if done % 30 == 0 or done == len(need):
                print(f"\rkline {done}/{len(need)} ok={ok}", end="", flush=True)
    print()
    if not frames:
        return pd.DataFrame()
    all_df = pd.concat(frames, ignore_index=True)
    all_df["code"] = all_df["code"].astype(str).str.zfill(6)
    all_df = all_df.drop_duplicates(["code", "date"], keep="last")
    all_df = all_df.sort_values(["code", "date"]).reset_index(drop=True)
    all_df.to_parquet(out, index=False)
    print(f"kline saved rows={len(all_df)} codes={all_df['code'].nunique()} -> {out}")
    return all_df


def fetch_zt_day(date: str) -> pd.DataFrame:
    try:
        data = http_json(ZT_URL.format(date=date), referer="https://quote.eastmoney.com/")
    except Exception:  # noqa: BLE001
        return pd.DataFrame()
    pool = (data.get("data") or {}).get("pool") or []
    if not pool:
        return pd.DataFrame()
    rows = []
    for x in pool:
        p = float(x.get("p") or 0)
        close = p / 1000.0 if p > 1000 else p
        rows.append(
            {
                "date": date,
                "code": str(x.get("c") or "").zfill(6),
                "name": x.get("n") or "",
                "close": close,
                "pct": float(x.get("zdp") or 0),
                "amount": float(x.get("amount") or 0),
                "ltsz": float(x.get("ltsz") or 0),
                "hs": float(x.get("hs") or 0),
                "lbc": int(x.get("lbc") or 1),
                "zbc": int(x.get("zbc") or 0),
                "fbt": int(x.get("fbt") or 150000),
                "hy": x.get("hybk") or "",
            }
        )
    return pd.DataFrame(rows)


def download_zt_recent(start: str, end: str, workers: int = 8) -> pd.DataFrame:
    """尽力拉东财涨停池（历史可能只有近端有数据）。"""
    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / "zt_pool.parquet"
    lo = datetime.strptime(start, "%Y%m%d")
    hi = datetime.strptime(end, "%Y%m%d")
    dates = []
    cur = lo
    while cur <= hi:
        if cur.weekday() < 5:
            dates.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)
    frames: list[pd.DataFrame] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_zt_day, d): d for d in dates}
        for fut in as_completed(futs):
            df = fut.result()
            if not df.empty:
                frames.append(df)
    if not frames:
        print("zt pool empty (eastmoney history unavailable)")
        return pd.DataFrame()
    all_df = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "code"])
    all_df.to_parquet(out, index=False)
    print(f"zt pool rows={len(all_df)} days={all_df['date'].nunique()} -> {out}")
    return all_df


def main() -> int:
    now = datetime.now(CST)
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="20250101")
    parser.add_argument("--end", default=now.strftime("%Y%m%d"))
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--max-codes", type=int, default=0, help="调试用，限制股票数")
    args = parser.parse_args()

    stocks = download_stock_list()
    codes = stocks["code"].astype(str).str.zfill(6).tolist()
    if args.max_codes > 0:
        codes = codes[: args.max_codes]
    beg = (datetime.strptime(args.start, "%Y%m%d") - timedelta(days=15)).strftime("%Y%m%d")
    end = (datetime.strptime(args.end, "%Y%m%d") + timedelta(days=5)).strftime("%Y%m%d")
    download_klines(codes, beg, end, workers=args.workers)
    download_zt_recent(args.start, args.end)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

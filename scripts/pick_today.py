#!/usr/bin/env python3
"""Print today's first-board auction picks (run 09:25-09:28)."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import requests

from backtest import OFFICIAL, build_universe, load_frames, select_and_trade
from download_data import trade_dates

HEADERS = {"User-Agent": "Mozilla/5.0"}


def sina_snapshot() -> pd.DataFrame:
    rows: list[dict] = []
    for page in range(1, 80):
        r = requests.get(
            "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData",
            params={"page": page, "num": 80, "sort": "symbol", "asc": 1, "node": "hs_a"},
            headers=HEADERS,
            timeout=20,
        )
        data = r.json()
        if not data:
            break
        rows.extend(data)
    df = pd.DataFrame(rows)
    df["code"] = df["code"].astype(str).str.zfill(6)
    df["open"] = pd.to_numeric(df["open"], errors="coerce")
    df["settlement"] = pd.to_numeric(df["settlement"], errors="coerce")
    df["nmc"] = pd.to_numeric(df["nmc"], errors="coerce")
    df["nmc_yi"] = df["nmc"] / 10000.0
    df["auction_pct"] = df["open"] / df["settlement"] - 1.0
    return df


def main():
    today = datetime.now().strftime("%Y%m%d")
    dates = trade_dates("20240101", today)
    if not dates:
        raise SystemExit("no trade dates")
    session = dates[-1]
    print("session", session, "now", today)

    kline, names, idx = load_frames()
    uni = build_universe(kline, names, idx)
    p = OFFICIAL

    have_today = (uni["next_date"] == session).any()
    if have_today:
        picks = select_and_trade(uni.loc[uni["next_date"] == session], p)
        cols = ["code", "name", "auction_pct", "buy_open", "float_mv_yi", "vol_ratio", "rank_in_day"]
        print(picks[cols].to_string(index=False))
        return

    # live: yesterday first-boards in universe.date == previous session, overlay sina open
    prev = dates[-2] if session == today else session
    if session != today:
        prev = session
    cand = uni.loc[uni["date"] == prev].copy()
    if cand.empty:
        raise SystemExit(f"no first-board rows for {prev}; update kline cache")
    snap = sina_snapshot()
    m = cand.merge(snap[["code", "open", "auction_pct", "nmc_yi"]], on="code", how="left", suffixes=("", "_live"))
    m["buy_open"] = m["open"]
    m["auction_pct"] = m["auction_pct_live"]
    m["float_mv_yi"] = m["nmc_yi"].fillna(m["float_mv_yi"])
    m["open_is_limit"] = m["buy_open"] + 1e-8 >= m["next_zt"] - 0.01
    m["open_is_down_limit"] = m["buy_open"] <= m["next_dt"] + 0.01
    m["next_date"] = today
    picks = select_and_trade(m, p)
    cols = ["code", "name", "auction_pct", "buy_open", "float_mv_yi", "vol_ratio", "rank_in_day"]
    if picks.empty:
        print("no pick")
        return
    print(picks[cols].to_string(index=False))


if __name__ == "__main__":
    main()

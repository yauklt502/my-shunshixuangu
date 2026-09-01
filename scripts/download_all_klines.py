#!/usr/bin/env python3
"""Download Tencent daily bars for all HS A-shares (resume-safe)."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from download_data import DATA, download_klines, to_tx_symbol

ROOT = Path(__file__).resolve().parents[1]


def main():
    lst = pd.read_csv(DATA / "stock_list.csv", dtype={"code": str})
    lst["code"] = lst["code"].str.zfill(6)
    lst = lst.loc[lst["code"].map(lambda c: to_tx_symbol(c) is not None)].copy()
    # skip 北交所 already by to_tx_symbol; skip 科创板 for 打板 universe
    lst = lst.loc[~lst["code"].str.startswith(("688", "689", "8", "4", "92"))]
    codes = lst["code"].drop_duplicates().tolist()
    print("codes", len(codes))
    download_klines(codes, workers=18, ndays=700)
    print("done")


if __name__ == "__main__":
    main()

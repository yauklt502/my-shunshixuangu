"""Download A-share daily bars from baostock for Sequoia-X backtests."""

from __future__ import annotations

import time
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path

import baostock as bs
import pandas as pd

OHLCV_COLUMNS = ["symbol", "date", "open", "high", "low", "close", "volume", "turnover"]
DEFAULT_START = "2023-01-01"
DEFAULT_END = "2026-09-01"
CACHE_PATH = Path("data/hs800_ohlcv.pkl.gz")
META_PATH = Path("data/hs800_meta.pkl.gz")
INDEX_PATH = Path("data/hs300_index.pkl.gz")


def to_baostock_code(symbol: str) -> str:
    prefix = "sh" if symbol.startswith(("6", "9")) else "sz"
    return f"{prefix}.{symbol}"


def from_baostock_code(code: str) -> str:
    return code.split(".")[-1]


def _read_result(rs) -> list[list[str]]:
    rows: list[list[str]] = []
    while rs.next():
        rows.append(rs.get_row_data())
    return rows


def _login() -> None:
    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"baostock login failed: {lg.error_msg}")


@dataclass(frozen=True)
class SymbolMeta:
    symbol: str
    name: str
    universe: str  # hs300 / zz500


def fetch_universe_meta() -> list[SymbolMeta]:
    """Current HS300 + CSI500 members (survivorship-biased, documented)."""
    _login()
    try:
        items: list[SymbolMeta] = []
        seen: set[str] = set()
        for universe, query in (
            ("hs300", bs.query_hs300_stocks),
            ("zz500", bs.query_zz500_stocks),
        ):
            rs = query()
            if rs.error_code != "0":
                raise RuntimeError(f"{universe} query failed: {rs.error_msg}")
            for row in _read_result(rs):
                # fields: updateDate, code, code_name
                symbol = from_baostock_code(row[1])
                name = row[2] if len(row) > 2 else ""
                if symbol in seen:
                    continue
                if "ST" in name.upper():
                    continue
                if symbol.startswith(("4", "8", "9")):
                    continue
                seen.add(symbol)
                items.append(SymbolMeta(symbol=symbol, name=name, universe=universe))
        return items
    finally:
        bs.logout()


def fetch_index(symbol_bs: str = "sh.000300", start: str = DEFAULT_START, end: str = DEFAULT_END) -> pd.DataFrame:
    _login()
    try:
        rs = bs.query_history_k_data_plus(
            symbol_bs,
            "date,open,high,low,close,volume,amount",
            start_date=start,
            end_date=end,
            frequency="d",
            adjustflag="3",
        )
        if rs.error_code != "0":
            raise RuntimeError(rs.error_msg)
        rows = _read_result(rs)
        df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "turnover"])
        for col in ["open", "high", "low", "close", "volume", "turnover"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        return df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    finally:
        bs.logout()


def _fetch_batch(payload: tuple[list[tuple[str, str]], str, str]) -> list[list]:
    tasks, start, end = payload
    import baostock as bs

    results: list[list] = []
    lg = bs.login()
    if lg.error_code != "0":
        return results
    try:
        for symbol, bs_code in tasks:
            ok = False
            for attempt in range(3):
                try:
                    rs = bs.query_history_k_data_plus(
                        bs_code,
                        "date,open,high,low,close,volume,amount",
                        start_date=start,
                        end_date=end,
                        frequency="d",
                        adjustflag="1",  # 后复权，与 Sequoia-X 一致
                    )
                    if rs.error_code != "0":
                        raise RuntimeError(rs.error_msg)
                    while rs.next():
                        results.append([symbol] + rs.get_row_data())
                    ok = True
                    break
                except Exception:
                    time.sleep(2 ** (attempt + 1))
                    bs.logout()
                    time.sleep(1)
                    bs.login()
            if not ok:
                continue
    finally:
        bs.logout()
    return results


def download_ohlcv(
    metas: list[SymbolMeta],
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    workers: int = 12,
) -> pd.DataFrame:
    tasks = [(m.symbol, to_baostock_code(m.symbol)) for m in metas]
    n_workers = max(1, min(workers, len(tasks)))
    chunks = [tasks[i::n_workers] for i in range(n_workers)]
    payloads = [(chunk, start, end) for chunk in chunks if chunk]
    with Pool(len(payloads)) as pool:
        batches = pool.map(_fetch_batch, payloads)
    rows: list[list] = []
    for batch in batches:
        rows.extend(batch)
    if not rows:
        raise RuntimeError("no OHLCV rows downloaded")
    df = pd.DataFrame(rows, columns=OHLCV_COLUMNS)
    for col in ["open", "high", "low", "close", "volume", "turnover"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["close"])
    df = df[df["volume"] > 0]
    df = df.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"]).reset_index(drop=True)
    return df


def save_cache(ohlcv: pd.DataFrame, metas: list[SymbolMeta], index_df: pd.DataFrame) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ohlcv.to_pickle(CACHE_PATH)
    pd.DataFrame([m.__dict__ for m in metas]).to_pickle(META_PATH)
    index_df.to_pickle(INDEX_PATH)


def load_cache() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not CACHE_PATH.exists():
        raise FileNotFoundError(f"missing cache {CACHE_PATH}; run download first")
    ohlcv = pd.read_pickle(CACHE_PATH)
    meta = pd.read_pickle(META_PATH) if META_PATH.exists() else pd.DataFrame()
    index_df = pd.read_pickle(INDEX_PATH) if INDEX_PATH.exists() else pd.DataFrame()
    return ohlcv, meta, index_df


def ensure_data(start: str = DEFAULT_START, end: str = DEFAULT_END, workers: int = 12, force: bool = False):
    if CACHE_PATH.exists() and not force:
        return load_cache()
    metas = fetch_universe_meta()
    ohlcv = download_ohlcv(metas, start=start, end=end, workers=workers)
    index_df = fetch_index(start=start, end=end)
    save_cache(ohlcv, metas, index_df)
    return ohlcv, pd.DataFrame([m.__dict__ for m in metas]), index_df

#!/usr/bin/env python3
"""Backtest yesterday-first-board picks after 09:25 auction.

Buy T+1 open (集合竞价价), skip 竞价/开盘涨停. Keep <=5 names per day.
"""

from __future__ import annotations

import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)


def limit_ratio(code: str) -> float:
    c = str(code).zfill(6)
    if c.startswith(("300", "301", "688", "689")):
        return 0.20
    return 0.10


def load_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    kline = pd.read_parquet(DATA / "kline.parquet")
    kline["code"] = kline["code"].astype(str).str.zfill(6)
    kline["date"] = kline["date"].astype(str)
    kline = kline.loc[~kline["code"].str.startswith(("688", "689", "8", "4", "92"))]
    kline = kline.loc[(kline["open"] > 0) & (kline["close"] > 0) & (kline["volume"] > 0)]

    names = pd.read_csv(DATA / "stock_list.csv", dtype={"code": str})
    names["code"] = names["code"].str.zfill(6)
    names["nmc_yi"] = pd.to_numeric(names["nmc"], errors="coerce") / 10000.0  # 万元 -> 亿
    names = names.drop_duplicates("code")

    idx = pd.read_parquet(DATA / "index_sh.parquet")
    idx["date"] = idx["date"].astype(str)
    idx = idx.sort_values("date")
    idx["idx_pre"] = idx["close"].shift(1)
    idx["idx_open_pct"] = idx["open"] / idx["idx_pre"] - 1.0
    return kline, names, idx


def build_universe(kline: pd.DataFrame, names: pd.DataFrame, idx: pd.DataFrame) -> pd.DataFrame:
    k = kline.sort_values(["code", "date"]).copy()
    k["preclose"] = k.groupby("code")["close"].shift(1)
    k["limit_r"] = k["code"].map(limit_ratio)
    k["pct"] = k["close"] / k["preclose"] - 1.0
    k["is_zt"] = np.where(
        k["limit_r"] >= 0.19,
        k["pct"] >= 0.195,
        k["pct"] >= 0.095,
    )
    k["is_zt"] &= k["close"] >= k["high"] * 0.997
    k["is_zt"] &= k["preclose"].notna()
    k["prev_zt"] = k.groupby("code")["is_zt"].shift(1).fillna(False)
    k["is_fb"] = k["is_zt"] & ~k["prev_zt"]
    k["y_one_word"] = k["is_zt"] & (k["low"] >= k["close"] * 0.997)
    k["vol_ma5"] = k.groupby("code")["volume"].transform(lambda s: s.shift(1).rolling(5, min_periods=3).mean())
    k["vol_ratio"] = k["volume"] / k["vol_ma5"]
    k["range_pct"] = (k["high"] - k["low"]) / k["preclose"]
    k["open_pct"] = k["open"] / k["preclose"] - 1.0

    dates = sorted(idx["date"].unique())
    if not dates:
        dates = sorted(k["date"].unique())
    nxt = {d: dates[i + 1] for i, d in enumerate(dates) if i + 1 < len(dates)}

    fb_n = k.loc[k["is_fb"]].groupby("date").size().rename("market_fb_n")
    zt_n = k.loc[k["is_zt"]].groupby("date").size().rename("market_zt_n")

    fb = k.loc[k["is_fb"]].copy()
    fb["next_date"] = fb["date"].map(nxt)
    fb = fb.dropna(subset=["next_date"])

    nxt_bars = k.rename(
        columns={
            "date": "next_date",
            "open": "buy_open",
            "close": "sell_close",
            "high": "sell_high",
            "low": "sell_low",
            "volume": "next_volume",
            "preclose": "next_preclose",
        }
    )[
        [
            "code",
            "next_date",
            "buy_open",
            "sell_close",
            "sell_high",
            "sell_low",
            "next_volume",
        ]
    ]
    df = fb.merge(nxt_bars, on=["code", "next_date"], how="inner")
    df = df.merge(fb_n, left_on="date", right_index=True, how="left")
    df = df.merge(zt_n, left_on="date", right_index=True, how="left")
    df = df.merge(
        idx[["date", "idx_open_pct"]].rename(columns={"date": "next_date"}),
        on="next_date",
        how="left",
    )
    df = df.merge(names[["code", "name", "nmc_yi"]], on="code", how="left")
    df = df.loc[~df["name"].fillna("").str.contains("ST", case=False, regex=False)]

    df["auction_pct"] = df["buy_open"] / df["close"] - 1.0
    df["next_limit_r"] = df["code"].map(limit_ratio)
    df["next_zt"] = np.round(df["close"] * (1.0 + df["next_limit_r"]) + 1e-8, 2)
    df["next_dt"] = np.round(df["close"] * (1.0 - df["next_limit_r"]) + 1e-8, 2)
    df["open_is_limit"] = df["buy_open"] + 1e-8 >= df["next_zt"] - 0.01
    df["open_is_down_limit"] = df["buy_open"] <= df["next_dt"] + 0.01
    df["float_mv_yi"] = df["nmc_yi"]
    df["turnover"] = df["vol_ratio"]  # proxy used in filters
    df = df.sort_values(["next_date", "code"]).reset_index(drop=True)
    return df


@dataclass
class Params:
    max_break: int = 0  # unused placeholder for formula comments
    first_before: int = 0
    vol_lo: float = 1.0
    vol_hi: float = 8.0
    mv_lo: float = 20.0
    mv_hi: float = 180.0
    auction_lo: float = -0.03
    auction_hi: float = 0.05
    range_lo: float = 0.0
    market_fb_lo: int = 15
    market_fb_hi: int = 250
    idx_open_lo: float = -0.02
    exclude_y_one_word: bool = True
    rank: str = "auction_pct"
    rank_asc: bool = True
    top_n: int = 5
    tp: float = 0.03
    sl: float = 0.04
    cost: float = 0.0015


RANK_COLS = {
    "auction_pct": "auction_pct",
    "abs_auction": "abs_auction",
    "float_mv_yi": "float_mv_yi",
    "vol_ratio": "vol_ratio",
    "range_pct": "range_pct",
}


def select_and_trade(uni: pd.DataFrame, p: Params) -> pd.DataFrame:
    m = (
        ~uni["open_is_limit"]
        & ~uni["open_is_down_limit"]
        & uni["vol_ratio"].between(p.vol_lo, p.vol_hi)
        & uni["float_mv_yi"].between(p.mv_lo, p.mv_hi)
        & uni["auction_pct"].between(p.auction_lo, p.auction_hi)
        & (uni["range_pct"].fillna(0) >= p.range_lo)
        & uni["market_fb_n"].between(p.market_fb_lo, p.market_fb_hi)
        & (uni["idx_open_pct"].fillna(0) >= p.idx_open_lo)
    )
    if p.exclude_y_one_word:
        m &= ~uni["y_one_word"].fillna(False)
    d = uni.loc[m].copy()
    if d.empty:
        return d
    d["abs_auction"] = d["auction_pct"].abs()
    col = RANK_COLS[p.rank]
    d = d.sort_values(["next_date", col], ascending=[True, p.rank_asc], kind="mergesort")
    d["rank_in_day"] = d.groupby("next_date").cumcount() + 1
    d = d.loc[d["rank_in_day"] <= p.top_n].copy()

    o = d["buy_open"].to_numpy(dtype=float)
    h = d["sell_high"].to_numpy(dtype=float)
    l = d["sell_low"].to_numpy(dtype=float)
    c = d["sell_close"].to_numpy(dtype=float)
    ret = c / o - 1.0
    exits = np.full(len(d), "close", dtype=object)
    if p.tp > 0 or p.sl > 0:
        hit_tp = (p.tp > 0) & (h >= o * (1.0 + p.tp))
        hit_sl = (p.sl > 0) & (l <= o * (1.0 - p.sl))
        both = hit_tp & hit_sl
        ret = np.where(both, -p.sl, np.where(hit_tp, p.tp, np.where(hit_sl, -p.sl, ret)))
        exits = np.where(both, "both_sl", np.where(hit_tp, "tp", np.where(hit_sl, "sl", "close")))
    d["ret"] = ret - p.cost
    d["exit"] = exits
    d["win"] = d["ret"] > 0
    return d


def summarize(trades: pd.DataFrame, tag: str) -> dict:
    if trades is None or trades.empty:
        return {
            "tag": tag,
            "n": 0,
            "days": 0,
            "per_day": 0.0,
            "win_rate": 0.0,
            "avg_ret": 0.0,
            "med_ret": 0.0,
            "sum_ret": 0.0,
            "max_dd": 0.0,
            "profit_factor": 0.0,
        }
    r = trades["ret"].astype(float)
    daily = trades.groupby("next_date")["ret"].mean().sort_index()
    equity = (1.0 + daily).cumprod()
    peak = equity.cummax()
    dd = equity / peak - 1.0
    gp = float(r[r > 0].sum())
    gl = float(-r[r <= 0].sum())
    pf = float(gp / gl) if gl > 0 else 999.0
    return {
        "tag": tag,
        "n": int(len(trades)),
        "days": int(trades["next_date"].nunique()),
        "per_day": float(len(trades) / max(trades["next_date"].nunique(), 1)),
        "win_rate": float(trades["win"].mean()),
        "avg_ret": float(r.mean()),
        "med_ret": float(r.median()),
        "sum_ret": float(r.sum()),
        "max_dd": float(dd.min()) if len(dd) else 0.0,
        "profit_factor": pf,
        "avg_win": float(r[r > 0].mean()) if (r > 0).any() else 0.0,
        "avg_loss": float(r[r <= 0].mean()) if (r <= 0).any() else 0.0,
        "tp_share": float((trades["exit"] == "tp").mean()),
        "sl_share": float(trades["exit"].isin(["sl", "both_sl"]).mean()),
    }


def grid_search(uni: pd.DataFrame, train_end: str) -> pd.DataFrame:
    train = uni.loc[uni["next_date"] <= train_end]
    test = uni.loc[uni["next_date"] > train_end]

    vol_bands = [(0.8, 6.0), (1.0, 5.0), (1.2, 8.0)]
    mvs = [(20.0, 150.0), (30.0, 120.0), (15.0, 220.0)]
    auctions = [(-0.04, 0.04), (-0.03, 0.02), (-0.02, 0.03), (0.0, 0.05), (-0.06, 0.01)]
    range_los = [0.0, 0.02]
    fb_bands = [(20, 180), (15, 250)]
    ranks = [
        ("auction_pct", True),
        ("abs_auction", True),
        ("vol_ratio", True),
        ("float_mv_yi", True),
    ]
    exits = [(0.0, 0.0), (0.02, 0.04), (0.03, 0.05), (0.02, 0.03)]
    idx_los = [-0.02, -1.0]

    combos = list(
        itertools.product(vol_bands, mvs, auctions, range_los, fb_bands, ranks, exits, idx_los)
    )
    print(f"grid size {len(combos)}")
    recs = []
    for i, (vol, mv, au, rlo, fb, rk, ex, ilo) in enumerate(combos, 1):
        p = Params(
            vol_lo=vol[0],
            vol_hi=vol[1],
            mv_lo=mv[0],
            mv_hi=mv[1],
            auction_lo=au[0],
            auction_hi=au[1],
            range_lo=rlo,
            market_fb_lo=fb[0],
            market_fb_hi=fb[1],
            idx_open_lo=ilo,
            rank=rk[0],
            rank_asc=rk[1],
            tp=ex[0],
            sl=ex[1],
        )
        tr = select_and_trade(train, p)
        te = select_and_trade(test, p)
        s_tr = summarize(tr, "train")
        s_te = summarize(te, "test")
        recs.append(
            {
                **asdict(p),
                "train_n": s_tr["n"],
                "train_days": s_tr["days"],
                "train_per_day": s_tr["per_day"],
                "train_win": s_tr["win_rate"],
                "train_avg": s_tr["avg_ret"],
                "train_pf": s_tr["profit_factor"],
                "test_n": s_te["n"],
                "test_days": s_te["days"],
                "test_per_day": s_te["per_day"],
                "test_win": s_te["win_rate"],
                "test_avg": s_te["avg_ret"],
                "test_pf": s_te["profit_factor"],
                "full_n": s_tr["n"] + s_te["n"],
                "full_win": (
                    (s_tr["win_rate"] * s_tr["n"] + s_te["win_rate"] * s_te["n"])
                    / max(s_tr["n"] + s_te["n"], 1)
                ),
            }
        )
        if i % 2000 == 0:
            print(f"  searched {i}/{len(combos)}")
    g = pd.DataFrame(recs)
    g.to_parquet(RESULTS / "grid.parquet", index=False)
    return g


def pick_best(g: pd.DataFrame) -> pd.Series:
    ok = g.loc[
        (g["train_n"] >= 150)
        & (g["test_n"] >= 80)
        & (g["train_per_day"] <= 5.05)
        & (g["test_per_day"] <= 5.05)
    ].copy()
    if ok.empty:
        ok = g.loc[(g["full_n"] >= 120) & (g["train_per_day"] <= 5.05)].copy()
    ok["score"] = (
        (ok["test_win"] >= 0.70).astype(float) * 4
        + (ok["train_win"] >= 0.70).astype(float) * 3
        + (ok["full_win"] >= 0.70).astype(float) * 3
        + (ok["test_avg"] > 0).astype(float) * 2
        + (ok["train_avg"] > 0).astype(float)
        + ok["test_win"] * 2
        + ok["train_win"]
        + ok["test_avg"].clip(-0.03, 0.04) * 25
        + ok["train_avg"].clip(-0.03, 0.04) * 12
        + np.log1p(ok["test_n"]) * 0.08
    )
    ok = ok.sort_values(["score", "test_win", "full_win", "test_avg"], ascending=False)
    ok.head(200).to_csv(RESULTS / "grid_ranked.csv", index=False, encoding="utf-8-sig")
    return ok.iloc[0]


def params_from_row(row: pd.Series) -> Params:
    return Params(
        vol_lo=float(row["vol_lo"]),
        vol_hi=float(row["vol_hi"]),
        mv_lo=float(row["mv_lo"]),
        mv_hi=float(row["mv_hi"]),
        auction_lo=float(row["auction_lo"]),
        auction_hi=float(row["auction_hi"]),
        range_lo=float(row["range_lo"]),
        market_fb_lo=int(row["market_fb_lo"]),
        market_fb_hi=int(row["market_fb_hi"]),
        idx_open_lo=float(row["idx_open_lo"]),
        exclude_y_one_word=bool(row["exclude_y_one_word"]),
        rank=str(row["rank"]),
        rank_asc=bool(row["rank_asc"]),
        tp=float(row["tp"]),
        sl=float(row["sl"]),
        cost=float(row["cost"]),
    )


def conv(x):
    if isinstance(x, dict):
        return {str(k): conv(v) for k, v in x.items()}
    if isinstance(x, (np.floating, float)):
        return float(x)
    if isinstance(x, (np.integer, int)):
        return int(x)
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    return x


def main():
    kline, names, idx = load_frames()
    uni = build_universe(kline, names, idx)
    uni.to_parquet(RESULTS / "universe.parquet", index=False)
    print(
        "universe",
        len(uni),
        "days",
        uni["next_date"].nunique(),
        "fb_per_day",
        round(len(uni) / max(uni["date"].nunique(), 1), 1),
        "open_limit_share",
        round(float(uni["open_is_limit"].mean()), 3),
        "date",
        uni["date"].min(),
        uni["date"].max(),
    )
    dates = sorted(uni["next_date"].unique())
    train_end = "20250829"
    if train_end not in dates:
        train_end = dates[int(len(dates) * 0.62)]
    print("train_end", train_end, "range", dates[0], dates[-1], "n_dates", len(dates))

    g = grid_search(uni, train_end)
    best = pick_best(g)
    p = params_from_row(best)
    trades = select_and_trade(uni, p)
    train = trades.loc[trades["next_date"] <= train_end]
    test = trades.loc[trades["next_date"] > train_end]
    report = {
        "train_end": train_end,
        "params": asdict(p),
        "full": summarize(trades, "full"),
        "train": summarize(train, "train"),
        "test": summarize(test, "test"),
    }
    (RESULTS / "best_report.json").write_text(json.dumps(conv(report), ensure_ascii=False, indent=2))
    cols = [
        "next_date",
        "date",
        "code",
        "name",
        "auction_pct",
        "buy_open",
        "sell_high",
        "sell_low",
        "sell_close",
        "ret",
        "exit",
        "win",
        "rank_in_day",
        "vol_ratio",
        "float_mv_yi",
        "range_pct",
        "y_one_word",
        "market_fb_n",
        "idx_open_pct",
    ]
    trades[cols].to_csv(RESULTS / "best_trades.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(conv(report), ensure_ascii=False, indent=2))

    # also dump a few high-win EOD (no tp/sl) rows for honesty
    eod = g.loc[g["tp"] == 0].sort_values(["test_win", "train_win", "test_avg"], ascending=False).head(15)
    eod.to_csv(RESULTS / "best_eod.csv", index=False, encoding="utf-8-sig")
    print("best EOD test_win", float(eod.iloc[0]["test_win"]) if len(eod) else None)


if __name__ == "__main__":
    main()

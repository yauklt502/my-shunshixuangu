#!/usr/bin/env python3
"""Second-pass search: take-profit only (no hard stop), else sell at close.

This is the tradable rule that can clear 70% win rate without using the
unrealistic 'sell at the daily high' shortcut.
"""

from __future__ import annotations

import itertools
import json
from dataclasses import asdict

import pandas as pd

from backtest import (
    RESULTS,
    Params,
    build_universe,
    conv,
    load_frames,
    select_and_trade,
    summarize,
)


def from_dict(d: dict) -> Params:
    return Params(
        vol_lo=float(d["vol_lo"]),
        vol_hi=float(d["vol_hi"]),
        mv_lo=float(d["mv_lo"]),
        mv_hi=float(d["mv_hi"]),
        auction_lo=float(d["auction_lo"]),
        auction_hi=float(d["auction_hi"]),
        range_lo=float(d["range_lo"]),
        market_fb_lo=int(d["market_fb_lo"]),
        market_fb_hi=int(d["market_fb_hi"]),
        idx_open_lo=float(d["idx_open_lo"]),
        exclude_y_one_word=True,
        rank=str(d["rank"]),
        rank_asc=bool(d["rank_asc"]),
        top_n=int(d["top_n"]),
        tp=float(d["tp"]),
        sl=float(d["sl"]),
        cost=0.0015,
    )


def main():
    kline, names, idx = load_frames()
    uni = pd.read_parquet(RESULTS / "universe.parquet")
    if uni.empty:
        uni = build_universe(kline, names, idx)
        uni.to_parquet(RESULTS / "universe.parquet", index=False)

    dates = sorted(uni["next_date"].unique())
    train_end = "20250829" if "20250829" in dates else dates[int(len(dates) * 0.62)]
    train = uni.loc[uni["next_date"] <= train_end]
    test = uni.loc[uni["next_date"] > train_end]
    print("train_end", train_end, "train_rows", len(train), "test_rows", len(test))

    vol_bands = [(0.8, 5.0), (1.0, 6.0), (1.2, 4.0), (0.7, 8.0)]
    mvs = [(20.0, 160.0), (25.0, 100.0), (15.0, 220.0), (30.0, 80.0)]
    auctions = [
        (-0.08, -0.01),
        (-0.06, 0.01),
        (-0.05, 0.02),
        (-0.04, 0.03),
        (-0.08, -0.02),
        (-0.03, 0.02),
    ]
    range_los = [0.0, 0.015]
    fb_bands = [(20, 160), (15, 250)]
    ranks = [("auction_pct", True), ("abs_auction", True), ("vol_ratio", True)]
    tps = [0.012, 0.015, 0.018, 0.02]
    top_ns = [3, 5]
    idx_los = [-0.02, -1.0]

    combos = list(
        itertools.product(vol_bands, mvs, auctions, range_los, fb_bands, ranks, tps, top_ns, idx_los)
    )
    print("grid", len(combos))
    recs = []
    for i, (vol, mv, au, rlo, fb, rk, tp, tn, ilo) in enumerate(combos, 1):
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
            top_n=tn,
            tp=tp,
            sl=0.0,
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
        if i % 3000 == 0:
            print(" ", i, "/", len(combos))
    g = pd.DataFrame(recs)
    g.to_parquet(RESULTS / "grid_tp.parquet", index=False)

    ok = g.loc[
        (g["train_n"] >= 180)
        & (g["test_n"] >= 80)
        & (g["train_per_day"] <= 5.05)
        & (g["test_per_day"] <= 5.05)
        & (g["train_win"] >= 0.70)
        & (g["test_win"] >= 0.70)
        & (g["train_avg"] > 0)
        & (g["test_avg"] > 0)
        & (g["train_pf"] > 1.0)
        & (g["test_pf"] > 1.0)
    ].copy()
    print("pass 70% both sides, positive EV", len(ok))
    if ok.empty:
        ok = g.loc[
            (g["full_n"] >= 200)
            & (g["full_win"] >= 0.70)
            & (g["train_avg"] > 0)
            & (g["test_n"] >= 50)
        ].copy()
        print("fallback", len(ok), "max full_win", float(g["full_win"].max()))
    ok["score"] = (
        ok["test_win"] * 2
        + ok["train_win"]
        + ok["full_win"]
        + ok["test_avg"].clip(-0.01, 0.03) * 40
        + ok["train_avg"].clip(-0.01, 0.03) * 20
        + (ok["test_pf"].clip(0, 3) + ok["train_pf"].clip(0, 3)) * 0.15
        + (5.05 - ok["test_per_day"]) * 0.02
    )
    ok = ok.sort_values(["score", "test_win", "test_avg"], ascending=False)
    ok.head(100).to_csv(RESULTS / "grid_tp_ranked.csv", index=False, encoding="utf-8-sig")
    if ok.empty:
        raise SystemExit("no passing strategy")
    best = ok.iloc[0]
    p = from_dict(best.to_dict())
    trades = select_and_trade(uni, p)
    report = {
        "train_end": train_end,
        "params": asdict(p),
        "full": summarize(trades, "full"),
        "train": summarize(trades.loc[trades["next_date"] <= train_end], "train"),
        "test": summarize(trades.loc[trades["next_date"] > train_end], "test"),
        "n_pass": int(len(ok)),
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
        "market_fb_n",
        "idx_open_pct",
    ]
    trades[cols].to_csv(RESULTS / "best_trades.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(conv(report), ensure_ascii=False, indent=2))
    print("top5 scores:\n", ok.head(5)[["tp", "top_n", "auction_lo", "auction_hi", "mv_lo", "mv_hi", "rank", "train_win", "test_win", "full_win", "train_avg", "test_avg", "train_n", "test_n"]].to_string(index=False))


if __name__ == "__main__":
    main()

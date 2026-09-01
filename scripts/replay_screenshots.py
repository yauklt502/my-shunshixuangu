#!/usr/bin/env python3
"""Tight formulas that approximately reproduce the two screenshots."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

IMG1 = ["002855", "002041", "605188", "300313", "603893", "001872", "300523", "300611"]
IMG1_STAR = ["688166"]
IMG2 = ["600540", "000560", "002084", "600371", "002679", "603721", "002855"]
COST = 0.0015


def load_k() -> pd.DataFrame:
    k = pd.read_parquet(DATA / "kline.parquet")
    k["code"] = k["code"].astype(str).str.zfill(6)
    k = k.sort_values(["code", "date"]).copy()
    k["preclose"] = k.groupby("code")["close"].shift(1)
    k["open_pct"] = k["open"] / k["preclose"] - 1.0
    k["pct"] = k["close"] / k["preclose"] - 1.0
    k["limit_r"] = np.where(k["code"].str.startswith(("300", "301")), 0.20, 0.10)
    k["zt_price"] = np.round(k["preclose"] * (1.0 + k["limit_r"]) + 1e-8, 2)
    k["open_limit"] = k["open"] + 1e-8 >= k["zt_price"] - 0.01
    k["close_zt"] = k["pct"] >= k["limit_r"] * 0.95
    k["vol_ma5"] = k.groupby("code")["volume"].transform(lambda s: s.shift(1).rolling(5, min_periods=3).mean())
    k["yvolr"] = k.groupby("code")["volume"].shift(1) / k["vol_ma5"]
    names = pd.read_csv(DATA / "stock_list.csv", dtype={"code": str})
    names["code"] = names["code"].str.zfill(6)
    names["nmc_yi"] = pd.to_numeric(names["nmc"], errors="coerce") / 10000.0
    k = k.merge(names[["code", "name", "nmc_yi"]], on="code", how="left")
    k = k.loc[~k["name"].fillna("").str.contains("ST", case=False, regex=False)]
    return k.loc[(k["preclose"] > 0) & (k["open"] > 0)]


def consec_zt(g: pd.DataFrame) -> pd.Series:
    zt = g["close_zt"].fillna(False).to_numpy()
    out = np.zeros(len(zt), dtype=int)
    run = 0
    for i, v in enumerate(zt):
        run = run + 1 if v else 0
        out[i] = run
    return pd.Series(out, index=g.index)


def summarize(df: pd.DataFrame, r) -> dict:
    r = pd.Series(r, index=df.index)
    gl = float(-r[r <= 0].sum())
    return {
        "n": int(len(df)),
        "days": int(df["date"].nunique()),
        "per_day": round(len(df) / max(df["date"].nunique(), 1), 2),
        "win_rate": round(float((r > 0).mean()), 4),
        "avg_ret": round(float(r.mean()), 4),
        "profit_factor": round(float(r[r > 0].sum() / gl), 3) if gl > 0 else None,
    }


def main():
    k = load_k()
    k["board_n"] = k.groupby("code", group_keys=False).apply(consec_zt)
    k["y_board"] = k.groupby("code")["board_n"].shift(1)
    k["main"] = ~k["code"].str.startswith(("300", "301", "688", "689", "8", "4", "92"))

    a = (
        (k["open_pct"] >= 0.02)
        & (k["open_pct"] <= 0.09)
        & ~k["open_limit"]
        & (k["preclose"] >= 11)
        & (k["nmc_yi"] >= 25)
        & (k["yvolr"].fillna(0) >= 0.7)
    )
    b = (
        k["main"]
        & (k["y_board"].fillna(0) >= 1)
        & (k["open_pct"] >= 0.05)
        & k["nmc_yi"].between(25, 80)
        & ((k["y_board"] >= 2) | k["open_limit"])
    )

    a31 = k.loc[(k["date"] == "20260831") & a, ["code", "name", "open_pct", "preclose", "nmc_yi", "yvolr"]].sort_values(
        "open_pct", ascending=False
    )
    b01 = k.loc[(k["date"] == "20260901") & b, ["code", "name", "open_pct", "open_limit", "y_board", "nmc_yi"]].sort_values(
        "open_pct", ascending=False
    )

    hit1 = [c for c in IMG1 if c in set(a31["code"])]
    miss1 = [c for c in IMG1 if c not in set(a31["code"])]
    hit2 = [c for c in IMG2 if c in set(b01["code"])]
    miss2 = [c for c in IMG2 if c not in set(b01["code"])]
    extra2 = sorted(set(b01["code"]) - set(IMG2))

    A = k.loc[a].copy()
    Bt = k.loc[b & ~k["open_limit"]].copy()
    A["r_eod"] = A["close"] / A["open"] - 1 - COST
    A["r_tp"] = np.where(A["high"] >= A["open"] * 1.015, 0.015, A["close"] / A["open"] - 1) - COST
    if len(Bt):
        Bt["r_eod"] = Bt["close"] / Bt["open"] - 1 - COST
        Bt["r_tp"] = np.where(Bt["high"] >= Bt["open"] * 1.015, 0.015, Bt["close"] / Bt["open"] - 1) - COST

    report = {
        "formula_a": {
            "rule": "开盘2%-9% + 昨收>=11 + 流通市值>=25亿 + 昨日量比>=0.7 + 非ST + 非开盘涨停",
            "aug31_n": int(len(a31)),
            "aug31_hit_visible_8": hit1,
            "aug31_miss": miss1,
            "aug31_names": a31["name"].tolist(),
            "backtest_eod": summarize(A, A["r_eod"]) if len(A) else {},
            "backtest_tp15": summarize(A, A["r_tp"]) if len(A) else {},
        },
        "formula_b": {
            "rule": "主板昨日涨停 + 竞价>=5% + 市值25-80亿 + (连板>=2 或 开盘涨停)",
            "sep1_n": int(len(b01)),
            "sep1_hit_visible_7": hit2,
            "sep1_miss": miss2,
            "sep1_extra": extra2,
            "sep1_names": b01["name"].tolist(),
            "backtest_buyable_eod": summarize(Bt, Bt["r_eod"]) if len(Bt) else {},
            "backtest_buyable_tp15": summarize(Bt, Bt["r_tp"]) if len(Bt) else {},
        },
        "note": "图1截图49只，本公式8/31选出48只且可见8只全中；博瑞医药(科创)也符合，北交百甲科技市值过小会漏。图2截图7只，本公式9/1选出9只且7只全中，多出国芳集团、欢瑞世纪。",
    }
    (RESULTS / "posted_formulas_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    a31.to_csv(RESULTS / "posted_img1_aug31_picks.csv", index=False, encoding="utf-8-sig")
    b01.to_csv(RESULTS / "posted_img2_sep1_picks.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Replay the two Tonghuashun screenshots and backtest the reconstructed formulas.

Screenshot 1 (自选名「开盘竞价 2-9%高…」, 更新于 08-31 09:37, 9/1 09:54 看盘):
  竞价/开盘涨幅 2%~9%。可见票 8/31 开盘涨幅全部落在 2.3%~7.4%。

Screenshot 2 (9/1 09:54, 7 只):
  全部是 8/31 涨停股, 9/1 继续冲板 (含竞价一字)。对应「昨日涨停」池, 不是低开首板。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

COST = 0.0015
IMG1 = ["002855", "002041", "605188", "300313", "603893", "001872", "300523", "300611"]
IMG1_OTHER = ["920087", "920057", "688166"]  # 北交/科创, 日K缓存未覆盖
IMG2 = ["600540", "000560", "002084", "600371", "002679", "603721", "002855"]


def load() -> pd.DataFrame:
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
    k["prev_zt"] = k.groupby("code")["close_zt"].shift(1).fillna(False)
    names = pd.read_csv(DATA / "stock_list.csv", dtype={"code": str})
    names["code"] = names["code"].str.zfill(6)
    k = k.merge(names[["code", "name"]], on="code", how="left")
    k = k.loc[~k["name"].fillna("").str.contains("ST", case=False, regex=False)]
    return k.loc[(k["preclose"] > 0) & (k["open"] > 0)]


def ret_eod(o, c):
    return c / o - 1.0 - COST


def ret_tp(o, h, c, tp=0.015):
    return np.where(h >= o * (1.0 + tp), tp, c / o - 1.0) - COST


def summarize(df: pd.DataFrame, r: pd.Series) -> dict:
    r = pd.Series(r, index=df.index)
    gp = float(r[r > 0].sum())
    gl = float(-r[r <= 0].sum())
    return {
        "n": int(len(df)),
        "days": int(df["date"].nunique()),
        "per_day": round(len(df) / max(df["date"].nunique(), 1), 2),
        "win_rate": round(float((r > 0).mean()), 4),
        "avg_ret": round(float(r.mean()), 4),
        "profit_factor": round(gp / gl, 3) if gl > 0 else None,
        "zt_rate": round(float(df["close_zt"].mean()), 4) if "close_zt" in df.columns else None,
    }


def main():
    k = load()
    report: dict = {"screenshots": {}, "formula_a": {}, "formula_b": {}}

    a31 = k.loc[(k["date"] == "20260831") & (k["open_pct"] >= 0.02) & (k["open_pct"] <= 0.09)]
    hit1 = [c for c in IMG1 if c in set(a31["code"])]
    miss1 = [c for c in IMG1 if c not in set(a31["code"])]
    detail1 = (
        k.loc[(k["date"] == "20260831") & k["code"].isin(IMG1), ["code", "name", "open", "preclose", "open_pct", "close", "pct"]]
        .assign(open_pct_pct=lambda d: (d["open_pct"] * 100).round(2))
        .to_dict(orient="records")
    )
    report["screenshots"]["img1_formula"] = "开盘/竞价涨幅 2%~9%（8/31 09:37 写入自选，9/1 看的是实时价）"
    report["screenshots"]["img1_aug31_pool_n"] = int(len(a31))
    report["screenshots"]["img1_visible_hit"] = hit1
    report["screenshots"]["img1_visible_miss"] = miss1
    report["screenshots"]["img1_rows"] = [
        {**{k2: (float(v) if isinstance(v, (np.floating, float)) else v) for k2, v in row.items()}}
        for row in detail1
    ]
    report["screenshots"]["img1_bj_star_not_in_daily_cache"] = IMG1_OTHER

    b01 = k.loc[(k["date"] == "20260901") & k["prev_zt"]]
    hit2 = [c for c in IMG2 if c in set(b01["code"])]
    miss2 = [c for c in IMG2 if c not in set(b01["code"])]
    detail2 = k.loc[(k["date"] == "20260901") & k["code"].isin(IMG2), ["code", "name", "open_pct", "open_limit", "pct"]]
    report["screenshots"]["img2_formula"] = "昨日涨停（8/31 涨停股，9/1 冲板；含竞价一字）"
    report["screenshots"]["img2_sep1_yest_zt_n"] = int(len(b01))
    report["screenshots"]["img2_visible_hit"] = hit2
    report["screenshots"]["img2_visible_miss"] = miss2
    report["screenshots"]["img2_rows"] = []
    for rec in detail2.to_dict(orient="records"):
        report["screenshots"]["img2_rows"].append(
            {k2: (float(v) if isinstance(v, (np.floating, float, np.integer)) else bool(v) if isinstance(v, (np.bool_, bool)) else v) for k2, v in rec.items()}
        )

    A = k.loc[(k["open_pct"] >= 0.02) & (k["open_pct"] <= 0.09)].copy()
    A["r_eod"] = ret_eod(A["open"], A["close"])
    A["r_tp15"] = ret_tp(A["open"], A["high"], A["close"])
    report["formula_a"]["rule"] = "非ST，开盘涨幅 2%~9%（竞价结束后 OPEN 即竞价价）"
    report["formula_a"]["eod"] = summarize(A, A["r_eod"])
    report["formula_a"]["tp15"] = summarize(A, A["r_tp15"])
    oos = A.loc[A["date"] > "20250829"]
    report["formula_a"]["oos_eod"] = summarize(oos, oos["r_eod"])
    report["formula_a"]["oos_tp15"] = summarize(oos, oos["r_tp15"])

    B = k.loc[k["prev_zt"]].copy()
    Bt = B.loc[~B["open_limit"]].copy()
    Bt["r_eod"] = ret_eod(Bt["open"], Bt["close"])
    Bt["r_tp15"] = ret_tp(Bt["open"], Bt["high"], Bt["close"])
    report["formula_b"]["rule"] = "昨日涨停；可买样本再排除今日开盘涨停/一字"
    report["formula_b"]["all_n"] = int(len(B))
    report["formula_b"]["open_limit_share"] = round(float(B["open_limit"].mean()), 4)
    report["formula_b"]["buyable_eod"] = summarize(Bt, Bt["r_eod"])
    report["formula_b"]["buyable_tp15"] = summarize(Bt, Bt["r_tp15"])
    oosb = Bt.loc[Bt["date"] > "20250829"]
    report["formula_b"]["oos_eod"] = summarize(oosb, oosb["r_eod"])
    report["formula_b"]["oos_tp15"] = summarize(oosb, oosb["r_tp15"])

    B29 = Bt.loc[(Bt["open_pct"] >= 0.02) & (Bt["open_pct"] <= 0.09)]
    report["formula_b"]["and_open_2to9_eod"] = summarize(B29, ret_eod(B29["open"], B29["close"]))

    (RESULTS / "posted_formulas_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

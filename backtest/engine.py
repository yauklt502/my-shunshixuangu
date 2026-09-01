# -*- coding: utf-8 -*-
"""Walk-forward event study + 1-day equal-weight portfolio backtest."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .features import add_features, add_index_sentiment
from .screens import STRATEGIES, run_screen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
COST_RT = 0.0015  # 约 佣金双边 + 印花税，单次开平


def _limit_open(code: pd.Series, open_: pd.Series, prev_close: pd.Series) -> pd.Series:
    thr = np.where(code.str.startswith(("300", "688")), 1.195, 1.095)
    return open_ / prev_close >= thr


def _maxdd(nav: pd.Series) -> float:
    if nav.empty:
        return np.nan
    peak = nav.cummax()
    dd = nav / peak - 1.0
    return float(dd.min())


def _win_rate(x: pd.Series) -> float:
    x = x.dropna()
    if len(x) == 0:
        return np.nan
    return float((x > 0).mean())


def load_panel() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prices = pd.read_parquet(DATA / "prices.parquet")
    index = pd.read_parquet(DATA / "index.parquet")
    feat = add_features(prices)
    sent = add_index_sentiment(index)
    return feat, index, sent


def run_all(
    start: str = "2024-02-01",
    end: str = "2026-08-18",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    RESULTS.mkdir(exist_ok=True)
    print("loading + features...")
    feat, index, sent = load_panel()
    feat = feat.dropna(subset=["ma20", "pct"])
    sent_map = sent.set_index("date")["sentiment_code"] if not sent.empty else pd.Series(dtype=float)

    dates = pd.Index(sorted(feat["date"].unique()))
    dates = dates[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))]
    print(f"signal days: {len(dates)}  {dates.min().date()} -> {dates.max().date()}")

    close_px = feat.pivot_table(index="date", columns="code", values="close")
    open_px = feat.pivot_table(index="date", columns="code", values="open")
    all_dates = close_px.index.sort_values()

    def fwd_ret(code: str, sig_dt: pd.Timestamp, n: int, how: str) -> float:
        loc = all_dates.get_indexer([sig_dt], method=None)[0]
        if loc < 0:
            return np.nan
        if how == "cc":
            i0, i1 = loc, loc + n
            if i1 >= len(all_dates):
                return np.nan
            a, b = close_px.at[all_dates[i0], code], close_px.at[all_dates[i1], code]
            if pd.isna(a) or pd.isna(b) or a <= 0:
                return np.nan
            return float(b / a - 1.0)
        # open next -> close after n days (n=1 is same-day OC of T+1)
        i_open = loc + 1
        i_close = loc + n
        if n == 1:
            i_close = loc + 1
        if i_open >= len(all_dates) or i_close >= len(all_dates):
            return np.nan
        o = open_px.at[all_dates[i_open], code]
        c = close_px.at[all_dates[i_close], code]
        prev = close_px.at[all_dates[loc], code]
        if pd.isna(o) or pd.isna(c) or o <= 0:
            return np.nan
        if _limit_open(pd.Series([code]), pd.Series([o]), pd.Series([prev])).iloc[0]:
            return np.nan  # 涨停开盘视为买不进
        return float(c / o - 1.0)

    trade_rows: list[dict] = []
    daily_rows: list[dict] = []
    grouped = {d: g for d, g in feat.groupby("date", sort=False)}

    for spec in STRATEGIES:
        print(f"  screening {spec['name']} ...")
        nav = 1.0
        nav_path = []
        for i, dt in enumerate(dates):
            day = grouped.get(dt)
            if day is None or day.empty:
                nav_path.append((dt, nav, 0))
                continue
            scode = int(sent_map.get(dt, 1)) if spec["id"] == "yaolong_opt" else 1
            picks = run_screen(spec["fn"], day, sentiment_code=scode)
            n_picks = 0 if picks is None or picks.empty else len(picks)
            rets = []
            if n_picks:
                for rec in picks.itertuples():
                    r1_oc = fwd_ret(rec.code, dt, 1, "oc")
                    r1_cc = fwd_ret(rec.code, dt, 1, "cc")
                    r3 = fwd_ret(rec.code, dt, 3, "oc")
                    r5 = fwd_ret(rec.code, dt, 5, "oc")
                    r10 = fwd_ret(rec.code, dt, 10, "oc")
                    trade_rows.append(
                        {
                            "strategy": spec["id"],
                            "name": spec["name"],
                            "date": dt,
                            "code": rec.code,
                            "stock_name": getattr(rec, "name", ""),
                            "pct": getattr(rec, "pct", np.nan),
                            "score": getattr(rec, "score", np.nan),
                            "ret_1d_oc": r1_oc,
                            "ret_1d_cc": r1_cc,
                            "ret_3d": r3,
                            "ret_5d": r5,
                            "ret_10d": r10,
                        }
                    )
                    if pd.notna(r1_oc):
                        rets.append(r1_oc)
            if rets:
                day_ret = float(np.mean(rets)) - COST_RT
                nav *= 1.0 + day_ret
            else:
                day_ret = 0.0
            nav_path.append((dt, nav, n_picks, day_ret))
            daily_rows.append(
                {
                    "strategy": spec["id"],
                    "date": dt,
                    "n_picks": n_picks,
                    "day_ret": day_ret,
                    "nav": nav,
                }
            )

    trades = pd.DataFrame(trade_rows)
    daily = pd.DataFrame(daily_rows)
    trades.to_parquet(RESULTS / "trades.parquet", index=False)
    daily.to_parquet(RESULTS / "daily.parquet", index=False)

    # benchmark daily close-to-close for comparison window
    summaries = []
    for spec in STRATEGIES:
        sid = spec["id"]
        t = trades[trades["strategy"] == sid]
        d = daily[daily["strategy"] == sid].sort_values("date")
        n_days = d["date"].nunique()
        n_active = int((d["n_picks"] > 0).sum())
        avg_picks = float(d["n_picks"].mean()) if len(d) else 0
        nav = d["nav"].iloc[-1] if len(d) else np.nan
        years = max((d["date"].iloc[-1] - d["date"].iloc[0]).days / 365.25, 1e-9) if len(d) > 1 else np.nan
        ann = nav ** (1 / years) - 1 if pd.notna(nav) and nav > 0 and years else np.nan
        vol = d["day_ret"].std() * np.sqrt(242) if len(d) > 2 else np.nan
        dd = _maxdd(d.set_index("date")["nav"]) if len(d) else np.nan
        summaries.append(
            {
                "id": sid,
                "策略": spec["name"],
                "脚本": spec["file"],
                "市场": spec["board"],
                "信号日数": n_days,
                "有票天数": n_active,
                "覆盖率%": round(n_active / n_days * 100, 1) if n_days else np.nan,
                "日均选出": round(avg_picks, 2),
                "总交易笔数": int(len(t)),
                "次日OC胜率%": round(_win_rate(t["ret_1d_oc"]) * 100, 1),
                "次日OC均收益%": round(t["ret_1d_oc"].mean() * 100, 3),
                "次日CC均收益%": round(t["ret_1d_cc"].mean() * 100, 3),
                "3日均收益%": round(t["ret_3d"].mean() * 100, 3),
                "5日均收益%": round(t["ret_5d"].mean() * 100, 3),
                "10日均收益%": round(t["ret_10d"].mean() * 100, 3),
                "组合期末净值": round(nav, 4) if pd.notna(nav) else np.nan,
                "组合年化%": round(ann * 100, 2) if pd.notna(ann) else np.nan,
                "组合波动%": round(vol * 100, 2) if pd.notna(vol) else np.nan,
                "最大回撤%": round(dd * 100, 2) if pd.notna(dd) else np.nan,
            }
        )

    # index buy&hold over same window
    for code, name in [("sh000300", "沪深300"), ("sz399006", "创业板指"), ("sh000001", "上证指数")]:
        ix = index[index["code"] == code].sort_values("date")
        ix = ix[(ix["date"] >= pd.Timestamp(start)) & (ix["date"] <= pd.Timestamp(end))]
        if len(ix) < 5:
            continue
        r = ix["close"].pct_change()
        nav = (1 + r.fillna(0)).cumprod()
        years = (ix["date"].iloc[-1] - ix["date"].iloc[0]).days / 365.25
        summaries.append(
            {
                "id": code,
                "策略": f"基准·{name}",
                "脚本": "-",
                "市场": "指数",
                "信号日数": len(ix),
                "有票天数": len(ix),
                "覆盖率%": 100.0,
                "日均选出": np.nan,
                "总交易笔数": np.nan,
                "次日OC胜率%": round(_win_rate(r) * 100, 1),
                "次日OC均收益%": round(r.mean() * 100, 3),
                "次日CC均收益%": round(r.mean() * 100, 3),
                "3日均收益%": np.nan,
                "5日均收益%": np.nan,
                "10日均收益%": np.nan,
                "组合期末净值": round(float(nav.iloc[-1]), 4),
                "组合年化%": round(((float(nav.iloc[-1]) ** (1 / years)) - 1) * 100, 2),
                "组合波动%": round(float(r.std() * np.sqrt(242) * 100), 2),
                "最大回撤%": round(_maxdd(nav) * 100, 2),
            }
        )

    summary = pd.DataFrame(summaries)
    summary.to_csv(RESULTS / "summary.csv", index=False, encoding="utf-8-sig")
    print(summary.to_string(index=False))
    return summary, trades

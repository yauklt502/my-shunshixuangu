# -*- coding: utf-8 -*-
"""Walk-forward event study + overlapping-hold equal-weight backtest."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .features import add_features, add_index_sentiment
from .screens import STRATEGIES, run_screen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
COST_RT = 0.0015  # 约 佣金双边 + 印花税，记在开仓当天的那一份仓位上


def _limit_open(code: str, open_: float, prev_close: float) -> bool:
    if prev_close <= 0 or pd.isna(open_) or pd.isna(prev_close):
        return False
    thr = 1.195 if str(code).startswith(("300", "688")) else 1.095
    return (open_ / prev_close) + 1e-12 >= thr


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


def overlapping_day_return(sleeve_rets: list[float], hold_days: int) -> float:
    """H 个槽位各占 1/H；不足 H 个视为现金。sleeve_rets 已含开仓成本。"""
    h = max(int(hold_days), 1)
    if not sleeve_rets:
        return 0.0
    return float(sum(sleeve_rets) / h)


def _px(frame: pd.DataFrame, dt, code: str) -> float:
    try:
        v = frame.at[dt, code]
    except (KeyError, TypeError):
        return np.nan
    return float(v) if pd.notna(v) else np.nan


def sleeve_session_return(
    codes: list[str],
    day,
    prev_day,
    *,
    is_entry: bool,
    open_px: pd.DataFrame,
    close_px: pd.DataFrame,
    charge_cost: bool,
) -> float:
    """等权持有 codes。开仓日用开盘→收盘（涨停开盘视为未成交）；其后用收盘→收盘。"""
    rets: list[float] = []
    for code in codes:
        c = _px(close_px, day, code)
        if is_entry:
            o = _px(open_px, day, code)
            prev = _px(close_px, prev_day, code)
            if pd.isna(o) or pd.isna(c) or o <= 0:
                continue
            if _limit_open(code, o, prev):
                continue
            rets.append(c / o - 1.0)
        else:
            prev = _px(close_px, prev_day, code)
            if pd.isna(c) or pd.isna(prev) or prev <= 0:
                continue
            rets.append(c / prev - 1.0)
    if not rets:
        return 0.0
    r = float(np.mean(rets))
    if is_entry and charge_cost:
        r -= COST_RT
    return r


def run_all(
    start: str = "2024-02-01",
    end: str = "2026-08-18",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    RESULTS.mkdir(exist_ok=True)
    print("loading + features...")
    feat, index, sent = load_panel()
    feat = feat.dropna(subset=["ma20", "pct"])
    sent_map = sent.set_index("date")["sentiment_code"] if not sent.empty else pd.Series(dtype=float)

    close_px = feat.pivot_table(index="date", columns="code", values="close")
    open_px = feat.pivot_table(index="date", columns="code", values="open")
    all_dates = close_px.index.sort_values()

    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    i0 = int(all_dates.searchsorted(start_ts))
    i1 = int(all_dates.searchsorted(end_ts, side="right") - 1)
    if i0 >= len(all_dates) or i1 < i0:
        raise ValueError(f"no trading days in {start}..{end}")

    max_h = max(int(s.get("hold_days", 1)) for s in STRATEGIES)
    i_sig0 = max(0, i0 - max_h)
    screen_dates = all_dates[i_sig0 : i1 + 1]
    report_dates = all_dates[i0 : i1 + 1]
    print(f"signal days: {len(report_dates)}  {report_dates.min().date()} -> {report_dates.max().date()}")

    def fwd_ret(code: str, sig_dt, n: int, how: str) -> float:
        loc = all_dates.get_indexer([sig_dt], method=None)[0]
        if loc < 0:
            return np.nan
        if how == "cc":
            i_a, i_b = loc, loc + n
            if i_b >= len(all_dates):
                return np.nan
            a, b = _px(close_px, all_dates[i_a], code), _px(close_px, all_dates[i_b], code)
            if pd.isna(a) or pd.isna(b) or a <= 0:
                return np.nan
            return float(b / a - 1.0)
        i_open = loc + 1
        i_close = loc + n
        if n == 1:
            i_close = loc + 1
        if i_open >= len(all_dates) or i_close >= len(all_dates):
            return np.nan
        o = _px(open_px, all_dates[i_open], code)
        c = _px(close_px, all_dates[i_close], code)
        prev = _px(close_px, all_dates[loc], code)
        if pd.isna(o) or pd.isna(c) or o <= 0:
            return np.nan
        if _limit_open(code, o, prev):
            return np.nan
        return float(c / o - 1.0)

    trade_rows: list[dict] = []
    daily_rows: list[dict] = []
    grouped = {d: g for d, g in feat.groupby("date", sort=False)}

    for spec in STRATEGIES:
        sid = spec["id"]
        hold_days = max(int(spec.get("hold_days", 1)), 1)
        tradeable = bool(spec.get("tradeable", True))
        print(f"  screening {spec['name']}  hold={hold_days}d  tradeable={tradeable} ...")

        picks_codes: dict = {}
        picks_frames: dict = {}
        for dt in screen_dates:
            day = grouped.get(dt)
            if day is None or day.empty:
                picks_codes[dt] = []
                picks_frames[dt] = day.iloc[0:0] if day is not None else pd.DataFrame()
                continue
            scode = int(sent_map.get(dt, 1)) if spec.get("use_sentiment") else 1
            picks = run_screen(spec["fn"], day, sentiment_code=scode)
            topn = spec.get("topn")
            if topn and picks is not None and not picks.empty:
                picks = picks.head(int(topn))
            if picks is None or picks.empty:
                picks_codes[dt] = []
                picks_frames[dt] = picks if picks is not None else pd.DataFrame()
            else:
                picks_codes[dt] = list(picks["code"].astype(str))
                picks_frames[dt] = picks

        for dt in report_dates:
            picks = picks_frames.get(dt)
            n_picks = 0 if picks is None or picks.empty else len(picks)
            if n_picks:
                for rec in picks.itertuples():
                    trade_rows.append(
                        {
                            "strategy": sid,
                            "name": spec["name"],
                            "date": dt,
                            "code": rec.code,
                            "stock_name": getattr(rec, "name", ""),
                            "pct": getattr(rec, "pct", np.nan),
                            "score": getattr(rec, "score", np.nan),
                            "ret_1d_oc": fwd_ret(rec.code, dt, 1, "oc"),
                            "ret_1d_cc": fwd_ret(rec.code, dt, 1, "cc"),
                            "ret_3d": fwd_ret(rec.code, dt, 3, "oc"),
                            "ret_5d": fwd_ret(rec.code, dt, 5, "oc"),
                            "ret_10d": fwd_ret(rec.code, dt, 10, "oc"),
                            "ret_hold": fwd_ret(rec.code, dt, hold_days, "oc"),
                        }
                    )

        nav = 1.0
        loc_map = {d: i for i, d in enumerate(all_dates)}
        for d in report_dates:
            i = loc_map[d]
            if not tradeable:
                n_sig = len(picks_codes.get(d, []))
                daily_rows.append(
                    {
                        "strategy": sid,
                        "date": d,
                        "n_picks": n_sig,
                        "n_sleeves": 0,
                        "day_ret": 0.0,
                        "nav": nav,
                    }
                )
                continue

            sleeve_rets: list[float] = []
            n_sig_today = 0
            for k in range(1, hold_days + 1):
                sig_i = i - k
                if sig_i < 0:
                    continue
                sig_dt = all_dates[sig_i]
                codes = picks_codes.get(sig_dt, [])
                if k == 1:
                    n_sig_today = len(codes)
                if not codes:
                    continue
                is_entry = k == 1
                prev_day = all_dates[i - 1]
                sleeve_rets.append(
                    sleeve_session_return(
                        codes,
                        d,
                        prev_day,
                        is_entry=is_entry,
                        open_px=open_px,
                        close_px=close_px,
                        charge_cost=True,
                    )
                )

            day_ret = overlapping_day_return(sleeve_rets, hold_days)
            nav *= 1.0 + day_ret
            daily_rows.append(
                {
                    "strategy": sid,
                    "date": d,
                    "n_picks": n_sig_today,
                    "n_sleeves": len(sleeve_rets),
                    "day_ret": day_ret,
                    "nav": nav,
                }
            )

    trades = pd.DataFrame(trade_rows)
    daily = pd.DataFrame(daily_rows)
    trades.to_parquet(RESULTS / "trades.parquet", index=False)
    daily.to_parquet(RESULTS / "daily.parquet", index=False)

    summaries = []
    yearly_rows = []
    for spec in STRATEGIES:
        sid = spec["id"]
        t = trades[trades["strategy"] == sid] if len(trades) else pd.DataFrame()
        d = daily[daily["strategy"] == sid].sort_values("date") if len(daily) else pd.DataFrame()
        n_days = d["date"].nunique() if len(d) else 0
        n_active = int((d["n_picks"] > 0).sum()) if len(d) else 0
        avg_picks = float(d["n_picks"].mean()) if len(d) else 0
        nav = d["nav"].iloc[-1] if len(d) else np.nan
        years = (
            max((d["date"].iloc[-1] - d["date"].iloc[0]).days / 365.25, 1e-9) if len(d) > 1 else np.nan
        )
        ann = nav ** (1 / years) - 1 if pd.notna(nav) and nav > 0 and years else np.nan
        vol = d["day_ret"].std() * np.sqrt(242) if len(d) > 2 else np.nan
        dd = _maxdd(d.set_index("date")["nav"]) if len(d) else np.nan
        hold_col = t["ret_hold"] if len(t) and "ret_hold" in t.columns else pd.Series(dtype=float)
        summaries.append(
            {
                "id": sid,
                "策略": spec["name"],
                "脚本": spec["file"],
                "市场": spec["board"],
                "持有日": spec.get("hold_days", 1),
                "可交易": spec.get("tradeable", True),
                "信号日数": n_days,
                "有票天数": n_active,
                "覆盖率%": round(n_active / n_days * 100, 1) if n_days else np.nan,
                "日均选出": round(avg_picks, 2),
                "总交易笔数": int(len(t)),
                "次日OC胜率%": round(_win_rate(t["ret_1d_oc"]) * 100, 1) if len(t) else np.nan,
                "次日OC均收益%": round(t["ret_1d_oc"].mean() * 100, 3) if len(t) else np.nan,
                "次日CC均收益%": round(t["ret_1d_cc"].mean() * 100, 3) if len(t) else np.nan,
                "3日均收益%": round(t["ret_3d"].mean() * 100, 3) if len(t) else np.nan,
                "5日均收益%": round(t["ret_5d"].mean() * 100, 3) if len(t) else np.nan,
                "10日均收益%": round(t["ret_10d"].mean() * 100, 3) if len(t) else np.nan,
                "持有期均收益%": round(hold_col.mean() * 100, 3) if len(hold_col) else np.nan,
                "组合期末净值": round(nav, 4) if pd.notna(nav) else np.nan,
                "组合年化%": round(ann * 100, 2) if pd.notna(ann) else np.nan,
                "组合波动%": round(vol * 100, 2) if pd.notna(vol) else np.nan,
                "最大回撤%": round(dd * 100, 2) if pd.notna(dd) else np.nan,
            }
        )

        if len(d):
            dd2 = d.copy()
            dd2["year"] = pd.to_datetime(dd2["date"]).dt.year
            for year, g in dd2.groupby("year"):
                ynav = float((1.0 + g["day_ret"]).prod())
                ydd = _maxdd((1.0 + g["day_ret"]).cumprod())
                yearly_rows.append(
                    {
                        "strategy": sid,
                        "year": int(year),
                        "nav": round(ynav, 4),
                        "cover_pct": round(float((g["n_picks"] > 0).mean()) * 100, 1),
                        "mean_day_pct": round(float(g["day_ret"].mean()) * 100, 3),
                        "maxdd_pct": round(ydd * 100, 2) if pd.notna(ydd) else np.nan,
                    }
                )

    for code, name in [("sh000300", "沪深300"), ("sz399006", "创业板指"), ("sh000001", "上证指数")]:
        ix = index[index["code"] == code].sort_values("date")
        ix = ix[(ix["date"] >= start_ts) & (ix["date"] <= end_ts)]
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
                "持有日": np.nan,
                "可交易": True,
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
                "持有期均收益%": np.nan,
                "组合期末净值": round(float(nav.iloc[-1]), 4),
                "组合年化%": round(((float(nav.iloc[-1]) ** (1 / years)) - 1) * 100, 2),
                "组合波动%": round(float(r.std() * np.sqrt(242) * 100), 2),
                "最大回撤%": round(_maxdd(nav) * 100, 2),
            }
        )

    summary = pd.DataFrame(summaries)
    summary.to_csv(RESULTS / "summary.csv", index=False, encoding="utf-8-sig")
    yearly = pd.DataFrame(yearly_rows)
    yearly.to_csv(RESULTS / "yearly.csv", index=False, encoding="utf-8-sig")
    print(summary.to_string(index=False))
    return summary, trades

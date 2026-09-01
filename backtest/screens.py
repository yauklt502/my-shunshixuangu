# -*- coding: utf-8 -*-
"""三套实盘对应的日线筛选。重复脚本已并入这三套，不再单独回测。"""
from __future__ import annotations

import numpy as np
import pandas as pd

MAIN_PREFIX = ("600", "601", "603", "605", "000", "001", "002")
YAOLONG_PREFIX = ("600", "601", "603", "605", "000", "001")  # no 002
CYB_PREFIX = ("300",)


def _pfx(df: pd.DataFrame, prefixes: tuple[str, ...]) -> pd.Series:
    return df["code"].str.startswith(prefixes)


def _ok(df: pd.DataFrame) -> pd.Series:
    return df["tradable"].fillna(False)


def _main_init(day: pd.DataFrame) -> pd.Series:
    return (
        _ok(day)
        & _pfx(day, MAIN_PREFIX)
        & (day["pct"] > 2)
        & (day["pct"] < 5.5)
        & (day["amount"] >= 1e8)
        & (day["amp"] <= 10)
    )


def screen_trend_stable(day: pd.DataFrame) -> pd.DataFrame:
    """主板·趋势稳健少：量比≥1.2，最多 3 只，不够不凑。"""
    m = (
        _main_init(day)
        & (day["nobs"] >= 120)
        & (day["close"] > day["ma20"])
        & (day["ma20"] > day["ma60"])
        & (day["ma60"] > day["ma120"])
        & (day["ma60"] > day["ma60_last"])
        & (day["spread_ma20_ma60"] > 0.01)
        & (day["vol_ratio"] >= 1.2)
    )
    out = day.loc[m].copy()
    if out.empty:
        return out
    vol_sc = np.minimum(out["vol_ratio"], 5) / 5 * 40
    pct_sc = out["pct"] / 5.5 * 20
    trend_sc = (
        out["close"] / out["ma20"] * 0.5
        + out["ma20"] / out["ma60"] * 0.3
        + out["ma60"] / out["ma120"] * 0.2
    )
    trend_sc = np.minimum(trend_sc, 1.2) / 1.2 * 40
    out["score"] = (vol_sc + pct_sc + trend_sc).round(2)
    return out.sort_values("score", ascending=False).head(3)


def screen_cyb_loose(day: pd.DataFrame) -> pd.DataFrame:
    """创业板·放宽版：无 MA5，扫全部 300，最多 8 只。"""
    m = (
        _ok(day)
        & _pfx(day, CYB_PREFIX)
        & (day["nobs"] >= 60)
        & day["pct"].between(3, 12)
        & (day["vol_ratio"] >= 1.5)
        & (day["close"] > day["ma20"])
        & (day["ma20"] > day["ma60"])
        & (day["ma60"] > day["ma120_eff"])
        & (day["ma60"] > day["ma60_last"])
        & (day["amp10"] < 12)
        & (day["bias20"] < 18)
    )
    out = day.loc[m].copy()
    if out.empty:
        return out
    vol_sc = np.minimum(out["vol_ratio"], 8) / 8 * 35
    trend_sc = (out["ma20"] / out["ma60"]) * 35
    amp_sc = (12 - out["amp10"]) / 12 * 30
    out["score"] = (vol_sc + trend_sc + amp_sc).round(2)
    return out.sort_values("score", ascending=False).head(8)


def screen_dragon(day: pd.DataFrame) -> pd.DataFrame:
    """龙头盯盘：全市场总龙头 Top3（仅观察，回测不入组合）。"""
    d = day.loc[_ok(day) & (day["nobs"] >= 2)].copy()
    if d.empty:
        return d
    candidates = d[(d["pct"] > 3.0) | (d["amount"] > 2e8)].copy()
    if candidates.empty:
        return candidates
    is_cyb_star = candidates["code"].str.startswith(("300", "688"))
    candidates["is_limit"] = np.where(
        is_cyb_star, candidates["pct"] >= 19.5, candidates["pct"] >= 9.5
    )
    need_board = (candidates["pct"] > 5.0) | (candidates["amount"] > 5e8)
    candidates["consecutive"] = np.where(need_board, candidates["consec_limit"].fillna(0), 0)
    max_amount = candidates["amount"].max()
    if max_amount <= 0:
        max_amount = 1.0
    score = np.where(candidates["is_limit"], 1000.0, 0.0)
    score = score + candidates["consecutive"] * 100
    score = score + candidates["pct"] * 2
    score = score + (candidates["amount"] / max_amount) * 50
    candidates["score"] = score.round(2)
    return candidates.sort_values("score", ascending=False).head(3)


def _yaolong_core(day: pd.DataFrame) -> pd.DataFrame:
    m = (
        _ok(day)
        & _pfx(day, YAOLONG_PREFIX)
        & (day["nobs"] >= 100)
        & (day["ma5"] > day["ma10"])
        & (day["ma10"] > day["ma20"])
        & (day["ma20"] > day["ma60"])
        & (day["ma5"] > day["ma5_last3"])
        & (day["ma10"] > day["ma10_last3"])
        & (day["ma20"] > day["ma20_last5"])
        & (day["close"] >= day["ma5"])
        & (day["rise5"] >= 12)
        & (day["rise10"] >= 20)
        & (day["pct"] >= 2)
        & (day["vol_ratio"] >= 1.0)
        & (day["vol_ratio"] <= 8)
        & (day["amount"] >= 8e8)
        & (day["up10"] >= 7)
    )
    return day.loc[m].copy()


def _yaolong_secondary_ok(row_df: pd.DataFrame) -> pd.Series:
    boom = (row_df["vol3_old"] > 0) & (row_df["vol3_now"] > row_df["vol3_old"] * 2.0)
    near_high = row_df["close"] < row_df["high30"] * 0.97
    pb = row_df["pullback"] > 5
    vola = row_df["amp10_close"] > 12
    return ~(boom.fillna(False) | near_high.fillna(False) | pb.fillna(False) | vola.fillna(False))


def screen_yaolong_opt(day: pd.DataFrame, sentiment_code: int | None = 1) -> pd.DataFrame:
    """主板妖龙：正式通过；情绪红灯时空仓。连板用真实连续涨停。"""
    if sentiment_code == 0:
        return day.iloc[0:0].copy()
    out = _yaolong_core(day)
    if out.empty:
        return out
    out = out.loc[_yaolong_secondary_ok(out)].copy()
    if out.empty:
        return out
    limit_up = out["consec_limit"].fillna(0)
    sub_lb = limit_up >= 2
    score = np.where(
        sub_lb,
        limit_up * 30
        + out["pct"] * 6
        + out["vol_ratio"] * 25
        + out["rise5"] * 2
        + out["up10"] * 8
        + (5 - out["pullback"]) * 5,
        out["rise5"] * 3
        + out["rise10"] * 2
        + out["pct"] * 5
        + out["vol_ratio"] * 20
        + out["spread_ma5_ma20"] * 8
        + limit_up * 25
        + out["up10"] * 10
        + (5 - out["pullback"]) * 10,
    )
    out["score"] = pd.Series(score, index=out.index).round(2)
    return out.sort_values("score", ascending=False)


STRATEGIES = [
    {
        "id": "main_trend",
        "name": "主板·趋势稳健少（不满仓/持有5日）",
        "file": "趋势稳健少.py",
        "board": "主板(+中小板)",
        "topn": 3,
        "fn": "trend_stable",
        "bench": "sh000300",
        "hold_days": 5,
        "tradeable": True,
        "use_sentiment": False,
    },
    {
        "id": "cyb_trend",
        "name": "创业板·放宽版（全市场/持有5日）",
        "file": "趋势王创业板_放宽版.py",
        "board": "创业板",
        "topn": 8,
        "fn": "cyb_loose",
        "bench": "sz399006",
        "hold_days": 5,
        "tradeable": True,
        "use_sentiment": False,
    },
    {
        "id": "main_trend_1d",
        "name": "对照·稳健少（最多3只/仍隔夜）",
        "file": "趋势稳健少.py",
        "board": "主板(+中小板)",
        "topn": 3,
        "fn": "trend_stable",
        "bench": "sh000300",
        "hold_days": 1,
        "tradeable": True,
        "use_sentiment": False,
    },
    {
        "id": "cyb_trend_1d",
        "name": "对照·创业板放宽（最多8只/仍隔夜）",
        "file": "趋势王创业板_放宽版.py",
        "board": "创业板",
        "topn": 8,
        "fn": "cyb_loose",
        "bench": "sz399006",
        "hold_days": 1,
        "tradeable": True,
        "use_sentiment": False,
    },
    {
        "id": "yaolong_on",
        "name": "主板妖龙（红灯空仓/只做隔夜）",
        "file": "主板妖龙优化.py",
        "board": "沪深主板(不含002)",
        "topn": None,
        "fn": "yaolong_opt",
        "bench": "sh000300",
        "hold_days": 1,
        "tradeable": True,
        "use_sentiment": True,
    },
    {
        "id": "dragon_obs",
        "name": "龙头盯盘（仅观察不下单）",
        "file": "龙头盯盘.py",
        "board": "全市场",
        "topn": 3,
        "fn": "dragon",
        "bench": "sh000300",
        "hold_days": 1,
        "tradeable": False,
        "use_sentiment": False,
    },
]


def run_screen(fn: str, day: pd.DataFrame, sentiment_code: int = 1) -> pd.DataFrame:
    if fn == "trend_stable":
        return screen_trend_stable(day)
    if fn == "cyb_loose":
        return screen_cyb_loose(day)
    if fn == "dragon":
        return screen_dragon(day)
    if fn == "yaolong_opt":
        return screen_yaolong_opt(day, sentiment_code=sentiment_code)
    raise KeyError(fn)

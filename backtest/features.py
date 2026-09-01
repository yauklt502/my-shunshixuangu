# -*- coding: utf-8 -*-
"""Precompute technical features used by all screeners."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _rolling_group(s: pd.Series, group: pd.Series, window: int, fn: str) -> pd.Series:
    g = s.groupby(group, sort=False)
    if fn == "mean":
        return g.rolling(window, min_periods=window).mean().reset_index(level=0, drop=True)
    if fn == "max":
        return g.rolling(window, min_periods=window).max().reset_index(level=0, drop=True)
    if fn == "sum":
        return g.rolling(window, min_periods=window).sum().reset_index(level=0, drop=True)
    raise ValueError(fn)


def _consec_true(s: pd.Series) -> pd.Series:
    s = s.fillna(False).astype(bool)
    gid = (~s).cumsum()
    return s.groupby(gid).cumsum()


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["code", "date"]).reset_index(drop=True)
    code = df["code"]
    close = df["close"]
    high = df["high"]
    low = df["low"]
    vol = df["volume"]
    prev = close.groupby(code).shift(1)

    df["pct"] = (close / prev - 1.0) * 100.0
    df["ma5"] = _rolling_group(close, code, 5, "mean")
    df["ma10"] = _rolling_group(close, code, 10, "mean")
    df["ma20"] = _rolling_group(close, code, 20, "mean")
    df["ma60"] = _rolling_group(close, code, 60, "mean")
    df["ma120"] = _rolling_group(close, code, 120, "mean")
    df["ma5_last"] = df["ma5"].groupby(code).shift(1)
    df["ma10_last"] = df["ma10"].groupby(code).shift(1)
    df["ma20_last3"] = df["ma20"].groupby(code).shift(3)  # compared to -5 in 妖龙 uses iloc[-5]
    df["ma5_last3"] = df["ma5"].groupby(code).shift(3)
    df["ma10_last3"] = df["ma10"].groupby(code).shift(3)
    df["ma20_last5"] = df["ma20"].groupby(code).shift(5)
    df["ma60_last"] = df["ma60"].groupby(code).shift(1)
    df["ma120_eff"] = df["ma120"].fillna(df["ma60"])

    vol_avg5 = _rolling_group(vol.groupby(code).shift(1), code, 5, "mean")
    df["vol_ratio"] = np.where(vol_avg5 > 0, vol / vol_avg5, np.nan)
    df["amp"] = np.where(low > 0, (high - low) / low * 100.0, np.nan)
    df["amp10"] = _rolling_group(df["amp"], code, 10, "mean")
    amp_close = np.where(close > 0, (high - low) / close * 100.0, np.nan)
    df["amp10_close"] = _rolling_group(pd.Series(amp_close, index=df.index), code, 10, "mean")
    df["bias20"] = np.where(df["ma20"] > 0, (close - df["ma20"]) / df["ma20"] * 100.0, np.nan)
    df["rise5"] = (close / close.groupby(code).shift(5) - 1.0) * 100.0
    df["rise10"] = (close / close.groupby(code).shift(10) - 1.0) * 100.0
    df["high30"] = _rolling_group(high, code, 30, "max")
    df["pullback"] = np.where(df["high30"] > 0, (df["high30"] - close) / df["high30"] * 100.0, np.nan)
    up = (close > prev).astype(float)
    df["up10"] = _rolling_group(up, code, 10, "sum")
    hit_main = (df["pct"] >= 9.5).astype(float)
    df["limit_up_6"] = _rolling_group(hit_main, code, 6, "sum")
    vol3 = _rolling_group(vol, code, 3, "mean")
    df["vol3_now"] = vol3
    df["vol3_old"] = vol3.groupby(code).shift(3)

    ma5_pct = (df["ma5"] / df["ma5_last"] - 1.0) * 100.0
    ma10_pct = (df["ma10"] / df["ma10_last"] - 1.0) * 100.0
    df["ma5_angle"] = np.degrees(np.arctan(ma5_pct))
    df["ma10_angle"] = np.degrees(np.arctan(ma10_pct))
    df["spread_ma5_ma20"] = np.where(df["ma20"] > 0, (df["ma5"] - df["ma20"]) / df["ma20"] * 100.0, np.nan)
    df["spread_ma5_ma60"] = np.where(df["ma60"] > 0, (df["ma5"] - df["ma60"]) / df["ma60"] * 100.0, np.nan)
    df["spread_ma20_ma60"] = np.where(df["ma60"] > 0, (df["ma20"] - df["ma60"]) / df["ma60"], np.nan)

    is_20cm = df["code"].str.startswith(("300", "688"))
    hit_limit = np.where(is_20cm, close / prev >= 1.195, close / prev >= 1.095)
    df["consec_limit"] = (
        pd.Series(hit_limit, index=df.index).groupby(code, sort=False).transform(_consec_true)
    )
    # 兼容旧字段：龙头/妖龙一律用真实连板（20cm 用 19.5%）
    df["consec_boards"] = df["consec_limit"]
    nobs = df.groupby(code).cumcount() + 1
    df["nobs"] = nobs
    df["tradable"] = (df["volume"] > 0) & (df["close"] > 0) & (df["open"] > 0) & (df["low"] > 0)
    return df


def add_index_sentiment(index_df: pd.DataFrame) -> pd.DataFrame:
    idx = index_df.copy()
    idx["date"] = pd.to_datetime(idx["date"])
    sh = idx[idx["code"] == "sh000001"].sort_values("date").copy()
    sz = idx[idx["code"] == "sz399001"].sort_values("date").copy()
    if sh.empty:
        return pd.DataFrame(columns=["date", "sentiment_score", "sentiment_code"])
    c = sh["close"]
    sh["ma5"] = c.rolling(5).mean()
    sh["ma10"] = c.rolling(10).mean()
    sh["pct"] = c.pct_change() * 100.0
    sh["rise5"] = (c / c.shift(5) - 1.0) * 100.0
    sz_pct = sz.set_index("date")["close"].pct_change() * 100.0
    sh = sh.set_index("date")
    score = np.zeros(len(sh))
    score += np.where(sh["pct"] > 0.3, 35, np.where(sh["pct"] > -0.3, 18, 0))
    score += np.where(sh["close"] > sh["ma5"], 25, 0)
    score += np.where(sh["ma5"] > sh["ma10"], 25, 0)
    score += np.where(sh["rise5"] > 0, 15, 0)
    aligned = sz_pct.reindex(sh.index)
    score = np.where(aligned <= -1.0, np.maximum(0, score - 10), score)
    code = np.where(score >= 70, 2, np.where(score >= 40, 1, 0))
    out = pd.DataFrame(
        {
            "date": sh.index,
            "sentiment_score": score,
            "sentiment_code": code,
            "index_pct": sh["pct"].values,
        }
    )
    return out.reset_index(drop=True)

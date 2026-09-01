"""Vectorized Sequoia-X V2 screening rules.

Each function returns a boolean DataFrame aligned to close (date x symbol).
Rules are copied from sngyai/Sequoia-X strategy modules, evaluated every day
with only information available on that close (no look-ahead inside the rule).
"""

from __future__ import annotations

import pandas as pd

STRATEGY_NAMES = (
    "turtle_trade",
    "ma_volume",
    "high_tight_flag",
    "limit_up_shakeout",
    "uptrend_limit_down",
    "rps_breakout",
)


def pivot_ohlcv(ohlcv: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build date x symbol panels from long OHLCV."""
    panels = {}
    for col in ["open", "high", "low", "close", "volume", "turnover"]:
        panels[col] = (
            ohlcv.pivot_table(index="date", columns="symbol", values=col, aggfunc="last")
            .sort_index()
        )
    return panels


def turtle_trade(panels: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """20-day high breakout + turnover > 1e8 + bullish candle."""
    close = panels["close"]
    high = panels["high"]
    open_ = panels["open"]
    turnover = panels["turnover"]
    high_20 = high.shift(1).rolling(20, min_periods=20).max()
    breakout = close > high_20
    liquid = turnover > 100_000_000
    is_yang = close > open_
    is_up = close > close.shift(1)
    return (breakout & liquid & is_yang & is_up).fillna(False)


def ma_volume(panels: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """MA5 golden-cross MA20 with 1.5x 20-day volume."""
    close = panels["close"]
    volume = panels["volume"]
    ma5 = close.rolling(5, min_periods=5).mean()
    ma20 = close.rolling(20, min_periods=20).mean()
    vol_ma20 = volume.rolling(20, min_periods=20).mean()
    golden_cross = (ma5.shift(1) < ma20.shift(1)) & (ma5 > ma20)
    volume_surge = volume > vol_ma20 * 1.5
    return (golden_cross & volume_surge).fillna(False)


def high_tight_flag(panels: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """High-tight flag: 40d momentum, 10d coil, hold high, shrink volume."""
    high = panels["high"]
    low = panels["low"]
    volume = panels["volume"]
    high40 = high.rolling(40, min_periods=40).max()
    low40 = low.rolling(40, min_periods=40).min()
    high10 = high.rolling(10, min_periods=10).max()
    low10 = low.rolling(10, min_periods=10).min()
    vol_ma20 = volume.shift(1).rolling(20, min_periods=20).mean()
    momentum = high40 / low40 > 1.6
    consolidation = high10 / low10 < 1.15
    high_level = low10 >= high40 * 0.8
    shrink = volume < vol_ma20 * 0.6
    return (momentum & consolidation & high_level & shrink).fillna(False)


def limit_up_shakeout(panels: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Yesterday limit-up, today bearish volume shakeout that holds yesterday close."""
    close = panels["close"]
    open_ = panels["open"]
    low = panels["low"]
    volume = panels["volume"]
    limit_up_yesterday = close.shift(1) >= close.shift(2) * 1.095
    bearish_today = close < open_
    volume_surge = volume > volume.shift(1) * 2.0
    support_hold = low >= close.shift(1)
    return (limit_up_yesterday & bearish_today & volume_surge & support_hold).fillna(False)


def uptrend_limit_down(panels: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Uptrend (MA20>MA60 yesterday) + volume limit-down today."""
    close = panels["close"]
    volume = panels["volume"]
    ma20 = close.rolling(20, min_periods=20).mean()
    ma60 = close.rolling(60, min_periods=60).mean()
    vol_ma20 = volume.rolling(20, min_periods=20).mean()
    uptrend = ma20.shift(1) > ma60.shift(1)
    limit_down = close <= close.shift(1) * 0.905
    volume_surge = volume > vol_ma20 * 2.0
    return (uptrend & limit_down & volume_surge).fillna(False)


def rps_breakout(panels: dict[str, pd.DataFrame], period: int = 120, threshold: float = 90.0) -> pd.DataFrame:
    """O'Neil-style RPS >= 90 and close within 10% of 120d high."""
    close = panels["close"]
    high = panels["high"]
    pct_change = close / close.shift(period) - 1.0
    rps = pct_change.rank(axis=1, pct=True) * 100.0
    roll_high = high.rolling(period, min_periods=period // 2).max()
    strong = rps >= threshold
    breakout = close >= roll_high * 0.90
    return (strong & breakout).fillna(False)


def compute_all_signals(ohlcv: pd.DataFrame) -> dict[str, pd.DataFrame]:
    panels = pivot_ohlcv(ohlcv)
    return {
        "turtle_trade": turtle_trade(panels),
        "ma_volume": ma_volume(panels),
        "high_tight_flag": high_tight_flag(panels),
        "limit_up_shakeout": limit_up_shakeout(panels),
        "uptrend_limit_down": uptrend_limit_down(panels),
        "rps_breakout": rps_breakout(panels),
    }

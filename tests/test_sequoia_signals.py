"""Unit tests for Sequoia-X signal rules and trade fills."""

from __future__ import annotations

import numpy as np
import pandas as pd

from sequoia_backtest.backtest import event_study, next_open_tradable, overlapping_portfolio
from sequoia_backtest.signals import (
    high_tight_flag,
    limit_up_shakeout,
    ma_volume,
    rps_breakout,
    turtle_trade,
    uptrend_limit_down,
)


def _panel(values: np.ndarray, start="2024-01-02", symbol="000001") -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=len(values))
    return pd.DataFrame({symbol: values}, index=idx)


def _panels_from_ohlc(open_, high, low, close, volume, turnover=None, symbol="000001"):
    if turnover is None:
        turnover = volume * close
    return {
        "open": _panel(open_, symbol=symbol),
        "high": _panel(high, symbol=symbol),
        "low": _panel(low, symbol=symbol),
        "close": _panel(close, symbol=symbol),
        "volume": _panel(volume, symbol=symbol),
        "turnover": _panel(turnover, symbol=symbol),
    }


def test_turtle_trade_detects_20day_breakout_yang_line():
    n = 25
    close = np.full(n, 10.0)
    high = np.full(n, 10.5)
    low = np.full(n, 9.5)
    open_ = np.full(n, 9.8)
    volume = np.full(n, 1_000_000.0)
    turnover = np.full(n, 200_000_000.0)
    close[-1] = 12.0
    high[-1] = 12.2
    open_[-1] = 11.0
    panels = _panels_from_ohlc(open_, high, low, close, volume, turnover)
    sig = turtle_trade(panels)
    assert bool(sig.iloc[-1, 0])
    assert not bool(sig.iloc[-2, 0])


def test_turtle_trade_rejects_bearish_breakout():
    n = 25
    close = np.full(n, 10.0)
    high = np.full(n, 10.5)
    open_ = np.full(n, 9.8)
    low = np.full(n, 9.5)
    volume = np.full(n, 1_000_000.0)
    turnover = np.full(n, 200_000_000.0)
    close[-1] = 12.0
    high[-1] = 13.0
    open_[-1] = 12.5  # yin line
    panels = _panels_from_ohlc(open_, high, low, close, volume, turnover)
    sig = turtle_trade(panels)
    assert not bool(sig.iloc[-1, 0])


def test_ma_volume_golden_cross_with_volume_surge():
    n = 30
    close = np.concatenate([np.full(20, 20.0), np.full(10, 10.0)])
    # last 5 days rally so MA5 crosses MA20 from below
    close[-5:] = np.array([10.0, 14.0, 18.0, 22.0, 26.0])
    volume = np.full(n, 1000.0)
    volume[-1] = 5000.0
    high = close + 0.1
    low = close - 0.1
    open_ = close.copy()
    panels = _panels_from_ohlc(open_, high, low, close, volume)
    sig = ma_volume(panels)
    assert bool(sig.iloc[-1, 0])


def test_high_tight_flag_requires_coil_after_runup():
    n = 45
    close = np.linspace(10.0, 18.0, n)
    high = close + 0.2
    low = close - 0.2
    # last 10 days: tight range near highs
    close[-10:] = 17.8
    high[-10:] = 18.0
    low[-10:] = 17.6
    # 40d high/low still > 1.6 because early lows ~10 and highs ~18
    volume = np.full(n, 1000.0)
    volume[-1] = 200.0
    open_ = close.copy()
    panels = _panels_from_ohlc(open_, high, low, close, volume)
    sig = high_tight_flag(panels)
    assert bool(sig.iloc[-1, 0])


def test_limit_up_shakeout_pattern():
    n = 5
    close = np.array([10.0, 10.0, 10.0, 11.0, 10.95])
    open_ = np.array([10.0, 10.0, 10.0, 10.2, 11.2])
    high = np.array([10.1, 10.1, 10.1, 11.0, 11.3])
    low = np.array([9.9, 9.9, 9.9, 10.1, 11.0])  # today low holds yesterday close 11.0
    volume = np.array([100.0, 100.0, 100.0, 100.0, 250.0])
    panels = _panels_from_ohlc(open_, high, low, close, volume)
    sig = limit_up_shakeout(panels)
    assert bool(sig.iloc[-1, 0])


def test_uptrend_limit_down_in_ma20_above_ma60():
    n = 70
    close = np.linspace(10.0, 20.0, n)
    close[-1] = close[-2] * 0.90  # limit down
    volume = np.full(n, 1000.0)
    volume[-1] = 5000.0
    high = np.maximum(close, np.r_[close[0], close[:-1]]) + 0.1
    low = close - 0.1
    open_ = close.copy()
    open_[-1] = close[-2]
    panels = _panels_from_ohlc(open_, high, low, close, volume)
    sig = uptrend_limit_down(panels)
    assert bool(sig.iloc[-1, 0])


def test_rps_breakout_ranks_strong_name():
    idx = pd.bdate_range("2023-01-02", periods=130)
    weak = np.full(130, 10.0)
    strong = np.linspace(10.0, 20.0, 130)
    close = pd.DataFrame({"AAA": strong, "BBB": weak}, index=idx)
    high = close + 0.1
    panels = {
        "close": close,
        "high": high,
        "low": close - 0.1,
        "open": close,
        "volume": pd.DataFrame(100.0, index=idx, columns=["AAA", "BBB"]),
        "turnover": pd.DataFrame(1e8, index=idx, columns=["AAA", "BBB"]),
    }
    sig = rps_breakout(panels, period=120, threshold=90)
    assert bool(sig.iloc[-1]["AAA"])
    assert not bool(sig.iloc[-1]["BBB"])


def test_next_open_skips_limit_up_gap():
    idx = pd.bdate_range("2024-01-02", periods=3)
    close = pd.DataFrame({"600000": [10.0, 10.0, 10.0]}, index=idx)
    open_ = pd.DataFrame({"600000": [10.0, 10.0, 11.0]}, index=idx)  # day2 open +10%
    volume = pd.DataFrame({"600000": [1.0, 1.0, 1.0]}, index=idx)
    panels = {"close": close, "open": open_, "volume": volume, "high": open_, "low": close, "turnover": volume}
    tradable = next_open_tradable(panels)
    # signal on first day, next open is 10 (ok); signal on second day, next open 11 vs close 10 -> limit up
    assert bool(tradable.iloc[0, 0])
    assert not bool(tradable.iloc[1, 0])


def test_event_study_uses_next_open_entry():
    idx = pd.bdate_range("2024-01-02", periods=8)
    close = pd.DataFrame({"600000": [10, 10, 11, 12, 13, 14, 15, 16]}, index=idx, dtype=float)
    open_ = pd.DataFrame({"600000": [10, 10, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5]}, index=idx, dtype=float)
    turnover = pd.DataFrame({"600000": [1e9] * 8}, index=idx)
    signal = pd.DataFrame(False, index=idx, columns=["600000"])
    tradable = pd.DataFrame(True, index=idx, columns=["600000"])
    signal.iloc[1, 0] = True  # T = second bar, buy next open 10.5
    trades, stats = event_study(signal, tradable, open_, close, turnover, windows=(1, 5))
    assert len(trades) == 1
    # T+1 close is 11, entry 10.5 → 11/10.5 - 1
    assert abs(trades.iloc[0]["ret_1d"] - (11 / 10.5 - 1)) < 1e-9
    assert stats[1]["n"] == 1


def test_overlapping_portfolio_earns_known_open_to_close():
    idx = pd.bdate_range("2024-01-02", periods=6)
    close = pd.DataFrame({"600000": [10.0, 10.0, 11.0, 11.0, 11.0, 11.0]}, index=idx)
    open_ = pd.DataFrame({"600000": [10.0, 10.0, 10.0, 11.0, 11.0, 11.0]}, index=idx)
    turnover = pd.DataFrame({"600000": [1e9] * 6}, index=idx)
    signal = pd.DataFrame(False, index=idx, columns=["600000"])
    tradable = pd.DataFrame(True, index=idx, columns=["600000"])
    signal.iloc[1, 0] = True
    eq, stats = overlapping_portfolio(signal, tradable, open_, close, turnover, hold_days=1, max_picks=10)
    assert stats["n_picks"] == 1
    # entry on day 2: open 10 -> close 11, minus buy+sell costs
    expected = (11 / 10 - 1) - 0.0005 - 0.0010
    assert abs(eq.iloc[2] - (1 + expected)) < 1e-9

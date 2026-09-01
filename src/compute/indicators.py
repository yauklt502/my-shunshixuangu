"""Vectorized technical indicators using numpy."""

from __future__ import annotations

import numpy as np
from typing import Dict, List

from src.common import KlineBar


def _closes(bars: List[KlineBar]) -> np.ndarray:
    return np.array([b.close for b in bars], dtype=np.float64)


def _volumes(bars: List[KlineBar]) -> np.ndarray:
    return np.array([b.volume for b in bars], dtype=np.float64)


def ma(closes: np.ndarray, period: int) -> np.ndarray:
    result = np.full(len(closes), np.nan)
    if len(closes) < period:
        return result
    cumsum = np.cumsum(closes)
    cumsum[period:] = cumsum[period:] - cumsum[:-period]
    result[period - 1:] = cumsum[period - 1:] / period
    return result


def expma(closes: np.ndarray, period: int) -> np.ndarray:
    result = np.full(len(closes), np.nan)
    if len(closes) == 0:
        return result
    alpha = 2.0 / (period + 1)
    result[0] = closes[0]
    for i in range(1, len(closes)):
        result[i] = alpha * closes[i] + (1 - alpha) * result[i - 1]
    return result


def macd(closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, np.ndarray]:
    ema_fast = expma(closes, fast)
    ema_slow = expma(closes, slow)
    dif = ema_fast - ema_slow
    dea = expma(dif, signal)
    macd_bar = 2 * (dif - dea)
    return {"dif": dif, "dea": dea, "macd": macd_bar}


def kdj(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
) -> Dict[str, np.ndarray]:
    length = len(closes)
    k_arr = np.full(length, 50.0)
    d_arr = np.full(length, 50.0)
    j_arr = np.full(length, 50.0)

    for i in range(n - 1, length):
        low_n = np.min(lows[i - n + 1 : i + 1])
        high_n = np.max(highs[i - n + 1 : i + 1])
        if high_n == low_n:
            rsv = 50.0
        else:
            rsv = (closes[i] - low_n) / (high_n - low_n) * 100
        k_arr[i] = (m1 - 1) / m1 * k_arr[i - 1] + rsv / m1
        d_arr[i] = (m2 - 1) / m2 * d_arr[i - 1] + k_arr[i] / m2
        j_arr[i] = 3 * k_arr[i] - 2 * d_arr[i]

    return {"k": k_arr, "d": d_arr, "j": j_arr}


def volume_ratio(volumes: np.ndarray, period: int = 5) -> np.ndarray:
    avg_vol = ma(volumes, period)
    result = np.full(len(volumes), np.nan)
    mask = avg_vol > 0
    result[mask] = volumes[mask] / avg_vol[mask]
    return result


def is_triple_volume(volumes: np.ndarray, period: int = 5, multiplier: float = 3.0) -> np.ndarray:
    vr = volume_ratio(volumes, period)
    return vr >= multiplier


def ma5_step_up(closes: np.ndarray, ma5: np.ndarray, lookback: int = 5) -> np.ndarray:
    """Detect climbing along 5-day MA (5日线台阶)."""
    result = np.zeros(len(closes), dtype=bool)
    for i in range(lookback, len(closes)):
        segment = ma5[i - lookback + 1 : i + 1]
        if np.any(np.isnan(segment)):
            continue
        diffs = np.diff(segment)
        result[i] = np.all(diffs > 0) and closes[i] >= ma5[i]
    return result


def peak_warning(closes: np.ndarray, highs: np.ndarray, period: int = 20) -> np.ndarray:
    """Simple peak warning: price near N-day high with divergence."""
    result = np.zeros(len(closes), dtype=bool)
    for i in range(period, len(closes)):
        high_n = np.max(highs[i - period : i])
        result[i] = closes[i] >= high_n * 0.98 and closes[i] < closes[i - 1]
    return result


def compute_all_indicators(bars: List[KlineBar]) -> List[KlineBar]:
    """Batch compute indicators and attach to bar objects."""
    if not bars:
        return bars

    closes = _closes(bars)
    highs = np.array([b.high for b in bars], dtype=np.float64)
    lows = np.array([b.low for b in bars], dtype=np.float64)
    volumes = _volumes(bars)

    ma5 = ma(closes, 5)
    ma10 = ma(closes, 10)
    ma20 = ma(closes, 20)
    macd_vals = macd(closes)
    kdj_vals = kdj(highs, lows, closes)
    vr = volume_ratio(volumes)
    triple = is_triple_volume(volumes)
    step_up = ma5_step_up(closes, ma5)
    peak = peak_warning(closes, highs)

    enriched: List[KlineBar] = []
    for i, bar in enumerate(bars):
        indicators = {
            "ma5": float(ma5[i]) if not np.isnan(ma5[i]) else None,
            "ma10": float(ma10[i]) if not np.isnan(ma10[i]) else None,
            "ma20": float(ma20[i]) if not np.isnan(ma20[i]) else None,
            "dif": float(macd_vals["dif"][i]) if not np.isnan(macd_vals["dif"][i]) else None,
            "dea": float(macd_vals["dea"][i]) if not np.isnan(macd_vals["dea"][i]) else None,
            "macd": float(macd_vals["macd"][i]) if not np.isnan(macd_vals["macd"][i]) else None,
            "k": float(kdj_vals["k"][i]),
            "d": float(kdj_vals["d"][i]),
            "j": float(kdj_vals["j"][i]),
            "volume_ratio": float(vr[i]) if not np.isnan(vr[i]) else None,
            "triple_volume": bool(triple[i]),
            "ma5_step_up": bool(step_up[i]),
            "peak_warning": bool(peak[i]),
        }
        enriched.append(
            KlineBar(
                symbol=bar.symbol,
                timestamp=bar.timestamp,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                period=bar.period,
                indicators=indicators,
            )
        )
    return enriched

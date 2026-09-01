"""Event-study and overlapping-hold portfolio backtest."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

HOLD_WINDOWS = (1, 5, 10, 20)
BUY_COST = 0.0005
SELL_COST = 0.0010  # commission + stamp duty
MAX_PICKS_PER_DAY = 10


def limit_pct_for_symbol(symbol: str) -> float:
    if symbol.startswith(("300", "301", "688")):
        return 0.20
    if symbol.startswith(("8", "4")):
        return 0.30
    return 0.10


def next_open_tradable(panels: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """True on signal day T if T+1 open exists and is not a limit-up open vs T close."""
    close = panels["close"]
    open_ = panels["open"]
    volume = panels["volume"]
    next_open = open_.shift(-1)
    next_vol = volume.shift(-1)
    caps = pd.Series({c: limit_pct_for_symbol(str(c)) for c in close.columns})
    not_limit = next_open.lt(close.mul(1.0 + caps - 0.002, axis=1))
    has_bar = next_open.notna() & (next_vol > 0)
    return (has_bar & not_limit).fillna(False)


def _cap_picks(picks: np.ndarray, scores: np.ndarray, max_picks: int) -> np.ndarray:
    if picks.size <= max_picks:
        return picks
    order = np.argsort(np.nan_to_num(scores, nan=-np.inf))[::-1][:max_picks]
    return picks[order]


@dataclass
class StrategyResult:
    name: str
    n_raw_signals: int
    n_trades: int
    event: dict[int, dict[str, float]]
    portfolio: dict[str, float]
    equity: pd.Series = field(default_factory=pd.Series)
    trades: pd.DataFrame = field(default_factory=pd.DataFrame)


def event_study(
    signal: pd.DataFrame,
    tradable: pd.DataFrame,
    open_: pd.DataFrame,
    close: pd.DataFrame,
    turnover: pd.DataFrame,
    windows: tuple[int, ...] = HOLD_WINDOWS,
    max_picks: int = MAX_PICKS_PER_DAY,
) -> tuple[pd.DataFrame, dict[int, dict[str, float]]]:
    """Buy T+1 open, mark to close of T+N. Daily names capped by turnover."""
    live = signal & tradable
    entry = open_.shift(-1)
    rows: list[dict] = []
    dates = live.index
    symbols = list(live.columns)
    live_v = live.to_numpy()
    entry_v = entry.to_numpy()
    close_v = close.to_numpy()
    turn_v = turnover.to_numpy()
    n_dates = live_v.shape[0]
    max_w = max(windows)

    for i in range(n_dates - 1):
        picks = np.flatnonzero(live_v[i])
        if picks.size == 0:
            continue
        picks = _cap_picks(picks, turn_v[i, picks], max_picks)
        px0 = entry_v[i]
        if i + max_w >= n_dates:
            # still record shorter windows if possible
            pass
        for j in picks:
            e = px0[j]
            if not np.isfinite(e) or e <= 0:
                continue
            rec: dict = {"date": dates[i], "symbol": symbols[j], "entry": float(e)}
            complete = True
            for w in windows:
                k = i + w
                if k >= n_dates:
                    complete = False
                    rec[f"ret_{w}d"] = np.nan
                    continue
                px = close_v[k, j]
                if not np.isfinite(px) or px <= 0:
                    complete = False
                    rec[f"ret_{w}d"] = np.nan
                else:
                    rec[f"ret_{w}d"] = float(px / e - 1.0)
            if complete or any(np.isfinite(rec.get(f"ret_{w}d", np.nan)) for w in windows):
                rows.append(rec)

    trades = pd.DataFrame(rows)
    stats: dict[int, dict[str, float]] = {}
    if trades.empty:
        for w in windows:
            stats[w] = {"n": 0, "mean": float("nan"), "median": float("nan"), "win_rate": float("nan"), "p25": float("nan"), "p75": float("nan")}
        return trades, stats

    for w in windows:
        col = f"ret_{w}d"
        r = trades[col].dropna()
        if r.empty:
            stats[w] = {"n": 0, "mean": float("nan"), "median": float("nan"), "win_rate": float("nan"), "p25": float("nan"), "p75": float("nan")}
            continue
        stats[w] = {
            "n": int(len(r)),
            "mean": float(r.mean()),
            "median": float(r.median()),
            "win_rate": float((r > 0).mean()),
            "p25": float(r.quantile(0.25)),
            "p75": float(r.quantile(0.75)),
        }
    return trades, stats


def overlapping_portfolio(
    signal: pd.DataFrame,
    tradable: pd.DataFrame,
    open_: pd.DataFrame,
    close: pd.DataFrame,
    turnover: pd.DataFrame,
    hold_days: int = 5,
    max_picks: int = MAX_PICKS_PER_DAY,
) -> tuple[pd.Series, dict[str, float]]:
    """Equal-weight among names currently held.

    Signal on T → buy T+1 open, sell T+hold_days close (hold_days trading sessions).
    Entry-day name return is open→close minus buy cost; exit-day includes sell cost.
    Cash days earn 0.
    """
    live = signal & tradable
    dates = live.index
    n, m = live.shape
    close_v = close.to_numpy()
    open_v = open_.to_numpy()
    live_v = live.to_numpy()
    turn_v = turnover.to_numpy()

    held = np.zeros((n, m), dtype=bool)
    is_entry = np.zeros((n, m), dtype=bool)
    is_exit = np.zeros((n, m), dtype=bool)
    n_picks = 0
    n_entry_days = 0

    for s in range(n - 1):
        picks = np.flatnonzero(live_v[s])
        if picks.size == 0:
            continue
        picks = _cap_picks(picks, turn_v[s, picks], max_picks)
        entry_i = s + 1
        if entry_i >= n:
            continue
        exit_i = min(entry_i + hold_days - 1, n - 1)
        held[entry_i : exit_i + 1, picks] = True
        is_entry[entry_i, picks] = True
        is_exit[exit_i, picks] = True
        n_picks += int(picks.size)
        n_entry_days += 1

    cc = np.zeros((n, m))
    oc = np.zeros((n, m))
    cc[1:] = close_v[1:] / np.where(close_v[:-1] == 0, np.nan, close_v[:-1]) - 1.0
    oc[1:] = close_v[1:] / np.where(open_v[1:] == 0, np.nan, open_v[1:]) - 1.0
    cc = np.nan_to_num(cc, nan=0.0, posinf=0.0, neginf=0.0)
    oc = np.nan_to_num(oc, nan=0.0, posinf=0.0, neginf=0.0)

    daily = np.zeros(n)
    for i in range(n):
        js = np.flatnonzero(held[i])
        if js.size == 0:
            continue
        r = np.where(is_entry[i, js], oc[i, js], cc[i, js])
        r = r - np.where(is_entry[i, js], BUY_COST, 0.0) - np.where(is_exit[i, js], SELL_COST, 0.0)
        daily[i] = float(np.mean(r))

    eq = pd.Series(np.cumprod(1.0 + daily), index=dates, name="nav")
    rets = pd.Series(daily, index=dates)
    span_days = max((eq.index[-1] - eq.index[0]).days, 1)
    total = float(eq.iloc[-1] / eq.iloc[0] - 1.0) if eq.iloc[0] else float("nan")
    ann = float((eq.iloc[-1] / eq.iloc[0]) ** (365.25 / span_days) - 1.0) if eq.iloc[-1] > 0 else float("nan")
    peak = eq.cummax()
    dd = float((eq / peak - 1.0).min())
    vol = float(rets.std() * np.sqrt(252)) if rets.std() > 0 else 0.0
    sharpe = float((rets.mean() * 252) / (rets.std() * np.sqrt(252))) if rets.std() > 0 else float("nan")
    stats = {
        "total_return": total,
        "ann_return": ann,
        "max_drawdown": dd,
        "vol": vol,
        "sharpe": sharpe,
        "end_nav": float(eq.iloc[-1]),
        "n_entry_days": n_entry_days,
        "n_picks": n_picks,
    }
    return eq, stats


def buy_hold_index(index_df: pd.DataFrame, start: str, end: str) -> tuple[pd.Series, dict[str, float]]:
    s = index_df.set_index("date")["close"].sort_index().loc[start:end]
    eq = s / s.iloc[0]
    rets = eq.pct_change().fillna(0.0)
    span_days = max((eq.index[-1] - eq.index[0]).days, 1)
    total = float(eq.iloc[-1] - 1.0)
    ann = float(eq.iloc[-1] ** (365.25 / span_days) - 1.0)
    dd = float((eq / eq.cummax() - 1.0).min())
    vol = float(rets.std() * np.sqrt(252)) if rets.std() > 0 else 0.0
    sharpe = float((rets.mean() * 252) / (rets.std() * np.sqrt(252))) if rets.std() > 0 else float("nan")
    return eq, {
        "total_return": total,
        "ann_return": ann,
        "max_drawdown": dd,
        "vol": vol,
        "sharpe": sharpe,
        "end_nav": float(eq.iloc[-1]),
        "n_entry_days": int(len(eq)),
        "n_picks": 1,
    }


def evaluate_strategy(
    name: str,
    signal: pd.DataFrame,
    panels: dict[str, pd.DataFrame],
    tradable: pd.DataFrame,
    start: str,
    end: str,
    hold_days: int = 5,
) -> StrategyResult:
    close = panels["close"].loc[start:end]
    open_ = panels["open"].loc[start:end]
    turnover = panels["turnover"].loc[start:end]
    sig = signal.reindex(index=close.index, columns=close.columns).fillna(False)
    trd = tradable.reindex(index=close.index, columns=close.columns).fillna(False)
    n_raw = int(sig.to_numpy().sum())
    trades, event = event_study(sig, trd, open_, close, turnover)
    equity, port = overlapping_portfolio(sig, trd, open_, close, turnover, hold_days=hold_days)
    return StrategyResult(
        name=name,
        n_raw_signals=n_raw,
        n_trades=int(len(trades)),
        event=event,
        portfolio=port,
        equity=equity,
        trades=trades,
    )

"""Backtest analytics: win rate, P/L ratio, max drawdown, equity curve."""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from src.common import BacktestResult
from src.execution.backtest_executor import BacktestExecutor


def compute_backtest_metrics(
    executor: BacktestExecutor,
    strategy_id: str,
    initial_capital: float,
) -> BacktestResult:
    trades = executor.trades
    equity_curve = [initial_capital]
    cash = initial_capital
    positions: Dict[str, Tuple[int, float]] = {}

    for t in trades:
        symbol = t["symbol"]
        qty = t["quantity"]
        price = t["price"]
        if t["side"] == "buy":
            if symbol in positions:
                old_qty, old_avg = positions[symbol]
                new_qty = old_qty + qty
                new_avg = (old_avg * old_qty + price * qty) / new_qty
                positions[symbol] = (new_qty, new_avg)
            else:
                positions[symbol] = (qty, price)
            cash -= price * qty
        else:
            if symbol in positions:
                old_qty, _ = positions[symbol]
                cash += price * qty
                new_qty = old_qty - qty
                if new_qty <= 0:
                    del positions[symbol]
                else:
                    avg = positions[symbol][1]
                    positions[symbol] = (new_qty, avg)

        pos_value = sum(q * p for q, p in positions.values())
        equity_curve.append(cash + pos_value)

    final_equity = equity_curve[-1]
    total_return = (final_equity - initial_capital) / initial_capital

    round_trips: List[float] = []
    open_prices: Dict[str, float] = {}
    for t in trades:
        if t["side"] == "buy":
            open_prices[t["symbol"]] = t["price"]
        elif t["symbol"] in open_prices:
            pnl = (t["price"] - open_prices[t["symbol"]]) / open_prices[t["symbol"]]
            round_trips.append(pnl)
            del open_prices[t["symbol"]]

    wins = [p for p in round_trips if p > 0]
    losses = [p for p in round_trips if p <= 0]
    win_rate = len(wins) / len(round_trips) if round_trips else 0.0
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = abs(float(np.mean(losses))) if losses else 1.0
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0

    peak = np.maximum.accumulate(np.array(equity_curve))
    drawdown = (peak - np.array(equity_curve)) / peak
    max_drawdown = float(np.max(drawdown)) if len(drawdown) else 0.0

    return BacktestResult(
        strategy_id=strategy_id,
        total_return=total_return,
        win_rate=win_rate,
        profit_loss_ratio=profit_loss_ratio,
        max_drawdown=max_drawdown,
        equity_curve=equity_curve,
        trades=trades,
    )

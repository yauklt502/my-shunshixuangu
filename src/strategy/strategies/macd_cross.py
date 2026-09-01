"""MACD 金叉死叉策略."""

from __future__ import annotations

from typing import List

from src.common import KlineBar, SignalType, StrategySignal

from ..base import Strategy


class MacdCrossStrategy(Strategy):
    strategy_id = "macd_cross"

    def on_bar(self, bars: List[KlineBar], index: int) -> StrategySignal:
        bar = bars[index]
        ind = bar.indicators
        signal = SignalType.NONE
        reason = ""

        if index < 1:
            return StrategySignal(
                strategy_id=self.strategy_id,
                symbol=bar.symbol,
                signal=signal,
                timestamp=bar.timestamp,
                price=bar.close,
            )

        prev = bars[index - 1].indicators
        dif = ind.get("dif")
        dea = ind.get("dea")
        prev_dif = prev.get("dif")
        prev_dea = prev.get("dea")

        if None not in (dif, dea, prev_dif, prev_dea):
            if prev_dif <= prev_dea and dif > dea:
                signal = SignalType.OPEN_LONG
                reason = "MACD金叉"
            elif prev_dif >= prev_dea and dif < dea:
                signal = SignalType.CLOSE
                reason = "MACD死叉"

        return StrategySignal(
            strategy_id=self.strategy_id,
            symbol=bar.symbol,
            signal=signal,
            timestamp=bar.timestamp,
            price=bar.close,
            reason=reason,
        )

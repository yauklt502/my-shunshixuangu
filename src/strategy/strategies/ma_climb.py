"""Example: climb along 5-day MA (沿5日线爬升)."""

from __future__ import annotations

from datetime import datetime
from typing import List

from src.common import KlineBar, SignalType, StrategySignal

from ..base import Strategy


class Ma5ClimbStrategy(Strategy):
    strategy_id = "ma5_climb"

    def on_bar(self, bars: List[KlineBar], index: int) -> StrategySignal:
        bar = bars[index]
        ind = bar.indicators

        signal = SignalType.NONE
        reason = ""

        if ind.get("ma5_step_up") and bar.close > ind.get("ma5", 0):
            signal = SignalType.OPEN_LONG
            reason = "沿5日线台阶爬升"
        elif ind.get("peak_warning"):
            signal = SignalType.CLOSE
            reason = "见顶预警"

        return StrategySignal(
            strategy_id=self.strategy_id,
            symbol=bar.symbol,
            signal=signal,
            timestamp=bar.timestamp,
            price=bar.close,
            reason=reason,
        )

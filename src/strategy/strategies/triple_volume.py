"""Example: triple volume strategy (三倍量战法)."""

from __future__ import annotations

from typing import List

from src.common import KlineBar, SignalType, StrategySignal

from ..base import Strategy


class TripleVolumeStrategy(Strategy):
    strategy_id = "triple_volume"

    def on_bar(self, bars: List[KlineBar], index: int) -> StrategySignal:
        bar = bars[index]
        ind = bar.indicators

        signal = SignalType.NONE
        reason = ""

        if ind.get("triple_volume") and bar.close > bar.open:
            signal = SignalType.OPEN_LONG
            reason = "三倍量阳线"
        elif index > 0 and bars[index - 1].indicators.get("triple_volume"):
            prev = bars[index - 1]
            if bar.close < prev.close * 0.97:
                signal = SignalType.CLOSE
                reason = "倍量后回落止损"

        return StrategySignal(
            strategy_id=self.strategy_id,
            symbol=bar.symbol,
            signal=signal,
            timestamp=bar.timestamp,
            price=bar.close,
            reason=reason,
        )

"""缩量涨停：缩量 + 接近涨停."""

from __future__ import annotations

from typing import List

from src.common import KlineBar, SignalType, StrategySignal

from ..base import Strategy


class ShrinkLimitUpStrategy(Strategy):
    strategy_id = "shrink_limit_up"

    def on_bar(self, bars: List[KlineBar], index: int) -> StrategySignal:
        bar = bars[index]
        ind = bar.indicators
        signal = SignalType.NONE
        reason = ""

        vr = ind.get("volume_ratio")
        prev_close = bars[index - 1].close if index > 0 else bar.open
        change = (bar.close - prev_close) / prev_close if prev_close else 0

        if vr is not None and vr < 0.6 and change >= 0.095 and bar.close >= bar.open:
            signal = SignalType.OPEN_LONG
            reason = "缩量涨停"
        elif change >= 0.095 and index > 0 and bars[index - 1].close < bar.close * 0.91:
            signal = SignalType.CLOSE
            reason = "涨停打开止盈"

        return StrategySignal(
            strategy_id=self.strategy_id,
            symbol=bar.symbol,
            signal=signal,
            timestamp=bar.timestamp,
            price=bar.close,
            reason=reason,
        )

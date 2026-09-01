"""KDJ 超卖反弹策略."""

from __future__ import annotations

from typing import List

from src.common import KlineBar, SignalType, StrategySignal

from ..base import Strategy


class KdjOversoldStrategy(Strategy):
    strategy_id = "kdj_oversold"

    def on_bar(self, bars: List[KlineBar], index: int) -> StrategySignal:
        bar = bars[index]
        ind = bar.indicators
        signal = SignalType.NONE
        reason = ""

        j = ind.get("j")
        k = ind.get("k")
        d = ind.get("d")

        if index >= 1:
            prev = bars[index - 1].indicators
            prev_k = prev.get("k")
            prev_d = prev.get("d")
            if j is not None and j < 20 and k is not None and d is not None:
                if prev_k is not None and prev_d is not None and prev_k <= prev_d and k > d:
                    signal = SignalType.OPEN_LONG
                    reason = "KDJ超卖金叉"
            if j is not None and j > 80 and k is not None and d is not None:
                if prev_k is not None and prev_d is not None and prev_k >= prev_d and k < d:
                    signal = SignalType.CLOSE
                    reason = "KDJ超买死叉"

        return StrategySignal(
            strategy_id=self.strategy_id,
            symbol=bar.symbol,
            signal=signal,
            timestamp=bar.timestamp,
            price=bar.close,
            reason=reason,
        )

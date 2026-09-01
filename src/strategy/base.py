"""Strategy base class and signal definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from src.common import KlineBar, SignalType, StrategySignal


class Strategy(ABC):
    """Strategy only emits signals — never places orders directly."""

    strategy_id: str = "base"

    @abstractmethod
    def on_bar(self, bars: List[KlineBar], index: int) -> StrategySignal:
        """Evaluate at bar index. bars must include history up to index."""
        ...

    def evaluate(self, bars: List[KlineBar]) -> StrategySignal:
        if not bars:
            return StrategySignal(
                strategy_id=self.strategy_id,
                symbol="",
                signal=SignalType.NONE,
                timestamp=None,
                price=0.0,
            )
        return self.on_bar(bars, len(bars) - 1)

"""Strategy engine: backtest and live modes with multi-strategy support."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional

from src.common import Environment, KlineBar, SignalType, StrategySignal

from .base import Strategy

logger = logging.getLogger(__name__)


class StrategyEngine:
    """
    Runs strategies on standardized indicator data.
    Backtest: iterate historical bars.
    Live: trigger only on closed bars to avoid intrabar jitter.
    """

    def __init__(
        self,
        environment: Environment,
        on_signal: Optional[Callable[[StrategySignal], None]] = None,
    ):
        self.environment = environment
        self.strategies: Dict[str, Strategy] = {}
        self.on_signal = on_signal
        self._last_bar_time: Dict[str, datetime] = {}

    def register(self, strategy: Strategy) -> None:
        self.strategies[strategy.strategy_id] = strategy

    def run_backtest(self, bars: List[KlineBar]) -> List[StrategySignal]:
        signals: List[StrategySignal] = []
        for strategy in self.strategies.values():
            for i in range(len(bars)):
                sig = strategy.on_bar(bars, i)
                if sig.signal != SignalType.NONE:
                    signals.append(sig)
                    if self.on_signal:
                        self.on_signal(sig)
        return signals

    def on_live_bar(self, bars: List[KlineBar], bar_closed: bool = True) -> List[StrategySignal]:
        if self.environment != Environment.LIVE:
            raise RuntimeError("on_live_bar only available in LIVE environment")
        if not bar_closed:
            return []

        if not bars:
            return []

        symbol = bars[-1].symbol
        ts = bars[-1].timestamp
        if self._last_bar_time.get(symbol) == ts:
            return []
        self._last_bar_time[symbol] = ts

        signals: List[StrategySignal] = []
        for strategy in self.strategies.values():
            sig = strategy.evaluate(bars)
            if sig.signal != SignalType.NONE:
                signals.append(sig)
                if self.on_signal:
                    self.on_signal(sig)
        return signals

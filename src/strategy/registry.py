"""Register all built-in strategies."""

from __future__ import annotations

from typing import List

from src.strategy.base import Strategy
from src.strategy.strategies.kdj_oversold import KdjOversoldStrategy
from src.strategy.strategies.ma_climb import Ma5ClimbStrategy
from src.strategy.strategies.macd_cross import MacdCrossStrategy
from src.strategy.strategies.shrink_limit_up import ShrinkLimitUpStrategy
from src.strategy.strategies.triple_volume import TripleVolumeStrategy


def get_all_strategies() -> List[Strategy]:
    return [
        Ma5ClimbStrategy(),
        TripleVolumeStrategy(),
        ShrinkLimitUpStrategy(),
        MacdCrossStrategy(),
        KdjOversoldStrategy(),
    ]


def get_strategy(strategy_id: str) -> Strategy | None:
    for s in get_all_strategies():
        if s.strategy_id == strategy_id:
            return s
    return None

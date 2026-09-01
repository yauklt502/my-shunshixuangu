"""Risk controller: signals must pass all rules before execution."""

from __future__ import annotations

import logging
from typing import List, Optional

from src.common import AccountState, KlineBar, RiskConfig, StrategySignal

from .rules import (
    ConsecutiveLossRule,
    DailyLossRule,
    DuplicateOrderRule,
    LimitUpDownRule,
    MaxPositionRule,
    RiskCheckResult,
    RiskRule,
    SymbolFilterRule,
)

logger = logging.getLogger(__name__)


class RiskController:
    """All signals pass through risk before reaching execution layer."""

    def __init__(self, config: RiskConfig):
        self.rules: List[RiskRule] = [
            SymbolFilterRule(config),
            MaxPositionRule(config),
            DailyLossRule(config),
            ConsecutiveLossRule(config),
            LimitUpDownRule(config),
            DuplicateOrderRule(config),
        ]

    def validate(
        self,
        signal: StrategySignal,
        account: AccountState,
        bar: Optional[KlineBar] = None,
        context: Optional[dict] = None,
    ) -> RiskCheckResult:
        for rule in self.rules:
            result = rule.check(signal, account, bar, context)
            if not result.passed:
                logger.info(
                    "Risk rejected [%s] %s: %s",
                    signal.strategy_id,
                    signal.symbol,
                    result.reason,
                )
                return result
        return RiskCheckResult(True)

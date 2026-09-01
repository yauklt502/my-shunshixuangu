"""Risk control rules — must run before order execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.common import AccountState, KlineBar, RiskConfig, SignalType, StrategySignal


@dataclass
class RiskCheckResult:
    passed: bool
    reason: str = ""


class RiskRule(ABC):
    @abstractmethod
    def check(
        self,
        signal: StrategySignal,
        account: AccountState,
        bar: Optional[KlineBar] = None,
        context: Optional[dict] = None,
    ) -> RiskCheckResult:
        ...


class MaxPositionRule(RiskRule):
    def __init__(self, config: RiskConfig):
        self.config = config

    def check(
        self,
        signal: StrategySignal,
        account: AccountState,
        bar: Optional[KlineBar] = None,
        context: Optional[dict] = None,
    ) -> RiskCheckResult:
        if signal.signal != SignalType.OPEN_LONG:
            return RiskCheckResult(True)

        position_value = sum(p.market_value for p in account.positions)
        total_ratio = position_value / account.total_equity if account.total_equity else 0
        if total_ratio >= self.config.max_total_position:
            return RiskCheckResult(False, "总仓位超限")

        for p in account.positions:
            if p.symbol == signal.symbol:
                ratio = p.market_value / account.total_equity
                if ratio >= self.config.max_position_per_symbol:
                    return RiskCheckResult(False, f"{signal.symbol} 单股仓位超限")
        return RiskCheckResult(True)


class SymbolFilterRule(RiskRule):
    def __init__(self, config: RiskConfig):
        self.config = config

    def check(
        self,
        signal: StrategySignal,
        account: AccountState,
        bar: Optional[KlineBar] = None,
        context: Optional[dict] = None,
    ) -> RiskCheckResult:
        symbol = signal.symbol.upper()
        if self.config.exclude_st and ("ST" in symbol or symbol.startswith("*")):
            return RiskCheckResult(False, "ST 标的过滤")
        if self.config.exclude_star_market and symbol.startswith("688"):
            return RiskCheckResult(False, "科创板过滤")
        return RiskCheckResult(True)


class DailyLossRule(RiskRule):
    def __init__(self, config: RiskConfig):
        self.config = config

    def check(
        self,
        signal: StrategySignal,
        account: AccountState,
        bar: Optional[KlineBar] = None,
        context: Optional[dict] = None,
    ) -> RiskCheckResult:
        if account.total_equity <= 0:
            return RiskCheckResult(True)
        loss_ratio = -account.daily_pnl / account.total_equity
        if loss_ratio >= self.config.max_daily_loss:
            return RiskCheckResult(False, "单日亏损达阈值，暂停交易")
        return RiskCheckResult(True)


class ConsecutiveLossRule(RiskRule):
    def __init__(self, config: RiskConfig):
        self.config = config

    def check(
        self,
        signal: StrategySignal,
        account: AccountState,
        bar: Optional[KlineBar] = None,
        context: Optional[dict] = None,
    ) -> RiskCheckResult:
        if account.consecutive_losses >= self.config.max_consecutive_losses:
            return RiskCheckResult(False, "连续亏损暂停交易")
        return RiskCheckResult(True)


class LimitUpDownRule(RiskRule):
    def __init__(self, config: RiskConfig):
        self.config = config

    def check(
        self,
        signal: StrategySignal,
        account: AccountState,
        bar: Optional[KlineBar] = None,
        context: Optional[dict] = None,
    ) -> RiskCheckResult:
        if not self.config.avoid_limit_up_down or not bar:
            return RiskCheckResult(True)
        if signal.signal != SignalType.OPEN_LONG:
            return RiskCheckResult(True)

        prev_close = context.get("prev_close") if context else None
        if prev_close and prev_close > 0:
            change = (bar.close - prev_close) / prev_close
            if change >= 0.099 or change <= -0.099:
                return RiskCheckResult(False, "涨跌停附近，避免无法成交")
        return RiskCheckResult(True)


class DuplicateOrderRule(RiskRule):
    def __init__(self, config: RiskConfig):
        self.config = config
        self._last_open: Dict[str, datetime] = {}

    def check(
        self,
        signal: StrategySignal,
        account: AccountState,
        bar: Optional[KlineBar] = None,
        context: Optional[dict] = None,
    ) -> RiskCheckResult:
        if signal.signal != SignalType.OPEN_LONG:
            return RiskCheckResult(True)

        last = self._last_open.get(signal.symbol)
        if last and signal.timestamp:
            delta = signal.timestamp - last
            if delta < timedelta(seconds=self.config.min_order_interval_seconds):
                return RiskCheckResult(False, "短时间重复开仓拦截")
        if signal.timestamp:
            self._last_open[signal.symbol] = signal.timestamp
        return RiskCheckResult(True)

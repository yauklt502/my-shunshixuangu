"""Shared signal → risk → execution pipeline for backtest and live."""

from __future__ import annotations

from typing import Protocol

from src.common import AccountState, AppConfig, Position, SignalType, StrategySignal
from src.execution.base import Executor
from src.risk import RiskController
from src.storage import AuditLogger, RelationalStore


class ExecutorProtocol(Protocol):
    cash: float

    def submit(self, signal: StrategySignal, quantity: int): ...
    def sync_positions(self) -> list[Position]: ...


class SignalPipeline:
    """Signal out → risk check → order submit → audit log."""

    def __init__(
        self,
        config: AppConfig,
        risk: RiskController,
        executor: Executor,
        audit: AuditLogger,
        relational: RelationalStore,
    ):
        self.config = config
        self.risk = risk
        self.executor = executor
        self.audit = audit
        self.relational = relational

    def handle(self, signal: StrategySignal, prev_close: float | None = None) -> bool:
        account = self._build_account()
        context = {"prev_close": prev_close} if prev_close else None
        result = self.risk.validate(signal, account, context=context)

        self.audit.log_event(
            "signals",
            {
                "strategy_id": signal.strategy_id,
                "symbol": signal.symbol,
                "signal": signal.signal.value,
                "price": signal.price,
                "reason": signal.reason,
                "risk_passed": result.passed,
                "risk_reason": result.reason,
            },
        )
        self.relational.log_signal(
            {
                "strategy_id": signal.strategy_id,
                "symbol": signal.symbol,
                "signal": signal.signal.value,
                "price": signal.price,
                "reason": signal.reason,
                "timestamp": signal.timestamp.isoformat() if signal.timestamp else None,
            }
        )
        if not result.passed:
            return False

        quantity = self._calc_quantity(signal)
        if quantity <= 0:
            return False

        order = self.executor.submit(signal, quantity)
        self.audit.log_event(
            "orders",
            {"order_id": order.order_id, "symbol": order.symbol, "status": order.status.value},
        )
        if order.status.value == "filled":
            self.audit.log_event("fills", {"order_id": order.order_id, "price": order.filled_price})
        return True

    def _build_account(self) -> AccountState:
        positions = self.executor.sync_positions()
        if hasattr(self.executor, "total_equity"):
            equity = self.executor.total_equity  # type: ignore[attr-defined]
            cash = getattr(self.executor, "cash", self.config.initial_capital)
        elif hasattr(self.executor, "broker"):
            broker = self.executor.broker  # type: ignore[attr-defined]
            cash = getattr(broker, "cash", self.config.initial_capital)
            equity = cash + sum(p.market_value for p in positions)
        else:
            cash = self.config.initial_capital
            equity = cash + sum(p.market_value for p in positions)

        return AccountState(cash=cash, total_equity=equity, positions=list(positions))

    def _calc_quantity(self, signal: StrategySignal) -> int:
        if signal.signal == SignalType.OPEN_LONG:
            account = self._build_account()
            budget = account.cash * self.config.risk.max_position_per_symbol
            if signal.price <= 0:
                return 0
            return int(budget / signal.price / 100) * 100

        positions = {p.symbol: p for p in self.executor.sync_positions()}
        pos = positions.get(signal.symbol)
        return pos.quantity if pos else 0

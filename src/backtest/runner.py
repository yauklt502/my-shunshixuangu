"""End-to-end backtest runner."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from src.backtest.analytics import compute_backtest_metrics
from src.common import (
    AppConfig,
    BarPeriod,
    Environment,
    SignalType,
    StrategySignal,
)
from src.compute import IndicatorPreprocessor
from src.data_source import DataPipeline
from src.execution import BacktestExecutor
from src.risk import RiskController
from src.storage import AuditLogger, RelationalStore, TimeseriesStore
from src.strategy import Ma5ClimbStrategy, StrategyEngine, TripleVolumeStrategy


class BacktestRunner:
    def __init__(self, config: AppConfig):
        self.config = config
        self.pipeline = DataPipeline(Environment.BACKTEST)
        self.preprocessor = IndicatorPreprocessor()
        self.engine = StrategyEngine(Environment.BACKTEST)
        self.risk = RiskController(config.risk)
        self.executor = BacktestExecutor(config.initial_capital)
        self.timeseries = TimeseriesStore(config.storage.timeseries_dir)
        self.relational = RelationalStore(config.storage.relational_db)
        self.audit = AuditLogger(config.storage.log_dir)
        self._account_cash = config.initial_capital

    def register_default_strategies(self) -> None:
        self.engine.register(Ma5ClimbStrategy())
        self.engine.register(TripleVolumeStrategy())

    def _on_signal(self, signal: StrategySignal) -> None:
        from src.common import AccountState, Position

        account = AccountState(
            cash=self.executor.cash,
            total_equity=self.executor.total_equity,
            positions=[
                Position(
                    symbol=p.symbol,
                    quantity=p.quantity,
                    avg_price=p.avg_price,
                    market_value=p.market_value,
                )
                for p in self.executor.sync_positions()
            ],
        )
        result = self.risk.validate(signal, account)
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
            return

        quantity = self._calc_quantity(signal)
        if quantity <= 0:
            return
        order = self.executor.submit(signal, quantity)
        self.audit.log_event("orders", {"order_id": order.order_id, "symbol": order.symbol, "status": order.status.value})
        if order.status.value == "filled":
            self.audit.log_event("fills", {"order_id": order.order_id, "price": order.filled_price})
            self.relational.log_trade(self.executor.trades[-1])

    def _calc_quantity(self, signal: StrategySignal) -> int:
        if signal.signal == SignalType.OPEN_LONG:
            budget = self.executor.cash * self.config.risk.max_position_per_symbol
            if signal.price <= 0:
                return 0
            return int(budget / signal.price / 100) * 100  # A-share lot size
        pos = self.executor.positions.get(signal.symbol)
        return pos.quantity if pos else 0

    def run(
        self,
        symbol: str,
        period: BarPeriod = BarPeriod.DAILY,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 200,
    ) -> List[dict]:
        self.engine.on_signal = self._on_signal

        bars = self.pipeline.get_historical(symbol, period, start, end, limit)
        if not bars:
            return []

        enriched = self.preprocessor.process(bars)
        self.timeseries.save_bars(enriched)

        signals = self.engine.run_backtest(enriched)

        for strategy in self.engine.strategies.values():
            result = compute_backtest_metrics(self.executor, strategy.strategy_id, self.config.initial_capital)
            self.relational.save_backtest_report(result)

        return [s.__dict__ for s in signals]

"""End-to-end backtest runner."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from src.backtest.analytics import compute_backtest_metrics
from src.common import AppConfig, BarPeriod, Environment
from src.compute import IndicatorPreprocessor
from src.data_source import DataPipeline
from src.execution import BacktestExecutor
from src.risk import RiskController
from src.storage import AuditLogger, RelationalStore, TimeseriesStore
from src.strategy import StrategyEngine
from src.strategy.registry import get_all_strategies
from src.trading import SignalPipeline


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
        self.signal_pipeline = SignalPipeline(
            config, self.risk, self.executor, self.audit, self.relational
        )

    def register_default_strategies(self) -> None:
        for strategy in get_all_strategies():
            self.engine.register(strategy)

    def _on_signal(self, signal) -> None:
        self.signal_pipeline.handle(signal)
        if hasattr(self.executor, "trades") and self.executor.trades:
            last = self.executor.trades[-1]
            if last.get("order_id"):
                self.relational.log_trade(last)

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

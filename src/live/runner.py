"""Live trading orchestrator."""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from src.common import AppConfig, BarPeriod, Environment, StrategySignal
from src.compute import IndicatorPreprocessor
from src.data_source import DataPipeline
from src.data_source.stream import RealtimeBarStream
from src.execution import LiveExecutor
from src.execution.broker import create_broker
from src.risk import RiskController
from src.storage import AuditLogger, RelationalStore, TimeseriesStore
from src.strategy import StrategyEngine
from src.strategy.registry import get_all_strategies, get_strategy
from src.trading import SignalPipeline

logger = logging.getLogger(__name__)

EventCallback = Callable[[str, dict], None]


class LiveRunner:
    def __init__(self, config: AppConfig, on_event: Optional[EventCallback] = None):
        self.config = config
        self.on_event = on_event
        self.pipeline = DataPipeline(Environment.LIVE)
        self.preprocessor = IndicatorPreprocessor()
        self.engine = StrategyEngine(Environment.LIVE)
        self.risk = RiskController(config.risk)
        broker = create_broker(config.broker)
        self.executor = LiveExecutor(broker=broker, on_fill=self._on_fill)
        self.timeseries = TimeseriesStore(config.storage.timeseries_dir)
        self.relational = RelationalStore(config.storage.relational_db)
        self.audit = AuditLogger(config.storage.log_dir)
        self.signal_pipeline = SignalPipeline(
            config, self.risk, self.executor, self.audit, self.relational
        )
        self._stream: Optional[RealtimeBarStream] = None
        self._signals: List[StrategySignal] = []

    def register_default_strategies(self) -> None:
        for strategy in get_all_strategies():
            self.engine.register(strategy)

    def register_strategy(self, strategy_id: str) -> bool:
        strategy = get_strategy(strategy_id)
        if strategy:
            self.engine.register(strategy)
            return True
        return False

    def _on_fill(self, order) -> None:
        self.relational.log_trade(
            {
                "order_id": order.order_id,
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": order.filled_quantity,
                "price": order.filled_price,
                "strategy_id": order.strategy_id,
                "timestamp": order.created_at.isoformat() if order.created_at else None,
            }
        )
        self._emit("fill", {"order_id": order.order_id, "symbol": order.symbol, "price": order.filled_price})

    def _emit(self, event_type: str, data: dict) -> None:
        if self.on_event:
            self.on_event(event_type, data)

    def _on_bar(self, symbol: str, bars: list, bar_closed: bool) -> None:
        if not bar_closed:
            self._emit("tick", {"symbol": symbol, "price": bars[-1].close, "timestamp": str(bars[-1].timestamp)})
            return

        self.timeseries.save_bars(bars)
        prev_close = bars[-2].close if len(bars) >= 2 else None
        self.engine.on_signal = lambda sig: self._handle_signal(sig, prev_close)
        signals = self.engine.on_live_bar(bars, bar_closed=True)
        self._signals.extend(signals)
        self._emit(
            "bar_closed",
            {
                "symbol": symbol,
                "close": bars[-1].close,
                "signals": len(signals),
                "timestamp": str(bars[-1].timestamp),
            },
        )

    def _handle_signal(self, signal: StrategySignal, prev_close: float | None) -> None:
        self.signal_pipeline.handle(signal, prev_close=prev_close)
        self._emit(
            "signal",
            {
                "strategy_id": signal.strategy_id,
                "symbol": signal.symbol,
                "signal": signal.signal.value,
                "price": signal.price,
                "reason": signal.reason,
            },
        )

    def start(self, symbols: Optional[List[str]] = None) -> None:
        symbols = symbols or self.config.live.symbols
        period = BarPeriod(self.config.live.bar_period)
        self.engine.on_signal = None
        self._stream = RealtimeBarStream(
            symbols=symbols,
            period=period,
            poll_interval=self.config.live.poll_interval_seconds,
            on_bar=self._on_bar,
        )
        self._stream.start()
        self._emit("live_started", {"symbols": symbols, "period": period.value})
        logger.info("Live runner started: symbols=%s", symbols)

    def stop(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream = None
        self._emit("live_stopped", {})

    @property
    def is_running(self) -> bool:
        return self._stream is not None and self._stream._running

    def status(self) -> dict:
        positions = self.executor.sync_positions()
        return {
            "running": self.is_running,
            "symbols": self.config.live.symbols,
            "strategies": list(self.engine.strategies.keys()),
            "signal_count": len(self._signals),
            "positions": [
                {"symbol": p.symbol, "quantity": p.quantity, "avg_price": p.avg_price}
                for p in positions
            ],
        }

"""Realtime bar stream with bar-close detection."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

from src.common import BarPeriod, Environment, KlineBar
from src.compute import IndicatorPreprocessor
from src.data_source import DataPipeline

logger = logging.getLogger(__name__)

BarCallback = Callable[[str, List[KlineBar], bool], None]


class RealtimeBarStream:
    """
    Poll live data sources and emit callbacks when a bar closes.
    bar_closed=True means a new completed bar is available for strategy evaluation.
    """

    def __init__(
        self,
        symbols: List[str],
        period: BarPeriod = BarPeriod.DAILY,
        poll_interval: float = 5.0,
        on_bar: Optional[BarCallback] = None,
    ):
        self.symbols = symbols
        self.period = period
        self.poll_interval = poll_interval
        self.on_bar = on_bar
        self.pipeline = DataPipeline(Environment.LIVE)
        self.preprocessor = IndicatorPreprocessor()
        self._last_ts: Dict[str, datetime] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Realtime stream started for %s", self.symbols)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.poll_interval + 2)
        logger.info("Realtime stream stopped")

    def _loop(self) -> None:
        while self._running:
            for symbol in self.symbols:
                try:
                    self._poll_symbol(symbol)
                except Exception as e:
                    logger.warning("Stream poll error [%s]: %s", symbol, e)
            time.sleep(self.poll_interval)

    def _poll_symbol(self, symbol: str) -> None:
        bars = self.pipeline.get_historical(symbol, self.period, limit=120)
        if not bars:
            bar = self.pipeline.get_realtime_bar(symbol, self.period)
            if bar:
                bars = [bar]
            else:
                return

        enriched = self.preprocessor.process(bars, use_cache=False)
        latest = enriched[-1]
        prev_ts = self._last_ts.get(symbol)
        bar_closed = prev_ts is not None and latest.timestamp != prev_ts

        if prev_ts is None:
            self._last_ts[symbol] = latest.timestamp
            if self.on_bar:
                self.on_bar(symbol, enriched, False)
            return

        if latest.timestamp != prev_ts:
            self._last_ts[symbol] = latest.timestamp
            bar_closed = True

        if self.on_bar:
            self.on_bar(symbol, enriched, bar_closed)

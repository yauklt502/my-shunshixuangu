"""Failover wrapper: auto-switch when primary data source fails."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from src.common import BarPeriod, KlineBar

from .base import DataSource

logger = logging.getLogger(__name__)


class FailoverDataSource:
  def __init__(self, sources: List[DataSource]):
    self.sources = sources

  def fetch_klines(
    self,
    symbol: str,
    period: BarPeriod,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 500,
  ) -> List[KlineBar]:
    for source in self.sources:
      try:
        if not source.health_check():
          continue
        bars = source.fetch_klines(symbol, period, start, end, limit)
        if bars:
          return bars
      except Exception as e:
        logger.warning("Data source %s failed: %s", source.name, e)
    return []

  def fetch_realtime_bar(self, symbol: str, period: BarPeriod) -> Optional[KlineBar]:
    for source in self.sources:
      try:
        if not source.health_check():
          continue
        bar = source.fetch_realtime_bar(symbol, period)
        if bar:
          return bar
      except Exception as e:
        logger.warning("Data source %s failed: %s", source.name, e)
    return None

"""Abstract data source interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.common import BarPeriod, KlineBar


class DataSource(ABC):
    """Base adapter for market data providers."""

    name: str = "base"

    @abstractmethod
    def fetch_klines(
        self,
        symbol: str,
        period: BarPeriod,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[KlineBar]:
        ...

    @abstractmethod
    def fetch_realtime_bar(self, symbol: str, period: BarPeriod) -> Optional[KlineBar]:
        ...

    def health_check(self) -> bool:
        return True

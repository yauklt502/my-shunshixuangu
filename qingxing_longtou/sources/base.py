"""数据源抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from engine.models import MarketSnapshot


class DataSource(ABC):
    name: str = "base"
    label: str = "未命名"

    @abstractmethod
    def available(self) -> bool:
        ...

    @abstractmethod
    def fetch_snapshot(self, trade_date: str | None = None) -> MarketSnapshot:
        ...

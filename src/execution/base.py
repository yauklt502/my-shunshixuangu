"""Abstract broker / executor interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.common import Order, Position, StrategySignal


class Executor(ABC):
    @abstractmethod
    def submit(self, signal: StrategySignal, quantity: int) -> Order:
        ...

    @abstractmethod
    def cancel(self, order_id: str) -> bool:
        ...

    @abstractmethod
    def sync_positions(self) -> List[Position]:
        ...

    @abstractmethod
    def sync_orders(self) -> List[Order]:
        ...

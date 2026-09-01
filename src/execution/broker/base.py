"""Abstract broker adapter — unify mock, REST, and easytrader backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from src.common import Order, OrderStatus, Position


@dataclass
class BrokerFillResult:
    success: bool
    status: OrderStatus
    filled_quantity: int = 0
    filled_price: float = 0.0
    broker_order_id: str = ""
    message: str = ""


class BrokerAdapter(ABC):
    name: str = "base"

    @abstractmethod
    def submit_order(self, order: Order) -> BrokerFillResult:
        ...

    @abstractmethod
    def cancel_order(self, order_id: str, broker_order_id: str = "") -> bool:
        ...

    @abstractmethod
    def query_positions(self) -> List[Position]:
        ...

    @abstractmethod
    def query_orders(self) -> List[Order]:
        ...

    def health_check(self) -> bool:
        return True

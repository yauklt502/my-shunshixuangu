"""Paper-trading broker for live-mode development without real capital."""

from __future__ import annotations

import logging
import uuid
from typing import Dict, List

from src.common import Order, OrderSide, OrderStatus, Position

from .base import BrokerAdapter, BrokerFillResult

logger = logging.getLogger(__name__)


class MockBrokerAdapter(BrokerAdapter):
    name = "mock"

    def __init__(self, initial_cash: float = 1_000_000.0, commission_rate: float = 0.0003):
        self.cash = initial_cash
        self.commission_rate = commission_rate
        self._positions: Dict[str, Position] = {}
        self._orders: Dict[str, Order] = {}

    def submit_order(self, order: Order) -> BrokerFillResult:
        cost = order.price * order.quantity
        commission = cost * self.commission_rate

        if order.side == OrderSide.BUY:
            total = cost + commission
            if self.cash < total:
                return BrokerFillResult(False, OrderStatus.REJECTED, message="资金不足")
            self.cash -= total
            pos = self._positions.get(order.symbol)
            if pos:
                new_qty = pos.quantity + order.quantity
                pos.avg_price = (pos.avg_price * pos.quantity + cost) / new_qty
                pos.quantity = new_qty
                pos.market_value = new_qty * order.price
            else:
                self._positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    avg_price=order.price,
                    market_value=cost,
                )
        else:
            pos = self._positions.get(order.symbol)
            if not pos or pos.quantity < order.quantity:
                return BrokerFillResult(False, OrderStatus.REJECTED, message="持仓不足")
            self.cash += cost - commission
            pos.quantity -= order.quantity
            pos.market_value = pos.quantity * order.price
            if pos.quantity == 0:
                del self._positions[order.symbol]

        broker_id = str(uuid.uuid4())[:12]
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = order.price
        self._orders[order.order_id] = order
        logger.info(
            "Mock broker filled: %s %s %d @ %.2f",
            order.side.value,
            order.symbol,
            order.quantity,
            order.price,
        )
        return BrokerFillResult(
            True,
            OrderStatus.FILLED,
            filled_quantity=order.quantity,
            filled_price=order.price,
            broker_order_id=broker_id,
        )

    def cancel_order(self, order_id: str, broker_order_id: str = "") -> bool:
        order = self._orders.get(order_id)
        if order and order.status == OrderStatus.SUBMITTED:
            order.status = OrderStatus.CANCELLED
            return True
        return False

    def query_positions(self) -> List[Position]:
        return list(self._positions.values())

    def query_orders(self) -> List[Order]:
        return list(self._orders.values())

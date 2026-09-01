"""Live executor with async order queue and broker adapter."""

from __future__ import annotations

import logging
import queue
import threading
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional

from src.common import Order, OrderSide, OrderStatus, Position, SignalType, StrategySignal
from src.execution.broker import BrokerAdapter, create_broker

from .base import Executor

logger = logging.getLogger(__name__)


class LiveExecutor(Executor):
    """Async order queue; delegates to BrokerAdapter (mock/rest/easytrader)."""

    def __init__(
        self,
        broker: Optional[BrokerAdapter] = None,
        on_fill: Optional[Callable[[Order], None]] = None,
    ):
        self.broker = broker or create_broker()
        self.on_fill = on_fill
        self._queue: queue.Queue[Order] = queue.Queue()
        self._orders: Dict[str, Order] = {}
        self._worker = threading.Thread(target=self._process_queue, daemon=True)
        self._worker.start()

    def _process_queue(self) -> None:
        while True:
            order = self._queue.get()
            try:
                result = self.broker.submit_order(order)
                order.status = result.status
                order.filled_quantity = result.filled_quantity
                order.filled_price = result.filled_price
                if result.success and result.status == OrderStatus.FILLED and self.on_fill:
                    self.on_fill(order)
            except Exception as e:
                logger.error("Order failed: %s", e)
                order.status = OrderStatus.REJECTED
            self._queue.task_done()

    def submit(self, signal: StrategySignal, quantity: int) -> Order:
        order_id = str(uuid.uuid4())[:12]
        side = OrderSide.BUY if signal.signal == SignalType.OPEN_LONG else OrderSide.SELL
        order = Order(
            order_id=order_id,
            symbol=signal.symbol,
            side=side,
            quantity=quantity,
            price=signal.price,
            status=OrderStatus.PENDING,
            created_at=signal.timestamp or datetime.now(),
            strategy_id=signal.strategy_id,
        )
        self._orders[order_id] = order
        self._queue.put(order)
        return order

    def cancel(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if order and order.status in (OrderStatus.PENDING, OrderStatus.SUBMITTED):
            if self.broker.cancel_order(order_id):
                order.status = OrderStatus.CANCELLED
                return True
        return False

    def sync_positions(self) -> List[Position]:
        return self.broker.query_positions()

    def sync_orders(self) -> List[Order]:
        broker_orders = self.broker.query_orders()
        return broker_orders or list(self._orders.values())

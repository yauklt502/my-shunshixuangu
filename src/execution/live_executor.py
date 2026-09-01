"""Live executor with async order queue — broker adapter placeholder."""

from __future__ import annotations

import logging
import queue
import threading
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional

from src.common import Order, OrderSide, OrderStatus, Position, SignalType, StrategySignal

from .base import Executor

logger = logging.getLogger(__name__)


class LiveExecutor(Executor):
    """
    Async order queue for live trading.
    Replace _send_to_broker with actual broker API (e.g. 券商原生 API).
    """

    def __init__(self, broker_send: Optional[Callable[[Order], bool]] = None):
        self._queue: queue.Queue[Order] = queue.Queue()
        self._orders: Dict[str, Order] = {}
        self._positions: Dict[str, Position] = {}
        self._broker_send = broker_send or self._mock_broker_send
        self._worker = threading.Thread(target=self._process_queue, daemon=True)
        self._worker.start()

    def _mock_broker_send(self, order: Order) -> bool:
        logger.info("Mock broker: %s %s %d @ %.2f", order.side.value, order.symbol, order.quantity, order.price)
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = order.price
        return True

    def _process_queue(self) -> None:
        while True:
            order = self._queue.get()
            try:
                if self._broker_send(order):
                    order.status = OrderStatus.SUBMITTED
                    self._broker_send(order)
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
            order.status = OrderStatus.CANCELLED
            return True
        return False

    def sync_positions(self) -> List[Position]:
        return list(self._positions.values())

    def sync_orders(self) -> List[Order]:
        return list(self._orders.values())

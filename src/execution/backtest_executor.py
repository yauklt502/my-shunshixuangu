"""Simulated matching for backtest — never calls real broker APIs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List

from src.common import Order, OrderSide, OrderStatus, Position, SignalType, StrategySignal

from .base import Executor


class BacktestExecutor(Executor):
    def __init__(self, initial_cash: float = 1_000_000.0, commission_rate: float = 0.0003):
        self.cash = initial_cash
        self.commission_rate = commission_rate
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.trades: List[dict] = []

    def submit(self, signal: StrategySignal, quantity: int) -> Order:
        order_id = str(uuid.uuid4())[:12]
        side = OrderSide.BUY if signal.signal == SignalType.OPEN_LONG else OrderSide.SELL
        order = Order(
            order_id=order_id,
            symbol=signal.symbol,
            side=side,
            quantity=quantity,
            price=signal.price,
            status=OrderStatus.SUBMITTED,
            created_at=signal.timestamp or datetime.now(),
            strategy_id=signal.strategy_id,
        )
        self._fill(order)
        self.orders[order_id] = order
        return order

    def _fill(self, order: Order) -> None:
        cost = order.price * order.quantity
        commission = cost * self.commission_rate

        if order.side == OrderSide.BUY:
            total = cost + commission
            if self.cash < total:
                order.status = OrderStatus.REJECTED
                return
            self.cash -= total
            pos = self.positions.get(order.symbol)
            if pos:
                new_qty = pos.quantity + order.quantity
                pos.avg_price = (pos.avg_price * pos.quantity + cost) / new_qty
                pos.quantity = new_qty
                pos.market_value = new_qty * order.price
            else:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    avg_price=order.price,
                    market_value=cost,
                )
        else:
            pos = self.positions.get(order.symbol)
            if not pos or pos.quantity < order.quantity:
                order.status = OrderStatus.REJECTED
                return
            proceeds = cost - commission
            self.cash += proceeds
            pnl = (order.price - pos.avg_price) * order.quantity - commission
            pos.quantity -= order.quantity
            pos.market_value = pos.quantity * order.price
            if pos.quantity == 0:
                del self.positions[order.symbol]

        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = order.price
        self.trades.append(
            {
                "order_id": order.order_id,
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": order.quantity,
                "price": order.price,
                "strategy_id": order.strategy_id,
                "timestamp": (order.created_at.isoformat() if order.created_at else None),
            }
        )

    def cancel(self, order_id: str) -> bool:
        order = self.orders.get(order_id)
        if order and order.status == OrderStatus.SUBMITTED:
            order.status = OrderStatus.CANCELLED
            return True
        return False

    def sync_positions(self) -> List[Position]:
        return list(self.positions.values())

    def sync_orders(self) -> List[Order]:
        return list(self.orders.values())

    @property
    def total_equity(self) -> float:
        pos_value = sum(p.market_value for p in self.positions.values())
        return self.cash + pos_value

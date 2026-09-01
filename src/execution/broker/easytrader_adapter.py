"""easytrader wrapper for domestic broker clients (optional dependency)."""

from __future__ import annotations

import logging
import os
from typing import List, Optional

from src.common import Order, OrderSide, OrderStatus, Position

from .base import BrokerAdapter, BrokerFillResult

logger = logging.getLogger(__name__)


class EasyTraderAdapter(BrokerAdapter):
    """
    Requires: pip install easytrader
    Env: BROKER_CLIENT (yh_client/ht_client/etc), BROKER_ACCOUNT
    Note: easytrader typically needs a running broker desktop client on Windows.
    """

    name = "easytrader"

    def __init__(self, client_type: str | None = None):
        self.client_type = client_type or os.environ.get("BROKER_CLIENT", "yh_client")
        self._user = None
        try:
            import easytrader

            self._user = easytrader.use(self.client_type)
            self._user.prepare(os.environ.get("BROKER_ACCOUNT", ""))
        except ImportError:
            logger.warning("easytrader not installed — adapter disabled")
        except Exception as e:
            logger.warning("easytrader init failed: %s", e)

    def health_check(self) -> bool:
        return self._user is not None

    def submit_order(self, order: Order) -> BrokerFillResult:
        if not self._user:
            return BrokerFillResult(False, OrderStatus.REJECTED, message="easytrader 未就绪")

        try:
            if order.side == OrderSide.BUY:
                result = self._user.buy(order.symbol, price=order.price, amount=order.quantity)
            else:
                result = self._user.sell(order.symbol, price=order.price, amount=order.quantity)
            return BrokerFillResult(
                True,
                OrderStatus.SUBMITTED,
                filled_quantity=order.quantity,
                filled_price=order.price,
                broker_order_id=str(result.get("entrust_no", "")),
                message="委托已提交",
            )
        except Exception as e:
            logger.error("easytrader order failed: %s", e)
            return BrokerFillResult(False, OrderStatus.REJECTED, message=str(e))

    def cancel_order(self, order_id: str, broker_order_id: str = "") -> bool:
        if not self._user:
            return False
        try:
            self._user.cancel_entrust(broker_order_id or order_id)
            return True
        except Exception:
            return False

    def query_positions(self) -> List[Position]:
        if not self._user:
            return []
        try:
            positions = self._user.position
            return [
                Position(
                    symbol=p.get("证券代码", ""),
                    quantity=int(float(p.get("股票余额", 0))),
                    avg_price=float(p.get("成本价", 0)),
                    market_value=float(p.get("市值", 0)),
                )
                for p in positions
            ]
        except Exception:
            return []

    def query_orders(self) -> List[Order]:
        return []

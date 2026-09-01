"""Generic REST broker gateway adapter."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import List

from src.common import Order, OrderStatus, Position

from .base import BrokerAdapter, BrokerFillResult

logger = logging.getLogger(__name__)


class RestBrokerAdapter(BrokerAdapter):
    """
    Connect to a broker HTTP gateway.
    Env: BROKER_API_URL, BROKER_API_TOKEN
    Expected endpoints:
      POST /orders  {symbol, side, quantity, price}
      DELETE /orders/{id}
      GET /positions
      GET /orders
    """

    name = "rest"

    def __init__(
        self,
        api_url: str | None = None,
        api_token: str | None = None,
        timeout: float = 10.0,
    ):
        self.api_url = (api_url or os.environ.get("BROKER_API_URL", "")).rstrip("/")
        self.api_token = api_token or os.environ.get("BROKER_API_TOKEN", "")
        self.timeout = timeout

    def health_check(self) -> bool:
        if not self.api_url:
            return False
        try:
            self._request("GET", "/health")
            return True
        except Exception:
            return bool(self.api_url)

    def submit_order(self, order: Order) -> BrokerFillResult:
        if not self.api_url:
            return BrokerFillResult(False, OrderStatus.REJECTED, message="BROKER_API_URL 未配置")

        payload = {
            "client_order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "price": order.price,
            "strategy_id": order.strategy_id,
        }
        try:
            resp = self._request("POST", "/orders", payload)
            status = OrderStatus(resp.get("status", "submitted"))
            return BrokerFillResult(
                success=resp.get("success", True),
                status=status,
                filled_quantity=int(resp.get("filled_quantity", 0)),
                filled_price=float(resp.get("filled_price", 0)),
                broker_order_id=str(resp.get("broker_order_id", "")),
                message=resp.get("message", ""),
            )
        except Exception as e:
            logger.error("REST broker submit failed: %s", e)
            return BrokerFillResult(False, OrderStatus.REJECTED, message=str(e))

    def cancel_order(self, order_id: str, broker_order_id: str = "") -> bool:
        try:
            oid = broker_order_id or order_id
            self._request("DELETE", f"/orders/{oid}")
            return True
        except Exception as e:
            logger.error("REST broker cancel failed: %s", e)
            return False

    def query_positions(self) -> List[Position]:
        try:
            resp = self._request("GET", "/positions")
            items = resp if isinstance(resp, list) else resp.get("positions", [])
            return [
                Position(
                    symbol=p["symbol"],
                    quantity=int(p["quantity"]),
                    avg_price=float(p["avg_price"]),
                    market_value=float(p.get("market_value", 0)),
                )
                for p in items
            ]
        except Exception as e:
            logger.warning("REST broker query positions failed: %s", e)
            return []

    def query_orders(self) -> List[Order]:
        return []

    def _request(self, method: str, path: str, body: dict | None = None):
        url = f"{self.api_url}{path}"
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.api_token:
            req.add_header("Authorization", f"Bearer {self.api_token}")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}

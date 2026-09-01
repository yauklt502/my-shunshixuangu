"""Broker factory — select adapter from config or environment."""

from __future__ import annotations

import os

from src.common import BrokerConfig

from .base import BrokerAdapter
from .easytrader_adapter import EasyTraderAdapter
from .mock_broker import MockBrokerAdapter
from .rest_broker import RestBrokerAdapter


def create_broker(config: BrokerConfig | None = None) -> BrokerAdapter:
    config = config or BrokerConfig()
    broker_type = os.environ.get("BROKER_TYPE", config.broker_type).lower()

    if broker_type == "rest":
        return RestBrokerAdapter(api_url=config.api_url, api_token=config.api_token)
    if broker_type == "easytrader":
        return EasyTraderAdapter(client_type=config.client_type)
    return MockBrokerAdapter(initial_cash=config.initial_cash)

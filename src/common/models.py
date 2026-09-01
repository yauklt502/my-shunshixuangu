"""Core domain models shared across all layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class Environment(Enum):
    BACKTEST = "backtest"
    LIVE = "live"


class SignalType(Enum):
    NONE = "none"
    OPEN_LONG = "open_long"
    CLOSE = "close"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class BarPeriod(Enum):
    MIN1 = "1min"
    MIN5 = "5min"
    MIN60 = "60min"
    DAILY = "daily"


@dataclass
class KlineBar:
    """Standardized K-line bar with optional pre-computed indicators."""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    period: BarPeriod = BarPeriod.DAILY
    indicators: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "period": self.period.value,
            "indicators": self.indicators,
        }


@dataclass
class StrategySignal:
    strategy_id: str
    symbol: str
    signal: SignalType
    timestamp: Optional[datetime]
    price: float
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Order:
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    filled_quantity: int = 0
    filled_price: float = 0.0
    strategy_id: str = ""


@dataclass
class Position:
    symbol: str
    quantity: int
    avg_price: float
    market_value: float = 0.0


@dataclass
class AccountState:
    cash: float
    total_equity: float
    positions: List[Position] = field(default_factory=list)
    daily_pnl: float = 0.0
    consecutive_losses: int = 0


@dataclass
class BacktestResult:
    strategy_id: str
    total_return: float
    win_rate: float
    profit_loss_ratio: float
    max_drawdown: float
    equity_curve: List[float] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)

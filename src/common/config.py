"""Global configuration for backtest and live environments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .models import Environment


@dataclass
class RiskConfig:
    max_position_per_symbol: float = 0.2  # 单股最大仓位占比
    max_total_position: float = 0.8  # 总仓位上限
    max_daily_loss: float = 0.05  # 单日最大亏损
    max_consecutive_losses: int = 3  # 连续亏损暂停
    exclude_st: bool = True
    exclude_star_market: bool = True  # 科创板
    min_order_interval_seconds: int = 60  # 防重复下单
    avoid_limit_up_down: bool = True


@dataclass
class DataSourceConfig:
    primary: str = "tushare"
    fallbacks: List[str] = field(default_factory=lambda: ["mootdx"])
    cache_ttl_seconds: int = 300
    cache_dir: str = ".cache/data"


@dataclass
class StorageConfig:
    timeseries_dir: str = "data/timeseries"
    relational_db: str = "data/trading.db"
    log_dir: str = "data/logs"


@dataclass
class AppConfig:
    environment: Environment = Environment.BACKTEST
    initial_capital: float = 1_000_000.0
    risk: RiskConfig = field(default_factory=RiskConfig)
    data_source: DataSourceConfig = field(default_factory=DataSourceConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)

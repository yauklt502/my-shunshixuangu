"""Relational storage for trades, backtest reports, and config."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.common import BacktestResult


class RelationalStore:
    def __init__(self, db_path: str = "data/trading.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS trade_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT,
                    symbol TEXT,
                    side TEXT,
                    quantity INTEGER,
                    price REAL,
                    strategy_id TEXT,
                    timestamp TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS signal_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT,
                    symbol TEXT,
                    signal TEXT,
                    price REAL,
                    reason TEXT,
                    timestamp TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS backtest_report (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT,
                    total_return REAL,
                    win_rate REAL,
                    profit_loss_ratio REAL,
                    max_drawdown REAL,
                    equity_curve TEXT,
                    trades TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS strategy_config (
                    strategy_id TEXT PRIMARY KEY,
                    params TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def log_trade(self, trade: Dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO trade_log (order_id, symbol, side, quantity, price, strategy_id, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    trade.get("order_id"),
                    trade.get("symbol"),
                    trade.get("side"),
                    trade.get("quantity"),
                    trade.get("price"),
                    trade.get("strategy_id"),
                    trade.get("timestamp"),
                ),
            )

    def log_signal(self, signal: Dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO signal_log (strategy_id, symbol, signal, price, reason, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    signal.get("strategy_id"),
                    signal.get("symbol"),
                    signal.get("signal"),
                    signal.get("price"),
                    signal.get("reason"),
                    signal.get("timestamp"),
                ),
            )

    def save_backtest_report(self, result: BacktestResult) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO backtest_report "
                "(strategy_id, total_return, win_rate, profit_loss_ratio, max_drawdown, equity_curve, trades) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    result.strategy_id,
                    result.total_return,
                    result.win_rate,
                    result.profit_loss_ratio,
                    result.max_drawdown,
                    json.dumps(result.equity_curve),
                    json.dumps(result.trades),
                ),
            )

    def get_backtest_reports(self, strategy_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            if strategy_id:
                rows = conn.execute(
                    "SELECT * FROM backtest_report WHERE strategy_id = ? ORDER BY id DESC",
                    (strategy_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM backtest_report ORDER BY id DESC").fetchall()
        return [dict(zip(["id", "strategy_id", "total_return", "win_rate", "profit_loss_ratio",
                          "max_drawdown", "equity_curve", "trades", "created_at"], r)) for r in rows]

    def set_strategy_params(self, strategy_id: str, params: Dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO strategy_config (strategy_id, params, updated_at) VALUES (?, ?, ?)",
                (strategy_id, json.dumps(params), datetime.now().isoformat()),
            )

"""Structured logging for signals, orders, and fills."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class AuditLogger:
    def __init__(self, log_dir: str = "data/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._setup_file_logger("signals", "signals.log")
        self._setup_file_logger("orders", "orders.log")
        self._setup_file_logger("fills", "fills.log")

    def _setup_file_logger(self, name: str, filename: str) -> logging.Logger:
        logger = logging.getLogger(f"audit.{name}")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.FileHandler(self.log_dir / filename, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)
        return logger

    def log_event(self, category: str, event: Dict[str, Any]) -> None:
        event["logged_at"] = datetime.now().isoformat()
        logger = logging.getLogger(f"audit.{category}")
        logger.info(json.dumps(event, ensure_ascii=False, default=str))

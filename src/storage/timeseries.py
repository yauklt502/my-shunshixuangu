"""Time-series storage for K-line and tick data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.common import BarPeriod, KlineBar


class TimeseriesStore:
    def __init__(self, base_dir: str = "data/timeseries"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str, period: BarPeriod) -> Path:
        safe = symbol.replace("/", "_")
        return self.base_dir / f"{safe}_{period.value}.json"

    def save_bars(self, bars: List[KlineBar]) -> None:
        if not bars:
            return
        path = self._path(bars[0].symbol, bars[0].period)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([b.to_dict() for b in bars], f, ensure_ascii=False)

    def load_bars(self, symbol: str, period: BarPeriod) -> Optional[List[KlineBar]]:
        path = self._path(symbol, period)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [
            KlineBar(
                symbol=d["symbol"],
                timestamp=datetime.fromisoformat(d["timestamp"]),
                open=d["open"],
                high=d["high"],
                low=d["low"],
                close=d["close"],
                volume=d["volume"],
                period=BarPeriod(d["period"]),
                indicators=d.get("indicators", {}),
            )
            for d in data
        ]

"""Pre-compute and cache indicators for strategy consumption."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.common import BarPeriod, KlineBar

from .indicators import compute_all_indicators


class IndicatorPreprocessor:
    """Pre-compute indicators and persist for fast strategy reads."""

    def __init__(self, cache_dir: str = "data/indicators"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory: Dict[str, List[KlineBar]] = {}

    def _cache_key(self, symbol: str, period: BarPeriod) -> str:
        return f"{symbol}_{period.value}"

    def process(self, bars: List[KlineBar], use_cache: bool = True) -> List[KlineBar]:
        if not bars:
            return bars

        symbol = bars[0].symbol
        period = bars[0].period
        key = self._cache_key(symbol, period)

        if use_cache and key in self._memory:
            return self._memory[key]

        enriched = compute_all_indicators(bars)
        self._memory[key] = enriched

        if use_cache:
            path = self.cache_dir / f"{key}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump([b.to_dict() for b in enriched], f, ensure_ascii=False)

        return enriched

    def load_cached(self, symbol: str, period: BarPeriod) -> Optional[List[KlineBar]]:
        key = self._cache_key(symbol, period)
        if key in self._memory:
            return self._memory[key]

        path = self.cache_dir / f"{key}.json"
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        bars = [
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
        self._memory[key] = bars
        return bars

"""In-memory + file cache for data source requests."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Optional


class DataCache:
    def __init__(self, cache_dir: str = ".cache/data", ttl_seconds: int = 300):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self._memory: dict[str, tuple[float, Any]] = {}

    def _key(self, namespace: str, params: dict) -> str:
        raw = f"{namespace}:{json.dumps(params, sort_keys=True, default=str)}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, namespace: str, params: dict) -> Optional[Any]:
        key = self._key(namespace, params)
        if key in self._memory:
            ts, value = self._memory[key]
            if time.time() - ts < self.ttl_seconds:
                return value
            del self._memory[key]

        path = self.cache_dir / f"{key}.json"
        if path.exists():
            age = time.time() - path.stat().st_mtime
            if age < self.ttl_seconds:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._memory[key] = (time.time(), data)
                return data
        return None

    def set(self, namespace: str, params: dict, value: Any) -> None:
        key = self._key(namespace, params)
        self._memory[key] = (time.time(), value)
        path = self.cache_dir / f"{key}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, default=str)

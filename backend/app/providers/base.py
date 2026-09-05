from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MarketProvider(ABC):
    name: str
    display_name: str

    @abstractmethod
    def health(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def limit_up_pool(self, trade_date: str) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def quote(self, code: str) -> dict[str, Any]:
        ...

    @abstractmethod
    def depth(self, code: str) -> dict[str, Any]:
        ...

    @abstractmethod
    def daily_bars(self, code: str, count: int = 120) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def minute_bars(self, code: str, period: str = "1m") -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def intraday(self, code: str) -> list[dict[str, Any]]:
        ...


def normalize_code(code: str) -> tuple[str, str]:
    c = code.strip().lower().replace(".", "")
    if c.startswith(("sh", "sz", "bj")):
        return c[:2], c[2:].zfill(6)[-6:]
    pure = c.zfill(6)[-6:]
    if pure.startswith(("6", "9")):
        return "sh", pure
    if pure.startswith(("4", "8")):
        return "bj", pure
    return "sz", pure


def to_tdx_code(code: str) -> str:
    m, c = normalize_code(code)
    return f"{m}{c}"


def to_em_secid(code: str) -> str:
    m, c = normalize_code(code)
    return f"{1 if m == 'sh' else 0}.{c}"
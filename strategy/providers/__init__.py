"""行情数据源公共工具。"""

from __future__ import annotations

from typing import Any


def secid_em(code: str) -> str | None:
    """东方财富 secid。过滤北交所等易触发异常的代码。"""
    c = str(code or "").zfill(6)
    if not c.isdigit() or len(c) != 6:
        return None
    # 只要沪深主板/创业板/科创板常见号段
    if c.startswith(("5", "9")):  # 基金/北交所等跳过竞价批量
        return None
    if c.startswith("6"):
        return f"1.{c}"
    return f"0.{c}"


def tencent_symbol(code: str) -> str | None:
    c = str(code or "").zfill(6)
    if not c.isdigit() or len(c) != 6:
        return None
    if c.startswith(("5", "9", "4", "8")):
        return None
    if c.startswith("6"):
        return f"sh{c}"
    return f"sz{c}"


def sina_symbol(code: str) -> str | None:
    return tencent_symbol(code)


def num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def quote_fields(
    *,
    price: float,
    change_pct: float,
    open_price: float,
    pre_close: float,
    turnover: float = 0.0,
    name: str = "",
    code: str = "",
) -> dict[str, Any]:
    """统一成东财 ulist 近似字段，供引擎复用。"""
    return {
        "f2": price,
        "f3": change_pct,
        "f8": turnover,
        "f12": code,
        "f14": name,
        "f17": open_price,
        "f18": pre_close,
        "f62": None,
    }

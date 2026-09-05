"""多数据源注册。"""

from __future__ import annotations

from typing import Any

from backend.sources import eastmoney, tdx_eltdx, tonghuashun

REGISTRY = {
    "eastmoney": eastmoney,
    "tonghuashun": tonghuashun,
    "tdx": tdx_eltdx,
}


def get_module(source: str):
    key = (source or "eastmoney").strip().lower()
    if key in ("tongdaxin", "tdx", "eltdx", "通达信"):
        return REGISTRY["tdx"]
    if key in ("ths", "tonghuashun", "10jqka", "同花顺"):
        return REGISTRY["tonghuashun"]
    if key in ("em", "eastmoney", "东方财富"):
        return REGISTRY["eastmoney"]
    return REGISTRY.get(key, REGISTRY["eastmoney"])


async def source_health() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for sid, mod in REGISTRY.items():
        try:
            info = await mod.health()
        except Exception as exc:  # noqa: BLE001
            info = {"ok": False, "name": sid, "detail": str(exc)}
        out.append({"id": sid, **info})
    return out
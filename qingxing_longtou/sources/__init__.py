"""数据源注册与自动选择。"""

from __future__ import annotations

from sources.base import DataSource
from sources.eastmoney import EastMoneySource
from sources.tdx import TdxSource
from sources.tonghuashun import TonghuashunSource


def all_sources() -> list[DataSource]:
    return [EastMoneySource(), TonghuashunSource(), TdxSource()]


def get_source(name: str) -> DataSource:
    key = (name or "auto").strip().lower()
    mapping = {s.name: s for s in all_sources()}
    if key in ("auto", ""):
        # 优先东方财富（公开可用），其次同花顺，再次通达信
        for preferred in ("eastmoney", "tonghuashun", "tdx"):
            src = mapping[preferred]
            if src.available():
                return src
        return mapping["eastmoney"]
    if key not in mapping:
        raise KeyError(f"未知数据源: {name}")
    return mapping[key]


def source_status() -> list[dict[str, str | bool]]:
    out = []
    for s in all_sources():
        try:
            ok = s.available()
            detail = "可用" if ok else "不可用"
        except Exception as exc:
            ok = False
            detail = str(exc)
        out.append({"name": s.name, "label": s.label, "available": ok, "detail": detail})
    return out

"""硬过滤：把「坚决不做」写死，避免把噪声当成买点。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .config import DEFAULT_CONFIG, StrategyConfig


@dataclass(frozen=True)
class CandidateBasics:
    code: str
    name: str
    theme_tags: Sequence[str]
    is_st: bool = False
    is_limit_up_open: bool = False  # 一字已经买不到，不做追板
    chasing: bool = False  # 高开/大涨后追价
    system_mismatch: bool = False  # 明确「不符合系统」
    holding_count: int = 0
    total_position: float = 0.0
    full_position: bool = False


@dataclass(frozen=True)
class FilterResult:
    passed: bool
    reasons: tuple[str, ...]


def hard_filter(b: CandidateBasics, cfg: StrategyConfig = DEFAULT_CONFIG) -> FilterResult:
    reasons: list[str] = []
    if b.is_st:
        reasons.append("ST 默认不做")
    if b.full_position or b.total_position >= cfg.max_total_position:
        reasons.append("满仓/仓位超限，禁止新开仓")
    if b.holding_count >= cfg.max_names:
        reasons.append("已达十全十美持股上限，只调仓不做新票")
    if b.chasing:
        reasons.append("少追涨、多低吸：当前是追涨价")
    if b.is_limit_up_open:
        reasons.append("一字买不到，不追板")
    if b.system_mismatch:
        reasons.append("不符合系统的行情坚决不做")
    return FilterResult(passed=not reasons, reasons=tuple(reasons))

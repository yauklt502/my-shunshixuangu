"""硬过滤：不过滤掉的票不进入评分。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .config import DEFAULT_CONFIG, StrategyConfig


@dataclass(frozen=True)
class CandidateBasics:
    code: str
    name: str
    circ_mv: float  # 亿元
    is_st: bool = False
    theme_tags: Sequence[str] = ()
    is_yizi_rear: bool = False  # 一字连板后排
    board_height: int = 0
    market_max_board: int = 0
    relative_to_60d_low: float = 0.0  # (price/low60 - 1)


@dataclass(frozen=True)
class FilterResult:
    passed: bool
    reasons: tuple[str, ...]


def hard_filter(
    c: CandidateBasics,
    cfg: StrategyConfig = DEFAULT_CONFIG,
    allow_st: bool = False,
) -> FilterResult:
    reasons: list[str] = []

    if c.is_st and not allow_st:
        reasons.append("ST默认剔除")

    if not (cfg.circ_mv_min <= c.circ_mv <= cfg.circ_mv_max):
        reasons.append(
            f"流通市值{c.circ_mv:.1f}亿不在[{cfg.circ_mv_min},{cfg.circ_mv_max}]"
        )

    if c.is_yizi_rear:
        reasons.append("一字连板后排禁做")

    theme_hit = _theme_hit(c.theme_tags, cfg.mainline_keywords)
    if not theme_hit:
        reasons.append("未挂靠当期主线题材")

    # 动态天花板：接近市场最高板危险区
    if c.market_max_board > 0 and c.board_height > 0:
        danger = max(3, int(c.market_max_board * 0.7))
        if c.board_height >= danger and c.board_height >= c.market_max_board:
            reasons.append(f"已处市场最高板危险区(≥{danger})")

    if c.relative_to_60d_low > cfg.start_premium_max and c.board_height <= 1:
        reasons.append("启动位置相对60日低点过高")

    return FilterResult(passed=len(reasons) == 0, reasons=tuple(reasons))


def _theme_hit(tags: Sequence[str], keywords: Sequence[str]) -> bool:
    blob = " ".join(tags).upper()
    for kw in keywords:
        if kw.upper() in blob:
            return True
    return False


def is_mainline_theme(
    tags: Sequence[str],
    cfg: StrategyConfig = DEFAULT_CONFIG,
) -> bool:
    return _theme_hit(tags, cfg.mainline_keywords)

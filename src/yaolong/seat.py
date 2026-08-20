"""龙虎榜席位模式：真合力 vs 假点火。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from .config import DEFAULT_CONFIG, StrategyConfig


class SeatSignal(str, Enum):
    TRUE_SYNERGY = "TRUE_SYNERGY"  # 真合力
    FAKE_IGNITE = "FAKE_IGNITE"  # 假点火
    DAY_TRIP = "DAY_TRIP"  # 一日游嫌疑
    NEUTRAL = "NEUTRAL"  # 信息不足/中性
    DISTRIBUTION = "DISTRIBUTION"  # 出货主导


@dataclass(frozen=True)
class SeatRow:
    name: str
    buy: float  # 万元
    sell: float = 0.0


@dataclass(frozen=True)
class SeatBook:
    buys: Sequence[SeatRow]
    sells: Sequence[SeatRow] = ()


def classify_seat_pattern(
    book: SeatBook,
    cfg: StrategyConfig = DEFAULT_CONFIG,
) -> SeatSignal:
    if not book.buys:
        return SeatSignal.NEUTRAL

    total_buy = sum(max(0.0, r.buy) for r in book.buys)
    total_sell = sum(max(0.0, r.sell) for r in book.sells)
    if total_buy <= 0:
        return SeatSignal.NEUTRAL

    top = max(book.buys, key=lambda r: r.buy)
    top_ratio = top.buy / total_buy
    famous = _count_famous(book.buys, cfg.famous_seat_keywords)

    # 买卖两端同名/同帮系双向大额 → 做T噪声，偏假点火
    if _bidirectional_noise(book):
        return SeatSignal.FAKE_IGNITE

    if total_sell > total_buy * 1.2 and famous == 0:
        return SeatSignal.DISTRIBUTION

    # 单席畸高 + 卖盘汹涌 → 假点火/一日游
    if top_ratio >= cfg.seat_single_buy_max_ratio:
        if _mostly_sold_next_proxy(top, book.sells):
            return SeatSignal.DAY_TRIP
        return SeatSignal.FAKE_IGNITE

    if famous >= cfg.seat_min_famous and top_ratio < 0.40:
        return SeatSignal.TRUE_SYNERGY

    if famous >= 1 and top_ratio < 0.45 and total_buy >= total_sell:
        return SeatSignal.TRUE_SYNERGY

    return SeatSignal.NEUTRAL


def _count_famous(rows: Sequence[SeatRow], keywords: Sequence[str]) -> int:
    n = 0
    for r in rows:
        name = r.name
        if any(k in name for k in keywords):
            n += 1
    return n


def _bidirectional_noise(book: SeatBook) -> bool:
    buy_names = {r.name for r in book.buys if r.buy > 0}
    sell_names = {r.name for r in book.sells if r.sell > 0}
    both = buy_names & sell_names
    if len(both) < 2:
        return False
    # 同一席位大买大卖
    noisy = 0
    sell_map = {r.name: r.sell for r in book.sells}
    for r in book.buys:
        s = sell_map.get(r.name, 0.0)
        if r.buy > 0 and s > 0 and min(r.buy, s) / max(r.buy, s) > 0.4:
            noisy += 1
    return noisy >= 2


def _mostly_sold_next_proxy(top: SeatRow, sells: Sequence[SeatRow]) -> bool:
    """同日卖出榜出现同名大额，作为一日游代理特征。"""
    for s in sells:
        if s.name == top.name and s.sell >= top.buy * 0.6:
            return True
    return False

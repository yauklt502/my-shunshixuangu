"""六维评分卡。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .config import DEFAULT_CONFIG, StrategyConfig
from .filters import CandidateBasics, is_mainline_theme
from .seat import SeatBook, SeatSignal, classify_seat_pattern


@dataclass(frozen=True)
class PatternInput:
    stage: str  # startup / accelerate / climax / top / first_yin
    turnover: float
    volume_vs_5d: float  # 当日量 / 5日均量
    above_ma5: bool = True
    above_ma10: bool = True
    long_upper_shadow: bool = False
    limit_up: bool = False
    broken_then_seal: bool = False


@dataclass(frozen=True)
class LeaderInput:
    is_theme_first_mover: bool = False
    highest_board_in_theme: bool = False
    best_resilience: bool = False
    follower_count: int = 0  # 同题材跟风涨停数
    uniqueness: float = 0.5  # 0~1 主观辨识度，研究时可人工打


@dataclass(frozen=True)
class ScoreBreakdown:
    theme: float
    mcap: float
    leader: float
    volume: float
    seat: float
    pattern: float
    total: float
    seat_signal: SeatSignal
    notes: tuple[str, ...]

    @property
    def tradable(self) -> bool:
        return self.total >= DEFAULT_CONFIG.open_score_min


def score_candidate(
    basics: CandidateBasics,
    pattern: PatternInput,
    leader: LeaderInput,
    seat_book: Optional[SeatBook] = None,
    cfg: StrategyConfig = DEFAULT_CONFIG,
) -> ScoreBreakdown:
    notes: list[str] = []

    theme = _score_theme(basics.theme_tags, cfg)
    mcap = _score_mcap(basics.circ_mv, cfg)
    leader_s = _score_leader(leader)
    volume = _score_volume(pattern, cfg)
    seat_signal = (
        classify_seat_pattern(seat_book, cfg) if seat_book is not None else SeatSignal.NEUTRAL
    )
    seat = _score_seat(seat_signal)
    pattern_s = _score_pattern(pattern, cfg)

    if seat_signal in {SeatSignal.FAKE_IGNITE, SeatSignal.DAY_TRIP}:
        notes.append("席位假点火/一日游：当日禁追高")
        # 席位一票否决追高：席位分压到地板，总分很难过线
        seat = min(seat, 20.0)

    if pattern.stage == "top":
        notes.append("见顶阶段：禁买")
        pattern_s = min(pattern_s, 25.0)

    total = (
        cfg.w_theme * theme
        + cfg.w_mcap * mcap
        + cfg.w_leader * leader_s
        + cfg.w_volume * volume
        + cfg.w_seat * seat
        + cfg.w_pattern * pattern_s
    )

    return ScoreBreakdown(
        theme=theme,
        mcap=mcap,
        leader=leader_s,
        volume=volume,
        seat=seat,
        pattern=pattern_s,
        total=round(total, 2),
        seat_signal=seat_signal,
        notes=tuple(notes),
    )


def _score_theme(tags: Sequence[str], cfg: StrategyConfig) -> float:
    if not tags:
        return 30.0
    if not is_mainline_theme(tags, cfg):
        return 25.0
    blob = " ".join(tags)
    hard_hits = sum(
        1
        for k in ("AI", "算力", "机器人", "绿电", "半导体", "商业航天", "控制权")
        if k in blob or k.upper() in blob.upper()
    )
    return min(100.0, 70.0 + hard_hits * 8.0)


def _score_mcap(mv: float, cfg: StrategyConfig) -> float:
    if cfg.circ_mv_sweet_low <= mv <= cfg.circ_mv_sweet_high:
        return 95.0
    if cfg.circ_mv_min <= mv < cfg.circ_mv_sweet_low:
        return 75.0
    if cfg.circ_mv_sweet_high < mv <= cfg.circ_mv_max:
        return 70.0
    return 20.0


def _score_leader(leader: LeaderInput) -> float:
    s = 40.0
    if leader.is_theme_first_mover:
        s += 15
    if leader.highest_board_in_theme:
        s += 20
    if leader.best_resilience:
        s += 10
    s += min(15.0, leader.follower_count * 3.0)
    s += leader.uniqueness * 20.0
    return min(100.0, s)


def _score_volume(p: PatternInput, cfg: StrategyConfig) -> float:
    t = p.turnover
    if t >= cfg.turnover_danger:
        return 25.0
    if cfg.turnover_healthy_low <= t <= cfg.turnover_healthy_high:
        base = 85.0
    elif 5 <= t < cfg.turnover_healthy_low:
        base = 65.0
    elif cfg.turnover_healthy_high < t < cfg.turnover_danger:
        base = 55.0
    else:
        base = 40.0

    if p.stage == "startup" and p.volume_vs_5d >= 1.5:
        base += 10
    if p.stage == "accelerate" and p.broken_then_seal:
        base += 8
    if p.stage == "first_yin" and p.volume_vs_5d <= 1.1:
        base += 8
    return min(100.0, base)


def _score_seat(sig: SeatSignal) -> float:
    return {
        SeatSignal.TRUE_SYNERGY: 92.0,
        SeatSignal.NEUTRAL: 60.0,
        SeatSignal.DISTRIBUTION: 35.0,
        SeatSignal.FAKE_IGNITE: 15.0,
        SeatSignal.DAY_TRIP: 10.0,
    }[sig]


def _score_pattern(p: PatternInput, cfg: StrategyConfig) -> float:
    stage_base = {
        "startup": 80.0,
        "accelerate": 85.0,
        "climax": 55.0,
        "first_yin": 70.0,
        "top": 20.0,
    }.get(p.stage, 50.0)

    if p.long_upper_shadow and p.stage in {"climax", "accelerate"}:
        stage_base -= 15
    if not p.above_ma5 and p.stage != "first_yin":
        stage_base -= 20
    if p.stage == "first_yin" and not (p.above_ma5 or p.above_ma10):
        stage_base -= 25
    if p.limit_up and p.stage in {"startup", "accelerate"}:
        stage_base += 5
    return max(0.0, min(100.0, stage_base))

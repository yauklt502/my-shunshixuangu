"""买点质量评分：主题 / 位置 / 形态 / 风险。"""

from __future__ import annotations

from dataclasses import dataclass

from .config import DEFAULT_CONFIG, StrategyConfig


@dataclass(frozen=True)
class ScoreBreakdown:
    theme: float
    location: float
    setup: float
    risk: float
    total: float


def _clip(x: float) -> float:
    return max(0.0, min(100.0, x))


def score_setup(snap, cfg: StrategyConfig = DEFAULT_CONFIG) -> ScoreBreakdown:
    tags = {str(t) for t in snap.basics.theme_tags}
    hit = any(k in "".join(tags) or k in snap.basics.name for k in cfg.mainline_keywords)
    theme = 88.0 if (snap.mainline or hit) else (72.0 if snap.quality_tech else 45.0)
    if snap.quality_tech and snap.low_position:
        theme = max(theme, 80.0)

    location = 50.0
    if snap.low_position:
        location += 25
    if snap.near_day_low:
        location += 15
    if snap.stretched_up:
        location -= 35
    if snap.day_change <= -0.03:
        location += 10

    setup = 40.0
    if snap.stabilize_ok:
        setup += 20
    if snap.flag_breakout:
        setup += 25
    elif snap.flag_pattern:
        setup += 10
    if snap.start_seed:
        setup += 20
    if snap.whack_a_mole:
        setup += 15
    if snap.consolidating and not snap.stabilize_ok:
        setup -= 15
    if snap.liked_but_dead:
        setup -= 20

    risk = 70.0
    if snap.basics.chasing:
        risk -= 40
    if snap.basics.full_position:
        risk -= 50
    if snap.probe:
        risk -= 10
    if snap.has_core and snap.t0_setup:
        risk += 10
    if snap.whack_a_mole:
        risk -= 15  # 快进快出本身风险高，靠纪律补

    theme, location, setup, risk = map(_clip, (theme, location, setup, risk))
    total = (
        cfg.w_theme * theme
        + cfg.w_location * location
        + cfg.w_setup * setup
        + cfg.w_risk * risk
    )
    return ScoreBreakdown(theme, location, setup, risk, round(total, 2))

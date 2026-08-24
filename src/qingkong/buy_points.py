"""个股买入点状态机。

优先级（高 → 低）：
B5 打地鼠（快进快出，独立仓位）
B1 急跌低吸（牛市主线）
B2 企稳确认（不跌不动）
B4 飘旗待涨（整理后加速，仍等突破而不是提前抢）
B3 启动苗头（看好但不涨的票，离场后再等信号）
B7 试盘
B6 持仓做 T（已有底仓才允许）
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .config import DEFAULT_CONFIG, StrategyConfig
from .filters import CandidateBasics, hard_filter
from .regime import MarketRegime, position_cap
from .scorer import ScoreBreakdown, score_setup


class BuyPoint(str, Enum):
    B1_CRASH_DIP = "B1_CRASH_DIP"
    B2_STABILIZE = "B2_STABILIZE"
    B3_START_SEED = "B3_START_SEED"
    B4_FLAG_WAIT = "B4_FLAG_WAIT"
    B5_WHACK_A_MOLE = "B5_WHACK_A_MOLE"
    B6_T0 = "B6_T0"
    B7_PROBE = "B7_PROBE"
    NONE = "NONE"


class Action(str, Enum):
    BUY = "BUY"
    ADD = "ADD"
    HOLD = "HOLD"
    T0 = "T0"
    REDUCE = "REDUCE"
    EXIT = "EXIT"
    SKIP = "SKIP"
    WAIT = "WAIT"


@dataclass(frozen=True)
class StockSnapshot:
    """一只票当天用于判定买点的最小字段。"""

    basics: CandidateBasics
    day_change: float  # 当日涨跌幅，-0.04 = 跌 4%
    near_day_low: bool  # 是否靠近当日最低（「日低加仓」）
    recent_max_drop: float  # 近几日最大回撤，负值
    consolidating: bool  # 是否横盘/企稳确认中
    stabilize_ok: bool  # 是否已经给出企稳（不跌、缩量、收回均线等）
    flag_pattern: bool  # 飘旗/收敛整理
    flag_breakout: bool  # 旗形向上突破
    start_seed: bool  # 启动苗头：放量转强、突破横盘上沿
    liked_but_dead: bool  # 看好但就是不涨，应暂时离场
    probe: bool  # 试盘
    probe_failed: bool = False
    has_core: bool = False  # 已有底仓，才能做 T
    t0_setup: bool = False  # 分时具备做 T 空间
    limit_up: bool = False
    stretched_up: bool = False  # 已大幅拉高，适合止盈部分而不是新买
    mainline: bool = False
    low_position: bool = False  # 低位/涨幅不大
    quality_tech: bool = False  # 业绩稳定、细分龙头一类标签
    whack_a_mole: bool = False  # 打地鼠：预期短脉冲，必须快进快出


@dataclass(frozen=True)
class Decision:
    action: Action
    buy_point: BuyPoint
    position_cap: float
    suggested_position: float
    score: float
    reason: str


def decide(
    snap: StockSnapshot,
    regime: MarketRegime,
    holding: bool = False,
    cfg: StrategyConfig = DEFAULT_CONFIG,
    score: ScoreBreakdown | None = None,
) -> Decision:
    cap = position_cap(regime)
    fr = hard_filter(snap.basics, cfg)
    sc = score or score_setup(snap, cfg)

    if snap.probe_failed:
        return Decision(Action.EXIT, BuyPoint.B7_PROBE, cap, 0.0, sc.total, "试盘不符预期，按纪律离场")

    if snap.liked_but_dead and holding:
        return Decision(
            Action.EXIT,
            BuyPoint.B3_START_SEED,
            cap,
            0.0,
            sc.total,
            "看好但不涨，暂时离场，等启动苗头再进",
        )

    if snap.stretched_up and holding:
        return Decision(Action.REDUCE, BuyPoint.NONE, cap, 0.0, sc.total, "拉高/涨停只止盈部分仓位，底仓可留")

    if not fr.passed:
        return Decision(Action.SKIP, BuyPoint.NONE, cap, 0.0, sc.total, "；".join(fr.reasons))

    if regime == MarketRegime.EVENT_RISK and not holding:
        return Decision(Action.SKIP, BuyPoint.NONE, cap, 0.0, sc.total, "事件窗口先减仓，不新开")

    # B5 打地鼠：独立于主线低吸，必须快进快出
    if snap.whack_a_mole and not holding:
        if sc.total < 60:
            return Decision(Action.SKIP, BuyPoint.B5_WHACK_A_MOLE, cap, 0.0, sc.total, "打地鼠评分不够，宁错过")
        size = min(cfg.whack_max, cap)
        return Decision(Action.BUY, BuyPoint.B5_WHACK_A_MOLE, cap, size, sc.total, "打地鼠：大仓快进快出，预期失效立即清")

    # B6 持仓做 T
    if holding and snap.has_core and snap.t0_setup:
        size = round(min(cfg.t0_float_max, cap * 0.4), 4)
        return Decision(Action.T0, BuyPoint.B6_T0, cap, size, sc.total, "持股做 T：底仓不动，浮仓当日平")

    # B4 飘旗：有旗形但未突破 → 等待，不抢
    if snap.flag_pattern and not snap.flag_breakout:
        return Decision(Action.WAIT, BuyPoint.B4_FLAG_WAIT, cap, 0.0, sc.total, "飘旗有加速动能，待涨不抢跑")
    if snap.flag_pattern and snap.flag_breakout and sc.total >= cfg.open_score_min:
        size = cfg.dip_add_unit if holding else min(0.15, cap)
        act = Action.ADD if holding else Action.BUY
        return Decision(act, BuyPoint.B4_FLAG_WAIT, cap, size, sc.total, "飘旗后突破，小仓跟随加速")

    # B1 急跌低吸
    crash = snap.day_change <= cfg.crash_drop_min or snap.recent_max_drop <= cfg.deep_drop_min
    if crash and (snap.mainline or snap.quality_tech or holding):
        if regime in {MarketRegime.BULL_DIP, MarketRegime.BULL_GRIND} or holding:
            if snap.near_day_low or snap.recent_max_drop <= cfg.deep_drop_min:
                size = cfg.dip_add_unit if holding else min(0.15, cap)
                act = Action.ADD if holding else Action.BUY
                why = "日低加仓" if snap.near_day_low else "急跌/深跌分批低吸"
                return Decision(act, BuyPoint.B1_CRASH_DIP, cap, size, sc.total, f"{why}：牛市主线恐惧中分批买")

    # B2 企稳确认：还在跌就不动
    if snap.consolidating and not snap.stabilize_ok:
        return Decision(Action.WAIT, BuyPoint.B2_STABILIZE, cap, 0.0, sc.total, "企稳确认中，不跌不动")
    if snap.consolidating and snap.stabilize_ok and sc.total >= cfg.open_score_min:
        size = cfg.batch_add_unit if holding else min(0.12, cap)
        act = Action.ADD if holding else Action.BUY
        return Decision(act, BuyPoint.B2_STABILIZE, cap, size, sc.total, "企稳确认后分批少加")

    # B3 启动苗头
    if snap.start_seed and not snap.stretched_up and sc.total >= cfg.open_score_min:
        size = min(0.12, cap)
        return Decision(Action.BUY, BuyPoint.B3_START_SEED, cap, size, sc.total, "出现启动苗头再进，不提前埋伏死扛")

    # B7 试盘
    if snap.probe:
        return Decision(Action.BUY, BuyPoint.B7_PROBE, cap, cfg.probe_unit, sc.total, "试盘轻仓，不符预期离场")

    if holding:
        return Decision(Action.HOLD, BuyPoint.NONE, cap, 0.0, sc.total, "不符合加减条件，持股待涨或继续做 T 观察")

    return Decision(Action.SKIP, BuyPoint.NONE, cap, 0.0, sc.total, "没有合法买点，宁愿错过也不乱做")

"""买点 / 卖点状态机：把「追资金」编码成可执行动作。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .config import DEFAULT_CONFIG, StrategyConfig
from .emotion import EmotionLabel
from .scorer import ScoreBreakdown
from .seat import SeatSignal


class BuyPoint(str, Enum):
    B1_ONE_TO_TWO = "B1_ONE_TO_TWO"
    B2_DIVERGENCE_TO_CONSENSUS = "B2_DIVERGENCE_TO_CONSENSUS"
    B3_FIRST_YIN = "B3_FIRST_YIN"
    NONE = "NONE"


class SellPoint(str, Enum):
    S1_BREAK_MA5 = "S1_BREAK_MA5"
    S2_CLIMAX_VOLUME_YIN = "S2_CLIMAX_VOLUME_YIN"
    S3_LEADER_REPLACED = "S3_LEADER_REPLACED"
    S4_SEAT_TURN_BAD = "S4_SEAT_TURN_BAD"
    S5_EMOTION_COOL_EBB = "S5_EMOTION_COOL_EBB"
    S6_REGULATORY = "S6_REGULATORY"
    NONE = "NONE"


class Action(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    EXIT = "EXIT"
    SKIP = "SKIP"


@dataclass(frozen=True)
class MarketContext:
    emotion: EmotionLabel
    market_max_board: int


@dataclass(frozen=True)
class BarContext:
    board_height: int
    yesterday_board_height: int
    turnover: float
    limit_up: bool
    broken_then_seal: bool
    first_yin: bool
    above_ma5: bool
    above_ma10: bool
    huge_volume_yin: bool
    long_upper_shadow: bool
    leader_replaced: bool = False
    regulatory_risk: bool = False
    auction_strong: bool = False


@dataclass(frozen=True)
class Decision:
    action: Action
    buy_point: BuyPoint
    sell_point: SellPoint
    position_cap: float
    suggested_position: float
    reason: str


def decide_action(
    score: ScoreBreakdown,
    market: MarketContext,
    bar: BarContext,
    holding: bool = False,
    cfg: StrategyConfig = DEFAULT_CONFIG,
) -> Decision:
    pos_cap = cfg.position_cap.get(market.emotion.value, 0.0)

    # 持仓优先检查卖点
    if holding:
        sell = _check_sell(score, market, bar)
        if sell != SellPoint.NONE:
            action = Action.EXIT if sell != SellPoint.S1_BREAK_MA5 else Action.REDUCE
            if sell == SellPoint.S5_EMOTION_COOL_EBB:
                action = Action.REDUCE if market.emotion == EmotionLabel.COOL else Action.EXIT
            return Decision(
                action=action,
                buy_point=BuyPoint.NONE,
                sell_point=sell,
                position_cap=pos_cap,
                suggested_position=0.0 if action == Action.EXIT else max(0.0, pos_cap * 0.3),
                reason=f"触发卖点 {sell.value}",
            )
        return Decision(
            action=Action.HOLD,
            buy_point=BuyPoint.NONE,
            sell_point=SellPoint.NONE,
            position_cap=pos_cap,
            suggested_position=pos_cap,
            reason="持仓中，卖点未触发",
        )

    # 空仓：买点
    if pos_cap <= 0:
        return Decision(
            action=Action.SKIP,
            buy_point=BuyPoint.NONE,
            sell_point=SellPoint.NONE,
            position_cap=pos_cap,
            suggested_position=0.0,
            reason="情绪仓位上限为0",
        )

    if score.seat_signal in {SeatSignal.FAKE_IGNITE, SeatSignal.DAY_TRIP}:
        return Decision(
            action=Action.SKIP,
            buy_point=BuyPoint.NONE,
            sell_point=SellPoint.NONE,
            position_cap=pos_cap,
            suggested_position=0.0,
            reason="席位质量否决追高",
        )

    if score.total < cfg.open_score_min:
        return Decision(
            action=Action.SKIP,
            buy_point=BuyPoint.NONE,
            sell_point=SellPoint.NONE,
            position_cap=pos_cap,
            suggested_position=0.0,
            reason=f"评分{score.total}<{cfg.open_score_min}",
        )

    buy = _check_buy(market.emotion, bar, cfg)
    if buy == BuyPoint.NONE:
        return Decision(
            action=Action.SKIP,
            buy_point=BuyPoint.NONE,
            sell_point=SellPoint.NONE,
            position_cap=pos_cap,
            suggested_position=0.0,
            reason="未触发合法买点",
        )

    suggested = _size_for_buy(buy, pos_cap, market.emotion)
    return Decision(
        action=Action.BUY,
        buy_point=buy,
        sell_point=SellPoint.NONE,
        position_cap=pos_cap,
        suggested_position=suggested,
        reason=f"触发买点 {buy.value}",
    )


def _check_sell(score: ScoreBreakdown, market: MarketContext, bar: BarContext) -> SellPoint:
    if bar.regulatory_risk:
        return SellPoint.S6_REGULATORY
    if bar.huge_volume_yin or (bar.long_upper_shadow and bar.turnover >= 30):
        return SellPoint.S2_CLIMAX_VOLUME_YIN
    if bar.leader_replaced:
        return SellPoint.S3_LEADER_REPLACED
    if score.seat_signal in {SeatSignal.FAKE_IGNITE, SeatSignal.DAY_TRIP, SeatSignal.DISTRIBUTION}:
        return SellPoint.S4_SEAT_TURN_BAD
    if market.emotion in {EmotionLabel.COOL, EmotionLabel.EBB}:
        return SellPoint.S5_EMOTION_COOL_EBB
    if not bar.above_ma5:
        return SellPoint.S1_BREAK_MA5
    return SellPoint.NONE


def _check_buy(emotion: EmotionLabel, bar: BarContext, cfg: StrategyConfig) -> BuyPoint:
    if bar.turnover >= cfg.turnover_danger and not bar.first_yin:
        return BuyPoint.NONE

    # B3 断板首阴
    if bar.first_yin and (bar.above_ma5 or bar.above_ma10):
        if emotion in {EmotionLabel.WARM, EmotionLabel.CLIMAX, EmotionLabel.COOL}:
            if emotion == EmotionLabel.COOL:
                return BuyPoint.B3_FIRST_YIN
            return BuyPoint.B3_FIRST_YIN

    # B1 一进二
    if (
        bar.yesterday_board_height == 1
        and bar.board_height >= 1
        and emotion in {EmotionLabel.ICE, EmotionLabel.REPAIR, EmotionLabel.WARM, EmotionLabel.CLIMAX}
    ):
        if emotion == EmotionLabel.CLIMAX:
            # 高潮期一进二降权，仍允许但由仓位矩阵压缩
            pass
        if emotion == EmotionLabel.ICE and not bar.auction_strong:
            return BuyPoint.NONE
        if bar.limit_up or bar.auction_strong or bar.broken_then_seal:
            return BuyPoint.B1_ONE_TO_TWO

    # B2 分歧转一致
    if (
        bar.board_height >= 2
        and bar.broken_then_seal
        and emotion in {EmotionLabel.REPAIR, EmotionLabel.WARM}
    ):
        return BuyPoint.B2_DIVERGENCE_TO_CONSENSUS

    return BuyPoint.NONE


def _size_for_buy(buy: BuyPoint, pos_cap: float, emotion: EmotionLabel) -> float:
    mult = {
        BuyPoint.B1_ONE_TO_TWO: 0.50,
        BuyPoint.B2_DIVERGENCE_TO_CONSENSUS: 0.40,
        BuyPoint.B3_FIRST_YIN: 0.30,
    }.get(buy, 0.0)
    if emotion == EmotionLabel.CLIMAX and buy == BuyPoint.B1_ONE_TO_TWO:
        mult *= 0.6
    if emotion == EmotionLabel.ICE:
        mult = min(mult, 1.0)
        return min(pos_cap, 0.05)
    return round(pos_cap * mult, 4)

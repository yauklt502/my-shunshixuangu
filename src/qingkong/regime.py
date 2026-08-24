"""大盘环境：决定仓位上限，不决定具体买哪只。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MarketRegime(str, Enum):
    BULL_DIP = "BULL_DIP"  # 牛市急跌：恐惧中贪婪，分批低吸主线
    BULL_GRIND = "BULL_GRIND"  # 牛市震荡上行：少追涨、多低吸、持股做 T
    EVENT_RISK = "EVENT_RISK"  # 阅兵/会议等事件窗：先减仓
    ROTATION = "ROTATION"  # 热点轮动快：不一根筋，等启动苗头
    WEAK = "WEAK"  # 缩量、普跌：降低总仓，只做持仓 T 或空仓


@dataclass(frozen=True)
class MarketSnapshot:
    index_change: float  # 主要指数当日涨跌幅，如 -0.02
    volume_change: float  # 成交额相对昨日，如 -0.12
    down_count: int  # 下跌家数
    up_count: int
    is_bull_bias: bool  # 中期是否按牛市框架交易
    event_risk: bool = False  # 阅兵、长假、关键复牌等
    rotation_fast: bool = False


def classify_regime(m: MarketSnapshot) -> MarketRegime:
    if m.event_risk:
        return MarketRegime.EVENT_RISK
    if m.is_bull_bias and m.index_change <= -0.015:
        return MarketRegime.BULL_DIP
    if not m.is_bull_bias and (m.index_change <= -0.015 or m.down_count >= 4000):
        return MarketRegime.WEAK
    if m.rotation_fast:
        return MarketRegime.ROTATION
    if m.is_bull_bias:
        return MarketRegime.BULL_GRIND
    return MarketRegime.WEAK


def position_cap(regime: MarketRegime) -> float:
    return {
        MarketRegime.BULL_DIP: 0.75,
        MarketRegime.BULL_GRIND: 0.70,
        MarketRegime.ROTATION: 0.50,
        MarketRegime.EVENT_RISK: 0.40,
        MarketRegime.WEAK: 0.30,
    }[regime]

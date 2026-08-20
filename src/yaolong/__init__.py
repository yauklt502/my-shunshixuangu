"""妖龙跟随策略 — 规则引擎包。

研究框架，不构成投资建议。
"""

__version__ = "1.0.0"

from .config import StrategyConfig
from .emotion import EmotionLabel, classify_emotion
from .filters import hard_filter
from .scorer import ScoreBreakdown, score_candidate
from .seat import SeatSignal, classify_seat_pattern
from .signal import BuyPoint, SellPoint, decide_action

__all__ = [
    "StrategyConfig",
    "EmotionLabel",
    "classify_emotion",
    "hard_filter",
    "ScoreBreakdown",
    "score_candidate",
    "SeatSignal",
    "classify_seat_pattern",
    "BuyPoint",
    "SellPoint",
    "decide_action",
]

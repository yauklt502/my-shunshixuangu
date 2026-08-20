"""市场情绪周期分类。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EmotionLabel(str, Enum):
    ICE = "ICE"  # 冰点
    REPAIR = "REPAIR"  # 修复
    WARM = "WARM"  # 升温
    CLIMAX = "CLIMAX"  # 高潮
    COOL = "COOL"  # 降温
    EBB = "EBB"  # 退潮


@dataclass(frozen=True)
class EmotionSnapshot:
    limit_up_count: int
    limit_down_count: int
    max_board: int
    promote_rate: float  # 昨N板晋级到今N+1 的比率，0~1
    broken_big_face: bool = False  # 高标是否大面
    prev_label: Optional[EmotionLabel] = None


def classify_emotion(snap: EmotionSnapshot) -> EmotionLabel:
    """用公开、可统计的量把情绪落到六段。

    规则刻意偏保守：宁可少做，不要在退潮里硬刚。
    """
    if snap.broken_big_face and snap.promote_rate < 0.35:
        return EmotionLabel.EBB

    if snap.max_board <= 3 and snap.limit_up_count < 40 and snap.promote_rate < 0.30:
        return EmotionLabel.ICE

    if snap.max_board >= 8 and snap.promote_rate >= 0.50 and snap.limit_up_count >= 80:
        return EmotionLabel.CLIMAX

    if snap.promote_rate < 0.30 and snap.prev_label in {
        EmotionLabel.CLIMAX,
        EmotionLabel.WARM,
        EmotionLabel.COOL,
    }:
        if snap.limit_down_count >= 20 or snap.broken_big_face:
            return EmotionLabel.EBB
        return EmotionLabel.COOL

    if snap.promote_rate >= 0.45 and snap.max_board >= 5:
        return EmotionLabel.WARM

    if snap.prev_label in {EmotionLabel.ICE, EmotionLabel.EBB} and snap.promote_rate >= 0.30:
        return EmotionLabel.REPAIR

    if snap.limit_up_count >= 60 and snap.promote_rate >= 0.35:
        return EmotionLabel.WARM

    if snap.prev_label == EmotionLabel.CLIMAX and snap.promote_rate < 0.45:
        return EmotionLabel.COOL

    return EmotionLabel.REPAIR if snap.promote_rate >= 0.30 else EmotionLabel.ICE

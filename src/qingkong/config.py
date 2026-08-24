"""可调阈值。默认对齐公开复盘里反复出现的纪律，不是回测最优解。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class StrategyConfig:
    # 仓位
    max_names: int = 10  # 「十全十美」分散持仓的上限
    max_total_position: float = 0.85  # 明确反对满仓
    batch_add_unit: float = 0.10  # 「补一成仓」
    dip_add_unit: float = 0.10
    probe_unit: float = 0.05  # 试盘
    t0_float_max: float = 0.30  # 做 T 浮仓不超过三成（公开做 T 纪律的常用上限）
    whack_max: float = 0.25  # 打地鼠允许的较大仓，但必须快进快出

    # 买点触发
    crash_drop_min: float = -0.03  # 日内/近日急跌阈值
    deep_drop_min: float = -0.05
    stabilize_days_min: int = 1
    flag_days_min: int = 3
    flag_days_max: int = 8
    start_seed_change: float = 0.02  # 「启动苗头」：相对近期横盘的放量转强
    chase_up_max: float = 0.05  # 超过这个涨幅还追 = 追涨，默认禁止

    # 评分
    open_score_min: float = 70.0
    w_theme: float = 0.30
    w_location: float = 0.25
    w_setup: float = 0.25
    w_risk: float = 0.20

    mainline_keywords: Sequence[str] = field(
        default_factory=lambda: (
            "科技",
            "算力",
            "芯片",
            "半导体",
            "消费电子",
            "人工智能",
            "机器人",
            "固态电池",
            "黄金",
            "贵金属",
            "母机",
            "数据中心",
            "光模块",
        )
    )


DEFAULT_CONFIG = StrategyConfig()

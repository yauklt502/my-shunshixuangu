"""策略参数：全部可调，默认对齐 2025.08–2026.08 复盘结论。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class StrategyConfig:
    # 流通市值（亿元）
    circ_mv_min: float = 20.0
    circ_mv_max: float = 200.0
    circ_mv_sweet_low: float = 40.0
    circ_mv_sweet_high: float = 80.0

    # 换手率（%）
    turnover_healthy_low: float = 8.0
    turnover_healthy_high: float = 25.0
    turnover_danger: float = 35.0

    # 启动位置：相对 60 日低点的溢价上限
    start_premium_max: float = 0.40

    # 龙虎榜
    seat_single_buy_max_ratio: float = 0.50
    seat_min_famous: int = 2

    # 评分权重
    w_theme: float = 0.20
    w_mcap: float = 0.15
    w_leader: float = 0.20
    w_volume: float = 0.15
    w_seat: float = 0.15
    w_pattern: float = 0.15

    open_score_min: float = 75.0

    # 国家级 / 当期主线关键词（可按行情季更新）
    mainline_keywords: Sequence[str] = field(
        default_factory=lambda: (
            "AI",
            "算力",
            "PCB",
            "光模块",
            "机器人",
            "人形",
            "绿电",
            "电力",
            "央改",
            "半导体",
            "芯片",
            "商业航天",
            "低空",
            "固态电池",
            "新质生产力",
            "控制权变更",
            "并购重组",
        )
    )

    # 一线/半一线游资关键词（公开市场惯例名号，研究用）
    famous_seat_keywords: Sequence[str] = field(
        default_factory=lambda: (
            "章盟主",
            "炒股养家",
            "赵老哥",
            "小鳄鱼",
            "作手新一",
            "方新侠",
            "上塘路",
            "桑田路",
            "中山北路",
            "武定路",
            "成都帮",
            "绍兴帮",
            "华鑫上海分公司",
            "国泰君安上海江苏路",
            "中国中金财富证券北京宋庄路",
        )
    )

    # 情绪 → 总仓上限
    position_cap: dict[str, float] = field(
        default_factory=lambda: {
            "ICE": 0.05,
            "REPAIR": 0.20,
            "WARM": 0.40,
            "CLIMAX": 0.25,
            "COOL": 0.10,
            "EBB": 0.00,
        }
    )


DEFAULT_CONFIG = StrategyConfig()

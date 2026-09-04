"""领域模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Board:
    code: str
    name: str
    kind: str  # concept | industry
    change_percent: float | None = None
    amount: float | None = None
    main_net_inflow: float | None = None
    up_count: int | None = None
    down_count: int | None = None
    source: str = ""

    @property
    def member_count(self) -> int:
        return int((self.up_count or 0) + (self.down_count or 0))


@dataclass
class Stock:
    code: str
    name: str
    market: int = 0
    price: float | None = None
    change_percent: float | None = None
    amount: float | None = None
    turnover: float | None = None
    main_net_inflow: float | None = None
    board_code: str | None = None
    board_name: str | None = None
    source: str = ""


@dataclass
class LimitUpInfo:
    code: str
    name: str
    first_seal_time: int = 0
    consecutive_boards: int = 1
    seal_amount: float | None = None
    open_count: int = 0
    industry: str | None = None


@dataclass
class LimitBreakInfo:
    code: str
    name: str
    first_seal_time: int = 0
    open_count: int = 1
    change_percent: float | None = None


@dataclass
class Candidate:
    """策略输出的候选龙头。"""

    rank_label: str
    code: str
    name: str
    board_name: str
    board_kind: str
    change_percent: float | None
    price: float | None
    amount: float | None
    score: float
    tags: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    is_limit_up: bool = False
    is_broken: bool = False
    consecutive_boards: int | None = None
    first_seal_time: str | None = None
    attention: str = "观察"  # 观察 | 聚焦 | 回避
    weakness_flags: list[str] = field(default_factory=list)
    source: str = ""

    def to_row(self) -> dict[str, Any]:
        return {
            "关注": self.attention,
            "评级": self.rank_label,
            "代码": self.code,
            "名称": self.name,
            "板块": self.board_name,
            "涨幅%": None if self.change_percent is None else round(self.change_percent, 2),
            "现价": self.price,
            "连板": self.consecutive_boards,
            "封板": self.first_seal_time or "--",
            "得分": round(self.score, 1),
            "标签": " · ".join(self.tags),
            "要点": "；".join(self.reasons[:3]),
            "弱势信号": " · ".join(self.weakness_flags) if self.weakness_flags else "--",
            "数据源": self.source,
        }


@dataclass
class MarketSnapshot:
    trade_date: str
    source: str
    indices: list[dict[str, Any]] = field(default_factory=list)
    boards: list[Board] = field(default_factory=list)
    stocks_by_board: dict[str, list[Stock]] = field(default_factory=dict)
    zt_by_code: dict[str, LimitUpInfo] = field(default_factory=dict)
    zb_by_code: dict[str, LimitBreakInfo] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

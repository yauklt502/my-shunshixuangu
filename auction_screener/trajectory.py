"""集合竞价走势评分（09:15–09:25）。

09:15–09:20 可撤单：只观察。
09:20–09:25 不可撤单：主决策窗口。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuctionTick:
    """一次竞价快照。ts 用 HHMMSS 整数，如 92015。"""

    ts: int
    px: float
    prev_close: float
    vol_shares: float = 0.0
    amt: float = 0.0
    bid1_vol: float = 0.0
    bid1_px: float = 0.0
    ask1_vol: float = 0.0
    ask1_px: float = 0.0

    @property
    def open_pct(self) -> float:
        if self.prev_close <= 0 or self.px <= 0:
            return 0.0
        return (self.px / self.prev_close - 1.0) * 100.0


@dataclass
class TrajectoryState:
    ticks: list[AuctionTick] = field(default_factory=list)

    def add(self, tick: AuctionTick) -> None:
        if self.ticks and self.ticks[-1].ts == tick.ts and abs(self.ticks[-1].px - tick.px) < 1e-9:
            self.ticks[-1] = tick
            return
        self.ticks.append(tick)

    def after(self, hhmmss: int) -> list[AuctionTick]:
        return [t for t in self.ticks if t.ts >= hhmmss]

    def before(self, hhmmss: int) -> list[AuctionTick]:
        return [t for t in self.ticks if t.ts < hhmmss]


def _pct(tick: AuctionTick | None) -> float:
    return tick.open_pct if tick else 0.0


def score_trajectory(state: TrajectoryState) -> dict[str, Any]:
    """根据快照序列打走势分。

    返回:
      traj_score: 加减分（建议并入综合分）
      traj_label: 升势确认 / 高位横住 / 冲高回落 / 弱势磨底 / 样本不足
      detail: 诊断字段
    """
    ticks = [t for t in state.ticks if t.px > 0 and t.prev_close > 0]
    if len(ticks) < 2:
        last = ticks[-1] if ticks else None
        return {
            "traj_score": 0.0,
            "traj_label": "样本不足",
            "detail": {"n": len(ticks), "last_pct": _pct(last)},
        }

    early = [t for t in ticks if t.ts < 92000]
    late = [t for t in ticks if t.ts >= 92000]
    if not late:
        # 还在 9:20 前：不给强结论
        last = ticks[-1]
        label = "观察中"
        score = 0.0
        if last.open_pct >= 1.5:
            score = 2.0
        return {
            "traj_score": score,
            "traj_label": label,
            "detail": {"n": len(ticks), "last_pct": last.open_pct, "phase": "pre920"},
        }

    early_peak = max((t.open_pct for t in early), default=_pct(late[0]))
    late_first = late[0]
    late_last = late[-1]
    late_peak = max(t.open_pct for t in late)
    late_low = min(t.open_pct for t in late)
    lift = late_last.open_pct - late_first.open_pct
    dump_from_early = early_peak - late_last.open_pct if early else 0.0

    vol_start = late_first.vol_shares
    vol_end = late_last.vol_shares
    vol_up = vol_end > vol_start * 1.05 if vol_start > 0 else False

    bid_amt = late_last.bid1_vol * late_last.bid1_px
    ask_amt = late_last.ask1_vol * late_last.ask1_px
    imbalance = (bid_amt - ask_amt) / (bid_amt + ask_amt + 1.0)

    score = 0.0
    label = "高位横住"

    if late_last.open_pct < 1.5:
        label = "弱势磨底"
        score -= 12
    elif dump_from_early >= 0.5 and lift < 0:
        label = "冲高回落"
        score -= 18
    elif lift >= 0.3 and late_last.open_pct >= 1.5:
        label = "升势确认"
        score += 18
        if vol_up:
            score += 6
    elif abs(lift) <= 0.25 and late_last.open_pct >= 2.0 and (late_peak - late_low) <= 0.6:
        label = "高位横住"
        score += 10
        if vol_up:
            score += 3
    elif lift < -0.3:
        label = "冲高回落"
        score -= 14
    else:
        label = "高位横住"
        score += 4

    if imbalance > 0.35 and late_last.open_pct >= 1.5:
        score += 5
    elif imbalance < -0.35:
        score -= 5

    # 接近涨停但未封：保留取反可买性，略降「追高」分
    if late_last.open_pct >= 8.5:
        score -= 8
        if label == "升势确认":
            label = "高位横住"

    return {
        "traj_score": float(score),
        "traj_label": label,
        "detail": {
            "n": len(ticks),
            "early_peak": round(early_peak, 3),
            "late_first": round(late_first.open_pct, 3),
            "late_last": round(late_last.open_pct, 3),
            "lift": round(lift, 3),
            "dump_from_early": round(dump_from_early, 3),
            "vol_up": vol_up,
            "imbalance": round(imbalance, 3),
        },
    }


def hhmmss_from_str(s: str) -> int:
    """'09:20:15' / '92015' / '09:20:15.000' → 92015。"""
    t = (s or "").strip().replace(".", "")
    if not t:
        return 0
    if ":" in t:
        parts = t.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        sec = int(float(parts[2])) if len(parts) > 2 else 0
        return h * 10000 + m * 100 + sec
    digits = "".join(ch for ch in t if ch.isdigit())
    if len(digits) >= 6:
        return int(digits[:6])
    if len(digits) == 5:
        return int(digits)
    return int(digits) if digits else 0

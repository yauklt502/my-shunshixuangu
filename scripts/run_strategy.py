"""命令行：对样本 JSON 跑硬过滤 + 评分 + 买卖决策。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# 允许直接 python scripts/run_strategy.py
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from yaolong.config import DEFAULT_CONFIG
from yaolong.emotion import EmotionLabel, EmotionSnapshot, classify_emotion
from yaolong.filters import CandidateBasics, hard_filter
from yaolong.scorer import LeaderInput, PatternInput, score_candidate
from yaolong.seat import SeatBook, SeatRow
from yaolong.signal import BarContext, MarketContext, decide_action


def _seat_book(raw: dict[str, Any] | None) -> SeatBook | None:
    if not raw:
        return None
    buys = [SeatRow(name=x["name"], buy=float(x.get("buy", 0)), sell=float(x.get("sell", 0))) for x in raw.get("buys", [])]
    sells = [SeatRow(name=x["name"], buy=float(x.get("buy", 0)), sell=float(x.get("sell", 0))) for x in raw.get("sells", [])]
    return SeatBook(buys=buys, sells=sells)


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    emotion_raw = case.get("emotion")
    if isinstance(emotion_raw, dict):
        label = classify_emotion(
            EmotionSnapshot(
                limit_up_count=int(emotion_raw["limit_up_count"]),
                limit_down_count=int(emotion_raw.get("limit_down_count", 0)),
                max_board=int(emotion_raw["max_board"]),
                promote_rate=float(emotion_raw["promote_rate"]),
                broken_big_face=bool(emotion_raw.get("broken_big_face", False)),
                prev_label=EmotionLabel(emotion_raw["prev_label"]) if emotion_raw.get("prev_label") else None,
            )
        )
    else:
        label = EmotionLabel(str(emotion_raw))

    b = case["basics"]
    basics = CandidateBasics(
        code=b["code"],
        name=b["name"],
        circ_mv=float(b["circ_mv"]),
        is_st=bool(b.get("is_st", False)),
        theme_tags=tuple(b.get("theme_tags", [])),
        is_yizi_rear=bool(b.get("is_yizi_rear", False)),
        board_height=int(b.get("board_height", 0)),
        market_max_board=int(b.get("market_max_board", 0)),
        relative_to_60d_low=float(b.get("relative_to_60d_low", 0.0)),
    )
    fr = hard_filter(basics)

    p = case["pattern"]
    pattern = PatternInput(
        stage=p["stage"],
        turnover=float(p["turnover"]),
        volume_vs_5d=float(p.get("volume_vs_5d", 1.0)),
        above_ma5=bool(p.get("above_ma5", True)),
        above_ma10=bool(p.get("above_ma10", True)),
        long_upper_shadow=bool(p.get("long_upper_shadow", False)),
        limit_up=bool(p.get("limit_up", False)),
        broken_then_seal=bool(p.get("broken_then_seal", False)),
    )
    l = case.get("leader", {})
    leader = LeaderInput(
        is_theme_first_mover=bool(l.get("is_theme_first_mover", False)),
        highest_board_in_theme=bool(l.get("highest_board_in_theme", False)),
        best_resilience=bool(l.get("best_resilience", False)),
        follower_count=int(l.get("follower_count", 0)),
        uniqueness=float(l.get("uniqueness", 0.5)),
    )
    seat_book = _seat_book(case.get("seat"))
    score = score_candidate(basics, pattern, leader, seat_book)
    pos_cap = float(DEFAULT_CONFIG.position_cap.get(label.value, 0.0))

    if not fr.passed:
        return {
            "code": basics.code,
            "name": basics.name,
            "emotion": label.value,
            "filter_passed": False,
            "filter_reasons": list(fr.reasons),
            "score_total": score.total,
            "score": {
                "theme": score.theme,
                "mcap": score.mcap,
                "leader": score.leader,
                "volume": score.volume,
                "seat": score.seat,
                "pattern": score.pattern,
            },
            "seat_signal": score.seat_signal.value,
            "notes": list(score.notes),
            "action": "SKIP",
            "buy_point": "NONE",
            "sell_point": "NONE",
            "position_cap": pos_cap,
            "suggested_position": 0.0,
            "reason": "硬过滤未通过: " + "; ".join(fr.reasons),
        }

    bar_raw = case.get("bar", {})
    bar = BarContext(
        board_height=int(bar_raw.get("board_height", basics.board_height)),
        yesterday_board_height=int(bar_raw.get("yesterday_board_height", max(0, basics.board_height - 1))),
        turnover=float(bar_raw.get("turnover", pattern.turnover)),
        limit_up=bool(bar_raw.get("limit_up", pattern.limit_up)),
        broken_then_seal=bool(bar_raw.get("broken_then_seal", pattern.broken_then_seal)),
        first_yin=bool(bar_raw.get("first_yin", pattern.stage == "first_yin")),
        above_ma5=bool(bar_raw.get("above_ma5", pattern.above_ma5)),
        above_ma10=bool(bar_raw.get("above_ma10", pattern.above_ma10)),
        huge_volume_yin=bool(bar_raw.get("huge_volume_yin", False)),
        long_upper_shadow=bool(bar_raw.get("long_upper_shadow", pattern.long_upper_shadow)),
        leader_replaced=bool(bar_raw.get("leader_replaced", False)),
        regulatory_risk=bool(bar_raw.get("regulatory_risk", False)),
        auction_strong=bool(bar_raw.get("auction_strong", False)),
    )
    decision = decide_action(
        score,
        MarketContext(emotion=label, market_max_board=basics.market_max_board),
        bar,
        holding=bool(case.get("holding", False)),
    )

    return {
        "code": basics.code,
        "name": basics.name,
        "emotion": label.value,
        "filter_passed": fr.passed,
        "filter_reasons": list(fr.reasons),
        "score_total": score.total,
        "score": {
            "theme": score.theme,
            "mcap": score.mcap,
            "leader": score.leader,
            "volume": score.volume,
            "seat": score.seat,
            "pattern": score.pattern,
        },
        "seat_signal": score.seat_signal.value,
        "notes": list(score.notes),
        "action": decision.action.value,
        "buy_point": decision.buy_point.value,
        "sell_point": decision.sell_point.value,
        "position_cap": decision.position_cap,
        "suggested_position": decision.suggested_position,
        "reason": decision.reason,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="妖龙跟随策略样本评估")
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=ROOT / "data" / "samples" / "yaolong_cases.json",
        help="样本 JSON 路径",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    cases = json.loads(args.input.read_text(encoding="utf-8"))
    results = [evaluate_case(c) for c in cases]
    dump = json.dumps(results, ensure_ascii=False, indent=2 if args.pretty else None)
    print(dump)


if __name__ == "__main__":
    main()

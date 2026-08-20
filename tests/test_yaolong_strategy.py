from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from yaolong.emotion import EmotionLabel, EmotionSnapshot, classify_emotion
from yaolong.filters import CandidateBasics, hard_filter
from yaolong.scorer import LeaderInput, PatternInput, score_candidate
from yaolong.seat import SeatBook, SeatRow, SeatSignal, classify_seat_pattern
from yaolong.signal import Action, BarContext, BuyPoint, MarketContext, decide_action

# 复用 CLI 评估
sys.path.insert(0, str(ROOT / "scripts"))
from run_strategy import evaluate_case  # noqa: E402


def test_emotion_ebb_on_big_face():
    label = classify_emotion(
        EmotionSnapshot(
            limit_up_count=40,
            limit_down_count=25,
            max_board=5,
            promote_rate=0.2,
            broken_big_face=True,
            prev_label=EmotionLabel.CLIMAX,
        )
    )
    assert label == EmotionLabel.EBB


def test_hard_filter_rejects_yizi_rear():
    fr = hard_filter(
        CandidateBasics(
            code="1",
            name="x",
            circ_mv=50,
            theme_tags=["机器人"],
            is_yizi_rear=True,
        )
    )
    assert not fr.passed
    assert any("一字" in r for r in fr.reasons)


def test_true_synergy_seat():
    sig = classify_seat_pattern(
        SeatBook(
            buys=[
                SeatRow("华鑫上海分公司", 8000),
                SeatRow("上塘路", 6000),
                SeatRow("炒股养家", 5000),
                SeatRow("A", 2000),
            ],
            sells=[SeatRow("B", 3000)],
        )
    )
    assert sig == SeatSignal.TRUE_SYNERGY


def test_fake_ignite_seat():
    sig = classify_seat_pattern(
        SeatBook(
            buys=[SeatRow("独舞", 20000), SeatRow("A", 1000)],
            sells=[SeatRow("独舞", 16000)],
        )
    )
    assert sig in {SeatSignal.FAKE_IGNITE, SeatSignal.DAY_TRIP}


def test_sample_cases_end_to_end():
    cases = json.loads((ROOT / "data" / "samples" / "yaolong_cases.json").read_text(encoding="utf-8"))
    results = {c["id"]: evaluate_case(c) for c in cases}

    good = results["fenglong_like_warmup_leader"]
    assert good["filter_passed"]
    assert good["score_total"] >= 75
    assert good["action"] == Action.BUY.value
    assert good["buy_point"] in {
        BuyPoint.B1_ONE_TO_TWO.value,
        BuyPoint.B2_DIVERGENCE_TO_CONSENSUS.value,
    }

    fake = results["fake_ignite_chase"]
    assert fake["action"] == Action.SKIP.value
    assert fake["seat_signal"] in {"FAKE_IGNITE", "DAY_TRIP"}

    rear = results["yizi_rear_reject"]
    assert rear["filter_passed"] is False
    assert rear["action"] == Action.SKIP.value
    assert "硬过滤" in rear["reason"]

    yin = results["first_yin_dragon_pullback"]
    assert yin["action"] == Action.BUY.value
    assert yin["buy_point"] == BuyPoint.B3_FIRST_YIN.value

    ebb = results["ebb_no_trade"]
    assert ebb["emotion"] == EmotionLabel.EBB.value
    assert ebb["action"] == Action.SKIP.value
    assert ebb["position_cap"] == 0.0


def test_decide_exit_on_ma5_break():
    basics_score = score_candidate(
        CandidateBasics("1", "x", 50, theme_tags=["AI算力"], board_height=3, market_max_board=6),
        PatternInput(stage="accelerate", turnover=15, volume_vs_5d=1.2),
        LeaderInput(highest_board_in_theme=True, uniqueness=0.8),
    )
    d = decide_action(
        basics_score,
        MarketContext(emotion=EmotionLabel.WARM, market_max_board=6),
        BarContext(
            board_height=3,
            yesterday_board_height=3,
            turnover=18,
            limit_up=False,
            broken_then_seal=False,
            first_yin=False,
            above_ma5=False,
            above_ma10=True,
            huge_volume_yin=False,
            long_upper_shadow=False,
        ),
        holding=True,
    )
    assert d.action == Action.REDUCE

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from qingkong.buy_points import Action, BuyPoint
from qingkong.filters import CandidateBasics, hard_filter
from qingkong.regime import MarketRegime, MarketSnapshot, classify_regime
from run_buy_points import evaluate_case


def _load_cases() -> dict[str, dict]:
    raw = json.loads((ROOT / "data" / "samples" / "qingkong_cases.json").read_text(encoding="utf-8"))
    return {c["id"]: evaluate_case(c) for c in raw}


def test_bull_dip_classified():
    label = classify_regime(
        MarketSnapshot(
            index_change=-0.02,
            volume_change=-0.1,
            down_count=3500,
            up_count=1200,
            is_bull_bias=True,
        )
    )
    assert label == MarketRegime.BULL_DIP


def test_event_risk_overrides_bull():
    label = classify_regime(
        MarketSnapshot(
            index_change=0.01,
            volume_change=0.0,
            down_count=1000,
            up_count=3000,
            is_bull_bias=True,
            event_risk=True,
        )
    )
    assert label == MarketRegime.EVENT_RISK


def test_full_position_hard_filter():
    fr = hard_filter(
        CandidateBasics(
            code="1",
            name="x",
            theme_tags=("科技",),
            full_position=True,
            total_position=1.0,
        )
    )
    assert not fr.passed
    assert any("满仓" in r for r in fr.reasons)


def test_sample_cases_match_public_logic():
    results = _load_cases()

    add = results["nengte_day_low_add"]
    assert add["action"] == Action.ADD.value
    assert add["buy_point"] == BuyPoint.B1_CRASH_DIP.value

    wait = results["liou_wait_stabilize"]
    assert wait["action"] == Action.WAIT.value
    assert wait["buy_point"] == BuyPoint.B2_STABILIZE.value
    assert "不跌不动" in wait["reason"]

    mole = results["jintongling_whack"]
    assert mole["action"] == Action.BUY.value
    assert mole["buy_point"] == BuyPoint.B5_WHACK_A_MOLE.value

    flag = results["nengte_flag_wait"]
    assert flag["action"] == Action.WAIT.value
    assert flag["buy_point"] == BuyPoint.B4_FLAG_WAIT.value

    dead = results["dead_stock_exit"]
    assert dead["action"] == Action.EXIT.value

    full = results["full_position_forbid"]
    assert full["action"] == Action.SKIP.value

    chase = results["chase_forbid"]
    assert chase["action"] == Action.SKIP.value

    t0 = results["t0_on_core"]
    assert t0["action"] == Action.T0.value
    assert t0["buy_point"] == BuyPoint.B6_T0.value

    probe = results["probe_fail_exit"]
    assert probe["action"] == Action.EXIT.value

    event = results["event_window_no_new"]
    assert event["action"] == Action.SKIP.value
    assert event["regime"] == MarketRegime.EVENT_RISK.value

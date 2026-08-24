"""命令行：对样本 JSON 跑过滤 + 评分 + 买点决策。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qingkong.buy_points import StockSnapshot, decide
from qingkong.filters import CandidateBasics
from qingkong.regime import MarketRegime, MarketSnapshot, classify_regime
from qingkong.scorer import score_setup


def _basics(raw: dict[str, Any]) -> CandidateBasics:
    return CandidateBasics(
        code=str(raw["code"]),
        name=str(raw["name"]),
        theme_tags=tuple(raw.get("theme_tags", [])),
        is_st=bool(raw.get("is_st", False)),
        is_limit_up_open=bool(raw.get("is_limit_up_open", False)),
        chasing=bool(raw.get("chasing", False)),
        system_mismatch=bool(raw.get("system_mismatch", False)),
        holding_count=int(raw.get("holding_count", 0)),
        total_position=float(raw.get("total_position", 0.0)),
        full_position=bool(raw.get("full_position", False)),
    )


def _regime(case: dict[str, Any]) -> MarketRegime:
    raw = case.get("regime")
    if isinstance(raw, str):
        return MarketRegime(raw)
    m = raw or {}
    return classify_regime(
        MarketSnapshot(
            index_change=float(m.get("index_change", 0.0)),
            volume_change=float(m.get("volume_change", 0.0)),
            down_count=int(m.get("down_count", 0)),
            up_count=int(m.get("up_count", 0)),
            is_bull_bias=bool(m.get("is_bull_bias", True)),
            event_risk=bool(m.get("event_risk", False)),
            rotation_fast=bool(m.get("rotation_fast", False)),
        )
    )


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    b = _basics(case["basics"])
    s = case["snapshot"]
    snap = StockSnapshot(
        basics=b,
        day_change=float(s.get("day_change", 0.0)),
        near_day_low=bool(s.get("near_day_low", False)),
        recent_max_drop=float(s.get("recent_max_drop", 0.0)),
        consolidating=bool(s.get("consolidating", False)),
        stabilize_ok=bool(s.get("stabilize_ok", False)),
        flag_pattern=bool(s.get("flag_pattern", False)),
        flag_breakout=bool(s.get("flag_breakout", False)),
        start_seed=bool(s.get("start_seed", False)),
        liked_but_dead=bool(s.get("liked_but_dead", False)),
        probe=bool(s.get("probe", False)),
        probe_failed=bool(s.get("probe_failed", False)),
        has_core=bool(s.get("has_core", False)),
        t0_setup=bool(s.get("t0_setup", False)),
        limit_up=bool(s.get("limit_up", False)),
        stretched_up=bool(s.get("stretched_up", False)),
        mainline=bool(s.get("mainline", False)),
        low_position=bool(s.get("low_position", False)),
        quality_tech=bool(s.get("quality_tech", False)),
        whack_a_mole=bool(s.get("whack_a_mole", False)),
    )
    regime = _regime(case)
    holding = bool(case.get("holding", False))
    score = score_setup(snap)
    d = decide(snap, regime, holding=holding, score=score)
    return {
        "id": case.get("id"),
        "name": b.name,
        "regime": regime.value,
        "action": d.action.value,
        "buy_point": d.buy_point.value,
        "suggested_position": d.suggested_position,
        "score_total": d.score,
        "reason": d.reason,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="晴空万里云买入点规则引擎")
    parser.add_argument(
        "--cases",
        default=str(ROOT / "data" / "samples" / "qingkong_cases.json"),
        help="样本 JSON 路径",
    )
    args = parser.parse_args()
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    rows = [evaluate_case(c) for c in cases]
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

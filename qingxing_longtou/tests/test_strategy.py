"""策略单元测试（离线样本，不依赖外网）。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.models import Board, LimitBreakInfo, LimitUpInfo, MarketSnapshot, Stock
from engine.strategy import StrategyParams, run_strategy
from sources.tdx import TdxSource


class StrategyTests(unittest.TestCase):
    def test_focus_mainline_leader(self) -> None:
        boards = [
            Board("B1", "主线题材", "concept", change_percent=5.5, amount=2e9, main_net_inflow=5e8, up_count=40, down_count=5),
            Board("B2", "支线热闹", "concept", change_percent=2.0, amount=5e8, main_net_inflow=1e7, up_count=20, down_count=15),
        ]
        stocks = {
            "B1": [
                Stock("100001", "真龙股份", price=20, change_percent=10.0, amount=9e8, board_code="B1", board_name="主线题材"),
                Stock("100002", "跟风股份", price=15, change_percent=6.0, amount=2e8, board_code="B1", board_name="主线题材"),
            ],
            "B2": [
                Stock("200001", "局部热股", price=10, change_percent=8.0, amount=3e8, board_code="B2", board_name="支线热闹"),
            ],
        }
        zt = {
            "100001": LimitUpInfo("100001", "真龙股份", first_seal_time=93012, consecutive_boards=3, seal_amount=1e8, open_count=0),
        }
        snap = MarketSnapshot(
            trade_date="20260904",
            source="test",
            boards=boards,
            stocks_by_board=stocks,
            zt_by_code=zt,
        )
        rows = run_strategy(snap, StrategyParams(top_boards=5, min_change_pct=1.0))
        self.assertTrue(rows)
        self.assertEqual(rows[0].code, "100001")
        self.assertIn(rows[0].attention, ("聚焦", "观察"))
        self.assertTrue(any("主线" in t or "总龙头" in rows[0].rank_label for t in rows[0].tags) or "总龙头" in rows[0].rank_label)

    def test_weakness_break_lowers_attention(self) -> None:
        boards = [
            Board("B1", "测试板块", "concept", change_percent=4.0, amount=1e9, main_net_inflow=1e8, up_count=30, down_count=8),
        ]
        stocks = {
            "B1": [
                Stock("300001", "炸板股", price=18, change_percent=7.0, amount=4e8, board_code="B1", board_name="测试板块", main_net_inflow=-8e7),
            ]
        }
        zb = {"300001": LimitBreakInfo("300001", "炸板股", first_seal_time=100000, open_count=3, change_percent=7.0)}
        snap = MarketSnapshot("20260904", "test", boards=boards, stocks_by_board=stocks, zb_by_code=zb)
        rows = run_strategy(snap, StrategyParams(min_change_pct=1.0))
        self.assertTrue(rows)
        self.assertTrue(rows[0].weakness_flags)
        self.assertIn(rows[0].attention, ("观察", "回避"))


class TdxExportTests(unittest.TestCase):
    def test_sample_export(self) -> None:
        src = TdxSource(export_dir=ROOT / "plugins" / "tdx" / "export")
        self.assertTrue(src.available())
        snap = src.fetch_snapshot("20260904")
        self.assertGreaterEqual(len(snap.boards), 2)
        rows = run_strategy(snap)
        self.assertTrue(any(r.code == "688001" for r in rows))


if __name__ == "__main__":
    unittest.main()

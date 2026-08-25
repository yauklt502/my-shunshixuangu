"""Unit tests for quiet relative-strength rules. No network."""

from __future__ import annotations

import unittest

from screener.rules import (
    Bar,
    board_limit_pct,
    evaluate_quiet_rs,
    is_near_limit,
    score_quiet_rs,
    snapshot_today_quiet,
    turnover_pct,
)


def _bars(start: str, closes: list[float], vols: list[float] | None = None) -> list[Bar]:
    # start is unused except as prefix; dates are 2026-08-01 + i
    out = []
    vols = vols or [10000.0] * len(closes)
    y, m, d = 2026, 7, 20
    for i, c in enumerate(closes):
        day = d + i
        mm, dd = m, day
        while dd > 28:
            dd -= 28
            mm += 1
        ds = f"{y}-{mm:02d}-{dd:02d}"
        o = c * 0.995
        out.append(Bar(d=ds, o=o, c=c, h=c * 1.01, l=c * 0.99, v=vols[i]))
    return out


class BoardLimitTest(unittest.TestCase):
    def test_main_board(self):
        self.assertEqual(board_limit_pct("600519", "贵州茅台"), 10.0)
        self.assertEqual(board_limit_pct("000001", "平安银行"), 10.0)

    def test_chinext_star(self):
        self.assertEqual(board_limit_pct("300750", "宁德时代"), 20.0)
        self.assertEqual(board_limit_pct("688981", "中芯国际"), 20.0)

    def test_st(self):
        self.assertEqual(board_limit_pct("000001", "*ST示例"), 5.0)


class TurnoverTest(unittest.TestCase):
    def test_lots_to_pct(self):
        # 124000 手, 2.022e8 流通股 -> ~6.13%
        self.assertAlmostEqual(turnover_pct(124000, 202283850), 6.13, places=2)


class QuietRsTest(unittest.TestCase):
    def _index(self, bars: list[Bar], down_dates: set[str], down_pct: float = -1.0) -> dict[str, float]:
        out = {}
        for b in bars[1:]:
            out[b.d] = down_pct if b.d in down_dates else 0.5
        return out

    def test_quiet_grind_passes(self):
        closes = [10 + i * 0.12 for i in range(18)]  # ~1.2%/day grind
        bars = _bars("x", closes)
        down = {bars[i].d for i in (4, 7, 10, 13, 16)}
        idx = self._index(bars, down, -0.8)
        circ = 10000 * 10000 / 0.8  # v=10000 手 → 约 0.8% 换手
        m = evaluate_quiet_rs(bars, idx, circ_shares=circ, limit_pct=10.0, window=15)
        self.assertTrue(m.ok, m.reason)
        self.assertGreaterEqual(m.rs_up_rate, 0.6)
        self.assertGreater(m.score, 40)

    def test_limit_up_rejected(self):
        closes = [10.0]
        for _ in range(16):
            closes.append(round(closes[-1] * 1.101, 4))
        bars = _bars("x", closes)
        down = {bars[i].d for i in (3, 6, 9, 12)}
        idx = self._index(bars, down)
        m = evaluate_quiet_rs(bars, idx, circ_shares=1e9, limit_pct=10.0, window=15)
        self.assertFalse(m.ok)
        self.assertIn(m.reason, ("near_limit", "spike", "avg_up_out_of_band"))

    def test_follows_index_down_rejected(self):
        closes = [10.0]
        # go up most days, dump on the same days the index dumps
        dates_idx_down = {4, 7, 10, 13, 16}
        for i in range(1, 18):
            if i in dates_idx_down:
                closes.append(closes[-1] * 0.985)
            else:
                closes.append(closes[-1] * 1.012)
        bars = _bars("x", closes)
        down = {bars[i].d for i in dates_idx_down}
        idx = self._index(bars, down, -1.0)
        circ = 10000 * 10000 / 1.0
        m = evaluate_quiet_rs(bars, idx, circ_shares=circ, limit_pct=10.0, window=15)
        self.assertFalse(m.ok)
        self.assertEqual(m.reason, "rs_up_rate")

    def test_high_turnover_rejected(self):
        closes = [10 + i * 0.1 for i in range(18)]
        bars = _bars("x", closes, vols=[5e6] * 18)
        down = {bars[i].d for i in (4, 7, 10, 13, 16)}
        idx = self._index(bars, down)
        m = evaluate_quiet_rs(bars, idx, circ_shares=1e8, limit_pct=10.0, window=15)
        self.assertFalse(m.ok)
        self.assertEqual(m.reason, "turnover_high")

    def test_today_gate(self):
        self.assertTrue(snapshot_today_quiet(stock_ret_pct=1.2, index_ret_pct=-0.8, turnover_pct_today=1.0, limit_pct=10))
        self.assertFalse(snapshot_today_quiet(stock_ret_pct=1.2, index_ret_pct=0.5, turnover_pct_today=1.0, limit_pct=10))
        self.assertFalse(snapshot_today_quiet(stock_ret_pct=9.8, index_ret_pct=-1.0, turnover_pct_today=1.0, limit_pct=10))

    def test_near_limit(self):
        self.assertTrue(is_near_limit(9.7, 10.0))
        self.assertFalse(is_near_limit(3.0, 10.0))

    def test_score_prefers_higher_rs(self):
        a = score_quiet_rs(rs_up_rate=1.0, rs_excess_pct=2.0, avg_up_pct=1.5, avg_turn_pct=1.0, max_dd_pct=-1.0, up_day_ratio=0.7, vol_ratio=1.0)
        b = score_quiet_rs(rs_up_rate=0.6, rs_excess_pct=0.4, avg_up_pct=1.5, avg_turn_pct=1.0, max_dd_pct=-1.0, up_day_ratio=0.7, vol_ratio=1.0)
        self.assertGreater(a, b)


if __name__ == "__main__":
    unittest.main()

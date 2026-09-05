import unittest

from dragon.backtest import _tag_mainline_membership
from dragon.themes import plate_theme
from dragon.xuangubao import normalize_xgb, ts_to_fbt


class PlateMergeTest(unittest.TestCase):
    def test_agri_merge(self):
        self.assertEqual(plate_theme("养猪"), "农业养殖")
        self.assertEqual(plate_theme("大农业"), "农业养殖")
        self.assertEqual(plate_theme("大消费"), "大消费")
        self.assertEqual(plate_theme("短剧/互动影游"), "传媒")

    def test_fbt(self):
        from datetime import datetime
        from dragon.timeutil import CN
        ts = datetime(2026, 9, 4, 9, 36, 23, tzinfo=CN).timestamp()
        self.assertEqual(ts_to_fbt(ts), 93623)

    def test_tag_mainline(self):
        rows = [
            {"code": "1", "theme": "养猪", "themes": ["农业养殖"], "amount": 1},
            {"code": "2", "theme": "大农业", "themes": ["农业养殖"], "amount": 1},
            {"code": "5", "theme": "饲料", "themes": ["农业养殖"], "amount": 1},
            {"code": "3", "theme": "大消费", "themes": ["大消费"], "amount": 9},
            {"code": "4", "theme": "大消费", "themes": ["大消费"], "amount": 1},
        ]
        out = _tag_mainline_membership(rows)
        mains = [r for r in out if r["theme"] == "农业养殖"]
        self.assertGreaterEqual(len(mains), 2)

    def test_normalize_skips_st(self):
        self.assertIsNone(normalize_xgb({"stock_chi_name": "ST测试", "symbol": "000001.SZ"}))


if __name__ == "__main__":
    unittest.main()

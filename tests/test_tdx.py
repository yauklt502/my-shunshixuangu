import unittest

from dragon.tdx import FEED, pack_bar, pack_minute, pack_quote, to_tdx_code, ymd


class CodeNormTest(unittest.TestCase):
    def test_prefix(self):
        self.assertEqual(to_tdx_code("600108"), "sh600108")
        self.assertEqual(to_tdx_code("000592"), "sz000592")
        self.assertEqual(to_tdx_code("sh600108"), "sh600108")
        self.assertEqual(to_tdx_code("001366"), "sz001366")
        self.assertEqual(to_tdx_code("430047"), "bj430047")

    def test_ymd(self):
        self.assertEqual(ymd("20260904"), "2026-09-04")
        self.assertEqual(ymd("2026-09-04"), "2026-09-04")
        self.assertIsNone(ymd(""))


class PackTest(unittest.TestCase):
    def test_pack_quote_limit_up(self):
        class Lv:
            def __init__(self, price, volume):
                self.price = price
                self.volume = volume

        class Rec:
            last_price = 4.36
            last_close_price = 3.96
            open_price = 4.0
            high_price = 4.36
            low_price = 3.82
            amount = 9.44e8
            total_hand = 2275597
            code = "600108"
            buy_levels = (Lv(4.36, 361891), Lv(4.35, 10527))
            sell_levels = (Lv(0.0, 0),)

        q = pack_quote(Rec())
        self.assertEqual(q["change_pct"], 10.1)
        self.assertEqual(q["bids"][0]["volume"], 361891)
        self.assertEqual(q["asks"][0]["price"], 0.0)

    def test_pack_bar_and_minute(self):
        from datetime import datetime

        class Bar:
            time = datetime(2026, 9, 4, 15, 0)
            open = 4.0
            high = 4.36
            low = 3.82
            close = 4.36
            volume_lots = 2275597.6
            amount = 9.44e8

        b = pack_bar(Bar())
        self.assertEqual(b["close"], 4.36)
        self.assertIn("2026-09-04", b["time"])

        class P:
            time_label = "09:31"
            time = None
            price = 4.0
            avg_price = 4.01
            volume = 100

        class S:
            trading_date = None
            prev_close = 3.96
            open_price = 4.0
            points = (P(),)

        m = pack_minute(S())
        self.assertEqual(m["points"][0]["time"], "09:31")
        self.assertEqual(m["prev_close"], 3.96)


class LiveTdxTest(unittest.TestCase):
    def test_bundle_real_host(self):
        try:
            data = FEED.bundle("600108", "20260904")
        except Exception as exc:
            self.skipTest(str(exc))
        self.assertTrue(data["ok"])
        self.assertEqual(data["tdx_code"], "sh600108")
        self.assertGreaterEqual(len(data["kline"]["bars"]), 20)
        self.assertGreaterEqual(len(data["minute"]["points"]), 100)
        self.assertTrue(data["quote"]["bids"])
        k1 = FEED.kline("600108", "1m", 20)
        self.assertGreaterEqual(len(k1["bars"]), 5)


if __name__ == "__main__":
    unittest.main()

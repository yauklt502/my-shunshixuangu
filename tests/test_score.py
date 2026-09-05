import unittest

from dragon.decide import sentiment_score
from dragon.engine import analyze, resolve_mode, score_universe
from dragon.pipeline import apply_mainline_lane, pick_mainline, pick_secondary, pick_watch, rank_themes
from dragon.score import is_yizi, volume_verdict


def row(**kwargs):
    base = {
        "code": "000001",
        "name": "测试股",
        "industry": "出版",
        "theme": "出版",
        "price": 10.0,
        "change_pct": 10.0,
        "amount": 5e8,
        "circ_mv": 70e8,
        "turnover": 8.0,
        "boards": 5,
        "first_seal": 93109,
        "seal_fund": 8e7,
        "open_count": 2,
        "sealed": True,
        "volume_ratio": 1.8,
        "high": 10.0,
        "pre_close": 9.09,
    }
    base.update(kwargs)
    return base


def sample_rows():
    return [
        row(code="605577", name="龙版传媒", industry="出版", theme="出版", boards=5, first_seal=93109, amount=4.95e8, turnover=7.27, open_count=2),
        row(code="601949", name="中国出版", industry="出版", theme="出版", boards=1, first_seal=94840, amount=3.06e8, turnover=2.81, open_count=0),
        row(code="600108", name="亚盛集团", industry="种植业", theme="农业养殖", boards=2, first_seal=93623, amount=9.44e8, turnover=11.69, open_count=1),
        row(code="600354", name="敦煌种业", industry="种植业", theme="农业养殖", boards=1, first_seal=95108, amount=12.4e8, turnover=27.9, open_count=19),
        row(code="001366", name="播恩集团", industry="饲料", theme="农业养殖", boards=1, first_seal=94448, amount=2.06e8, turnover=9.39, open_count=0),
        row(code="000592", name="平潭发展", industry="林业Ⅱ", theme="林业Ⅱ", boards=1, first_seal=104303, amount=24.7e8, turnover=17.8, open_count=1),
        row(code="605580", name="恒盛能源", industry="电力", theme="电力", boards=2, first_seal=92501, amount=0.81e8, turnover=1.29, open_count=0),
        row(code="000892", name="欢瑞世纪", industry="影视院线", theme="影视院线", boards=1, first_seal=95430, amount=16.6e8, turnover=43.85, open_count=20),
    ]


CONCEPTS = [
    {"f12": "BK1508", "f14": "畜禽饲料", "f3": 8.46, "f104": 9, "f105": 0, "f128": "播恩集团", "f140": "001366"},
    {"f12": "BK9999", "f14": "合成生物", "f3": 4.0, "f104": 12, "f105": 0, "f128": "平潭发展", "f140": "000592"},
]


def run(rows=None, popularity=None, mode="盘后"):
    return analyze(
        rows or sample_rows(),
        popularity=popularity if popularity is not None else {"000592": 1, "600108": 3, "001366": 8},
        concepts=CONCEPTS,
        mode=mode,
    )


class VolumeRulesTest(unittest.TestCase):
    def test_yizi(self):
        self.assertTrue(is_yizi(92501, 0, 1.3))
        self.assertFalse(is_yizi(93109, 0, 7.2))
        self.assertFalse(is_yizi(92501, 2, 1.3))

    def test_healthy_vs_climax(self):
        v, s, _ = volume_verdict(turnover=7.3, amount_yi=5.0, volume_ratio=1.5, open_count=2, yizi=False)
        self.assertEqual(v, "健康换手")
        self.assertGreaterEqual(s, 80)
        v2, s2, _ = volume_verdict(turnover=43.8, amount_yi=16.6, volume_ratio=4.0, open_count=20, yizi=False)
        self.assertEqual(v2, "爆量见顶")
        self.assertLess(s2, s)
        v3, _, _ = volume_verdict(turnover=29.0, amount_yi=8.0, volume_ratio=3.0, open_count=2, yizi=False)
        self.assertEqual(v3, "爆量见顶")


class HumanLaneTest(unittest.TestCase):
    def test_mainline_watch_and_three_hats(self):
        result = run()
        self.assertEqual(result["mainline"]["theme"], "农业养殖")
        self.assertGreaterEqual(result["mainline"]["count"], 3)
        self.assertEqual(result["secondary"]["theme"], "出版")
        self.assertIsNotNone(result["watch"])
        self.assertEqual(result["watch"].code, "600108")
        self.assertIn("明天开盘只盯", result["action"])
        self.assertEqual(result["decision"].watch_hat, "情绪龙头")

        d = result["decision"]
        self.assertEqual(d.locomotive.code, "600108")
        self.assertEqual(d.sentiment.code, "600108")
        self.assertEqual(d.height.code, "605577")

        by = {s.code: s for s in result["scored"]}
        self.assertEqual(by["605577"].lane, "次主线")
        self.assertIn("空间高标", by["605577"].hats)
        self.assertTrue(by["605577"].pass_leader)
        self.assertFalse(by["605577"].in_mainline)
        self.assertTrue(by["600108"].in_mainline)
        self.assertIn("情绪龙头", by["600108"].hats)
        self.assertIn("火车头", by["600108"].hats)
        self.assertEqual(by["000592"].role, "独立票")
        self.assertEqual(by["000892"].role, "见顶观察")
        self.assertEqual(by["605580"].role, "高度锚")
        self.assertTrue(by["605580"].yizi)

        self.assertEqual(result["steps"][0]["title"], "先定板块再定票")
        self.assertTrue(result["steps"][0]["pass"])
        self.assertIn("农业养殖", result["steps"][0]["detail"])
        self.assertEqual(result["steps"][4]["title"], "情绪能不能叫出来")

    def test_hot_isolated_is_not_sentiment(self):
        result = run()
        by = {s.code: s for s in result["scored"]}
        self.assertEqual(by["000592"].pop_rank, 1)
        self.assertLess(sentiment_score(by["000592"]), 0)
        self.assertNotEqual(result["decision"].sentiment.code, "000592")

    def test_intraday_same_watch_different_action(self):
        result = run(mode="盘中")
        self.assertEqual(result["watch"].code, "600108")
        self.assertIn("盘中只跟", result["action"])

    def test_seal_order_skips_junk(self):
        ranked = rank_themes(sample_rows())
        main = pick_mainline(ranked)
        self.assertEqual(main["theme"], "农业养殖")
        self.assertEqual(pick_secondary(ranked, main)["theme"], "出版")
        scored = score_universe(sample_rows(), popularity={"600108": 3}, concepts=CONCEPTS)
        apply_mainline_lane(scored, "农业养殖")
        watch = pick_watch([s for s in scored if s.in_mainline])
        self.assertEqual(watch.code, "600108")

    def test_yizi_first_seal_skipped(self):
        rows = sample_rows()
        for r in rows:
            if r["code"] == "600108":
                r["first_seal"] = 92501
                r["open_count"] = 0
                r["turnover"] = 1.1
                r["amount"] = 0.6e8
        result = run(rows, popularity={"001366": 4})
        self.assertEqual(result["decision"].locomotive.code, "001366")
        self.assertEqual(result["watch"].code, "001366")

    def test_isolated_high_is_space_not_trash(self):
        only = row(code="605577", name="龙版传媒", theme="出版", industry="出版", boards=5, first_seal=93109, amount=4.95e8, turnover=7.27, open_count=2)
        result = run([only], popularity={"605577": 2})
        self.assertIsNone(result["mainline"])
        self.assertEqual(result["decision"].height.code, "605577")
        self.assertEqual(result["decision"].sentiment.code, "605577")
        self.assertEqual(result["watch"].code, "605577")
        self.assertEqual(result["scored"][0].role, "情绪龙头")
        self.assertNotEqual(result["scored"][0].role, "独立票")

    def test_isolated_low_cannot_pass(self):
        only = row(code="123456", name="孤雁", theme="航运港口", industry="航运港口", boards=2, first_seal=93840, amount=12e8, turnover=19.8, open_count=9)
        scored = score_universe([only], popularity={}, concepts=[])
        self.assertEqual(scored[0].dimensions["drive"].verdict, "独立板")
        self.assertFalse(scored[0].pass_leader)
        self.assertEqual(scored[0].role, "独立票")

    def test_theme_height_beats_first_one_board(self):
        rows = [
            row(code="1", name="先锋", theme="农业养殖", industry="种植业", boards=1, first_seal=93000, amount=3e8, turnover=8.0, open_count=0),
            row(code="2", name="高标", theme="农业养殖", industry="种植业", boards=3, first_seal=94000, amount=6e8, turnover=10.0, open_count=1),
            row(code="3", name="跟风", theme="农业养殖", industry="种植业", boards=1, first_seal=95000, amount=2e8, turnover=7.0, open_count=0),
        ]
        result = run(rows, popularity={"2": 5})
        self.assertEqual(result["decision"].locomotive.code, "2")
        self.assertEqual(result["watch"].code, "2")

    def test_sentiment_prefers_mainline_over_side_height(self):
        result = run(popularity={"605577": 1, "600108": 3})
        self.assertEqual(result["decision"].height.code, "605577")
        self.assertEqual(result["decision"].sentiment.code, "600108")
        self.assertEqual(result["watch"].code, "600108")

    def test_height_with_top_pop_can_be_sentiment(self):
        result = run(popularity={"605577": 1, "600108": 20})
        self.assertEqual(result["decision"].sentiment.code, "605577")
        self.assertEqual(result["watch"].code, "605577")
        self.assertEqual(result["decision"].watch_hat, "情绪龙头")
        self.assertEqual(result["decision"].locomotive.code, "600108")

    def test_mode_from_session(self):
        self.assertEqual(resolve_mode({"live": True}), "盘中")
        self.assertEqual(resolve_mode({"live": False}), "盘后")
        self.assertEqual(resolve_mode({"live": False}, "盘中"), "盘中")


if __name__ == "__main__":
    unittest.main()

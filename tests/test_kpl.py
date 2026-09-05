import unittest
from datetime import datetime

from dragon.kpl import (
    kpl_row_to_zt,
    parse_expression,
    parse_limit_row,
    parse_mood,
    parse_plates,
    parse_tianti,
    plates_as_concepts,
    rows_from_info,
    ts_to_fbt,
)
from dragon.market import fuse_broken, fuse_concepts, fuse_indexes, fuse_zt, overlay_kpl
from dragon.themes import plate_theme, theme_of
from dragon.timeutil import CN


TIANTI = {
    "StockList": [
        ["600108", "亚盛集团", 2, 1788485783, "801464", "农业", 0, 1, 11, 944000000, 3000000000],
        ["605577", "龙版传媒", 5, 1788485469, "801999", "AI应用", 0, 1, 5, 495000000, 800000000],
        ["001366", "播恩集团", 1, 1788486288, "801464", "农业", 0, 1, 11, 206000000, 3000000000],
    ],
    "ZhuShuList": [
        ["801464", "农业", 11, 3000000000, "600108,001366,600354"],
        ["801999", "AI应用", 5, 800000000, "605577"],
    ],
    "errcode": "0",
}


class ParseKplTest(unittest.TestCase):
    def test_ts_to_fbt_unix_and_hhmmss(self):
        self.assertEqual(ts_to_fbt(93623), 93623)
        self.assertEqual(ts_to_fbt(0), 0)
        dt = datetime(2026, 9, 4, 9, 36, 23, tzinfo=CN)
        self.assertEqual(ts_to_fbt(int(dt.timestamp())), 93623)

    def test_tianti_maps_nongye_and_keeps_ai(self):
        stocks, zhu = parse_tianti(TIANTI)
        by = {s["code"]: s for s in stocks}
        self.assertEqual(by["600108"]["plate"], "农业")
        self.assertEqual(by["600108"]["theme"], "农业养殖")
        self.assertEqual(by["600108"]["first_seal"], ts_to_fbt(1788485783))
        self.assertEqual(by["605577"]["theme"], "AI应用")
        self.assertEqual(zhu[0]["theme"], "农业养殖")
        self.assertEqual(zhu[0]["count"], 11)
        self.assertNotEqual(by["605577"]["theme"], "出版")

    def test_nested_info_rows(self):
        raw = {
            "info": [
                [
                    [
                        "600108",
                        "亚盛集团",
                        0,
                        "",
                        1788485783,
                        "农业",
                        100,
                        200,
                        1,
                        2,
                        -1,
                        944000000,
                        "猪肉、农业",
                        70e8,
                        11.69,
                        1,
                        1,
                        2.0,
                        "",
                        "801464",
                        1,
                        4.36,
                        10.1,
                    ]
                ],
                "2026-09-04",
            ]
        }
        rows = [parse_limit_row(r) for r in rows_from_info(raw["info"])]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["code"], "600108")
        self.assertEqual(rows[0]["reason"], "农业")
        self.assertEqual(rows[0]["turnover"], 11.69)
        self.assertEqual(rows[0]["rebound"], 1)

    def test_mood_picks_requested_day(self):
        data = {
            "info": [
                {"strong": "45", "ztjs": "39", "lbgd": "5", "Day": "2026-09-05", "df_num": "1"},
                {"strong": "41", "ztjs": "38", "lbgd": "5", "Day": "2026-09-04", "df_num": "2"},
            ],
            "tip": "提示",
            "errcode": "0",
        }
        mood = parse_mood(data, "2026-09-04")
        self.assertEqual(mood["strong"], 41)
        self.assertEqual(mood["zt"], 38)
        self.assertEqual(mood["day"], "2026-09-04")

    def test_expression_and_plates(self):
        expr = parse_expression(
            {"info": [39, 6, 1, 5, 12.5, 20.0, 50.0, 18.2, 1.1, 2.0, 0.5, "题材存在炒作机会"]}
        )
        self.assertEqual(expr["zt"], 39)
        self.assertEqual(expr["max_boards"], 5)
        self.assertAlmostEqual(expr["broken_rate"], 18.2)
        plates = parse_plates(
            {"list": [["801464", "农业", 6105, 1.082, 0.1, 100, 20]]}
        )
        self.assertEqual(plates[0]["theme"], "农业养殖")
        self.assertAlmostEqual(plates[0]["pct"], 1.082)

    def test_kpl_row_does_not_invent_open_count(self):
        stocks, _ = parse_tianti(TIANTI)
        row = kpl_row_to_zt(stocks[0], {"rebound": 1, "turnover": 11.69, "reason": "农业"})
        self.assertEqual(row["open_count"], 0)
        self.assertEqual(row["theme"], "农业养殖")
        self.assertEqual(row["reason"], "农业")


class FuseLanesTest(unittest.TestCase):
    def test_kpl_theme_overrides_em_industry(self):
        em = [
            {
                "code": "600108",
                "name": "亚盛集团",
                "industry": "种植业",
                "theme": "农业养殖",
                "first_seal": 93623,
                "boards": 2,
                "open_count": 1,
                "amount": 9.44e8,
                "turnover": 11.69,
                "price": 4.36,
                "change_pct": 10.1,
                "circ_mv": 70e8,
                "seal_fund": 1,
                "sealed": True,
            }
        ]
        stocks, zhu = parse_tianti(TIANTI)
        kpl = {
            "tianti": stocks,
            "zhu": zhu,
            "details": {"600108": {"reason": "农业", "rebound": 1, "turnover": 99}},
            "plates": [{"id": "801464", "name": "农业", "pct": 1.08, "amount": 1, "theme": "农业养殖"}],
            "broken": [],
            "indexes": [],
        }
        rows, src = fuse_zt(em, kpl, {})
        by = {r["code"]: r for r in rows}
        self.assertEqual(src, "eastmoney")
        self.assertEqual(by["600108"]["theme"], "农业养殖")
        self.assertEqual(by["600108"]["industry"], "农业")
        self.assertEqual(by["600108"]["open_count"], 1)
        self.assertEqual(by["600108"]["first_seal"], 93623)
        self.assertEqual(by["600108"]["turnover"], 11.69)
        self.assertEqual(by["600108"]["reason"], "农业")
        self.assertEqual(by["605577"]["theme"], "AI应用")
        self.assertEqual(by["605577"]["theme_source"], "kaipanla")

    def test_empty_em_falls_back_to_kpl(self):
        stocks, zhu = parse_tianti(TIANTI)
        kpl = {"tianti": stocks, "zhu": zhu, "details": {}, "broken": [], "plates": [], "indexes": []}
        rows, src = fuse_zt([], kpl, {})
        self.assertEqual(src, "kaipanla")
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["open_count"], 0)

    def test_broken_keeps_em_open_count(self):
        em = [
            {
                "code": "123456",
                "name": "炸板股",
                "industry": "种植业",
                "theme": "农业养殖",
                "open_count": 6,
                "sealed": False,
            }
        ]
        kpl = {
            "broken": [
                {"code": "123456", "theme": "农业养殖", "themes": "农业", "name": "炸板股"}
            ]
        }
        rows, src = fuse_broken(em, kpl, {})
        self.assertEqual(src, "eastmoney")
        self.assertEqual(rows[0]["open_count"], 6)
        self.assertEqual(rows[0]["theme"], "农业养殖")

    def test_concepts_prefer_kpl_strength(self):
        kpl = {
            "plates": [{"id": "801464", "name": "农业", "pct": 1.08, "amount": 1, "theme": "农业养殖"}],
            "zhu": [{"name": "农业", "count": 11, "codes": ["600108"]}],
        }
        concepts, src = fuse_concepts([{"f14": "畜禽饲料", "f3": 8.4}], kpl)
        self.assertEqual(src, "kaipanla")
        self.assertEqual(concepts[0]["f14"], "农业")
        self.assertEqual(concepts[0]["f104"], 11)
        self.assertEqual(concepts[1]["f14"], "畜禽饲料")
        empty, src2 = fuse_concepts([], {"plates": [], "zhu": []})
        self.assertEqual(empty, [])
        self.assertIsNone(src2)
        idx, isrc = fuse_indexes([], {"indexes": [{"code": "000001", "name": "上证", "pct": 1.0}]})
        self.assertEqual(isrc, "kaipanla")
        self.assertEqual(idx[0]["code"], "000001")

    def test_plates_as_concepts_skip_missing_pct(self):
        out = plates_as_concepts([{"id": "1", "name": "农业", "pct": None, "amount": 0}], [])
        self.assertEqual(out, [])

    def test_overlay_does_not_clobber_seal(self):
        row = {"code": "600108", "first_seal": 93623, "boards": 2, "open_count": 1, "amount": 1, "theme": "x"}
        overlay_kpl(row, {"plate": "农业", "theme": "农业养殖", "first_seal": 92500, "boards": 9}, None)
        self.assertEqual(row["first_seal"], 93623)
        self.assertEqual(row["boards"], 2)
        self.assertEqual(row["theme"], "农业养殖")

    def test_theme_aliases(self):
        self.assertEqual(theme_of("农业"), "农业养殖")
        self.assertEqual(plate_theme("农业"), "农业养殖")
        self.assertEqual(plate_theme("AI应用"), "AI应用")
        self.assertEqual(plate_theme("大消费"), "大消费")


if __name__ == "__main__":
    unittest.main()

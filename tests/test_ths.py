import unittest

from dragon.ths import fuse_popularity, parse_hot_rows, ranks_from_rows


HOUR = {
    "status_code": 0,
    "data": {
        "stock_list": [
            {
                "order": 1,
                "code": "605577",
                "name": "龙版传媒",
                "analyse_title": "AI漫剧+出版发行",
                "tag": {"concept_tag": ["IP经济(谷子经济)"], "popularity_tag": "5天5板"},
            },
            {
                "order": 2,
                "code": "000592",
                "name": "平潭发展",
                "tag": {"popularity_tag": "首板涨停"},
            },
            {
                "order": 5,
                "code": "600108",
                "name": "亚盛集团",
                "tag": {"popularity_tag": "2天2板"},
            },
            {
                "order": 5,
                "code": "600108",
                "name": "亚盛集团重复",
            },
        ]
    },
}


class ThsHotParseTest(unittest.TestCase):
    def test_parse_order_and_tag(self):
        rows = parse_hot_rows(HOUR)
        self.assertEqual([r["code"] for r in rows], ["605577", "000592", "600108"])
        by = {r["code"]: r for r in rows}
        self.assertEqual(by["605577"]["rank"], 1)
        self.assertEqual(by["605577"]["tag"], "5天5板")
        self.assertEqual(by["600108"]["rank"], 5)
        self.assertEqual(ranks_from_rows(rows)["600108"], 5)

    def test_bad_status_empty(self):
        self.assertEqual(parse_hot_rows({"status_code": -1, "data": {"stock_list": [{"code": "1"}]}}), [])
        self.assertEqual(parse_hot_rows(None), [])

    def test_order_fallback_to_index(self):
        rows = parse_hot_rows(
            {
                "status_code": 0,
                "data": {"stock_list": [{"code": "600000", "name": "浦发银行"}]},
            }
        )
        self.assertEqual(rows[0]["rank"], 1)

    def test_fuse_ths_wins_whole_list(self):
        ths = {"605577": 1, "600108": 5}
        em = {"600108": 3, "001366": 8}
        ranks, src = fuse_popularity(ths, em)
        self.assertEqual(src, "tonghuashun")
        self.assertEqual(ranks, ths)
        self.assertNotIn("001366", ranks)

    def test_fuse_em_only_when_ths_empty(self):
        ranks, src = fuse_popularity({}, {"600108": 3})
        self.assertEqual(src, "eastmoney")
        self.assertEqual(ranks["600108"], 3)
        ranks, src = fuse_popularity(None, None)
        self.assertEqual(src, "")
        self.assertEqual(ranks, {})


if __name__ == "__main__":
    unittest.main()

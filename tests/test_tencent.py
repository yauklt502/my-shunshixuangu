import unittest

from dragon.tencent import board_ladder, parse_qq_line, parse_qq_text, qq_code, quote_incomplete


YASHENG = (
    'v_sh600108="1~亚盛集团~600108~4.36~3.96~4.00~2275598~1037157~1238441~4.36~361891~'
    "4.35~10527~4.34~436~4.33~1496~4.32~537~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~~"
    "20260904161444~0.40~10.10~4.36~3.82~4.36/2275598/944268799~2275598~94427~11.69~"
    "157.64~~4.36~3.82~13.64~84.89~84.89~1.96~4.36~3.56~0.92~374887~4.15~170.32~149.10"
    '~~~1.29~94426.8799~11.7284~269"'
)


class TencentParseTest(unittest.TestCase):
    def test_qq_code(self):
        self.assertEqual(qq_code("600108"), "sh600108")
        self.assertEqual(qq_code("000592"), "sz000592")
        self.assertEqual(qq_code("430047"), "bj430047")

    def test_yasheng_quote_maps_to_em_fields(self):
        row = parse_qq_line(YASHENG)
        self.assertEqual(row["f12"], "600108")
        self.assertEqual(row["f14"], "亚盛集团")
        self.assertAlmostEqual(row["f2"], 4.36)
        self.assertAlmostEqual(row["f3"], 10.10)
        self.assertAlmostEqual(row["f8"], 11.69)
        self.assertAlmostEqual(row["f10"], 0.92)
        self.assertAlmostEqual(row["f6"], 944268799)
        self.assertEqual(row["_src"], "tencent")

    def test_parse_text_multi(self):
        got = parse_qq_text(YASHENG + ";")
        self.assertEqual(list(got), ["600108"])

    def test_incomplete_quote(self):
        self.assertTrue(quote_incomplete(None))
        self.assertTrue(quote_incomplete({}))
        self.assertFalse(quote_incomplete({"f2": 4.36, "f8": 11.69}))

    def test_board_ladder(self):
        rows = [
            {"boards": 1, "sealed": True},
            {"boards": 1, "sealed": True},
            {"boards": 2, "sealed": True},
            {"boards": 5, "sealed": True},
            {"boards": 3, "sealed": False},
        ]
        self.assertEqual(
            board_ladder(rows),
            [{"boards": 1, "count": 2}, {"boards": 2, "count": 1}, {"boards": 5, "count": 1}],
        )


if __name__ == "__main__":
    unittest.main()

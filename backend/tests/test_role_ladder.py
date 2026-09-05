from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.role_ladder import classify_roles, detect_emotion_height


def stock(code: str, name: str, industry: str, boards: int, first_time: str, amount: float = 1e8) -> dict:
    return {
        "code": code,
        "market": "sz",
        "symbol": f"sz{code}",
        "name": name,
        "industry": industry,
        "boards": boards,
        "first_time": first_time,
        "amount": amount,
    }


class RoleLadderTest(unittest.TestCase):
    def test_connected_height_same_chief_and_sentiment(self) -> None:
        pool = [
            stock("000001", "甲", "出版", 5, "09:30:00"),
            stock("000002", "乙", "出版", 4, "09:35:00"),
            stock("000003", "丙", "出版", 3, "09:40:00"),
            stock("000004", "丁", "出版", 2, "09:50:00"),
            stock("000005", "戊", "通信", 2, "10:00:00"),
        ]
        h = detect_emotion_height(pool)
        self.assertFalse(h["isolated_height"])
        self.assertEqual(h["emotion_height"], 5)

        out = classify_roles(pool)
        ladder = out["dragon_ladder"]
        self.assertEqual(ladder["chief"]["name"], "甲")
        self.assertEqual(ladder["sentiment"]["name"], "甲")
        self.assertEqual(ladder["dragon2"]["name"], "乙")
        self.assertEqual(ladder["dragon3"]["name"], "丙")
        self.assertTrue(out["summary"]["same_chief_sentiment"])
        titles = next(s for s in out["stocks"] if s["name"] == "甲")["title_keys"]
        self.assertEqual(titles, ["chief", "sentiment"])

    def test_isolated_height_splits_chief_and_sentiment(self) -> None:
        pool = [
            stock("000001", "余波龙", "稀土", 8, "09:25:00"),
            stock("000010", "情绪甲", "饲料", 3, "09:31:00"),
            stock("000011", "情绪乙", "饲料", 3, "09:40:00"),
            stock("000012", "饲料丙", "饲料", 2, "09:50:00"),
            stock("000013", "饲料丁", "饲料", 1, "10:00:00"),
            stock("000020", "别的", "通信", 1, "10:10:00"),
        ]
        h = detect_emotion_height(pool)
        self.assertTrue(h["isolated_height"])
        self.assertEqual(h["market_max"], 8)
        self.assertEqual(h["emotion_height"], 3)

        out = classify_roles(pool)
        ladder = out["dragon_ladder"]
        self.assertEqual(ladder["chief"]["name"], "余波龙")
        self.assertEqual(ladder["sentiment"]["name"], "情绪甲")
        self.assertEqual(ladder["main_theme"], "饲料")
        self.assertEqual(ladder["dragon2"]["name"], "情绪乙")
        self.assertEqual(ladder["dragon3"]["name"], "饲料丙")
        self.assertFalse(out["summary"]["same_chief_sentiment"])

    def test_tie_max_boards_earlier_seal_wins_chief(self) -> None:
        pool = [
            stock("000001", "早封", "电力", 4, "09:26:00"),
            stock("000002", "晚封", "电力", 4, "09:40:00"),
            stock("000003", "三", "电力", 3, "09:50:00"),
        ]
        out = classify_roles(pool)
        self.assertEqual(out["dragon_ladder"]["chief"]["name"], "早封")
        self.assertEqual(out["dragon_ladder"]["dragon2"]["name"], "晚封")

    def test_single_two_board_no_second(self) -> None:
        pool = [
            stock("000001", "独苗", "传媒", 2, "09:30:00"),
            stock("000002", "一板", "传媒", 1, "09:40:00"),
        ]
        out = classify_roles(pool)
        self.assertEqual(out["dragon_ladder"]["chief"]["name"], "独苗")
        self.assertEqual(out["dragon_ladder"]["sentiment"]["name"], "独苗")
        # 主线只剩一板可以补龙二
        self.assertEqual(out["dragon_ladder"]["dragon2"]["name"], "一板")
        self.assertIsNone(out["dragon_ladder"]["dragon3"])


if __name__ == "__main__":
    unittest.main()

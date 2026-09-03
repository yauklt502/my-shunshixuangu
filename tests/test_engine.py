#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import build_review, score_cell, snapshot_path


def test_snapshot_20260903():
    review = build_review("2026-09-03", refresh=False)
    assert review["source"] == "snapshot"
    assert review["date"] == "2026-09-03"
    names = [row["name"] for row in review["table"]]
    assert names[:4] == ["国芳集团", "集泰股份", "海通发展", "恒盛能源"]
    assert "深中华A" in names
    assert review["tldr"]["verdict_class"] == "red"
    assert "一票否决" in review["tldr"]["verdict"]
    assert snapshot_path("2026-09-03").exists()


def test_score_cell():
    assert score_cell(1) == ("1", "ok")
    assert score_cell(0.5) == ("½", "half")
    assert score_cell(0) == ("0", "no")


if __name__ == "__main__":
    test_score_cell()
    test_snapshot_20260903()
    print("ok")

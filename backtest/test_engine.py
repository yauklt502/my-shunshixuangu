# -*- coding: utf-8 -*-
"""Overlapping-hold portfolio math (no market data)."""
from backtest.engine import overlapping_day_return, sleeve_session_return, _limit_open
import numpy as np
import pandas as pd


def test_overlapping_two_sleeves():
    # 两个槽各 1/2：一个赚 2%，一个亏 1% → 组合 +0.5%
    assert abs(overlapping_day_return([0.02, -0.01], 2) - 0.005) < 1e-12
    # 只有一个槽有仓，另一个空仓：1/2 * 2% = 1%
    assert abs(overlapping_day_return([0.02], 2) - 0.01) < 1e-12
    # 全日空仓
    assert overlapping_day_return([], 5) == 0.0
    # 隔夜 H=1 就是整份仓位
    assert overlapping_day_return([0.01], 1) == 0.01


def test_limit_open_thresholds():
    assert _limit_open("600000", 10.95, 10.0) is True
    assert _limit_open("600000", 10.94, 10.0) is False
    assert _limit_open("300001", 11.95, 10.0) is True
    assert _limit_open("300001", 11.94, 10.0) is False
    assert _limit_open("688001", 12.0, 10.0) is True


def test_sleeve_entry_skips_limit_up():
    idx = pd.to_datetime(["2024-01-02", "2024-01-03"])
    close_px = pd.DataFrame({"600000": [10.0, 10.5], "600001": [10.0, 10.2]}, index=idx)
    open_px = pd.DataFrame({"600000": [np.nan, 10.96], "600001": [np.nan, 10.10]}, index=idx)
    # 600000 涨停开盘买不进，只成交 600001
    r = sleeve_session_return(
        ["600000", "600001"],
        idx[1],
        idx[0],
        is_entry=True,
        open_px=open_px,
        close_px=close_px,
        charge_cost=False,
    )
    assert abs(r - (10.2 / 10.10 - 1.0)) < 1e-12


if __name__ == "__main__":
    test_overlapping_two_sleeves()
    test_limit_open_thresholds()
    test_sleeve_entry_skips_limit_up()
    print("test_engine ok")

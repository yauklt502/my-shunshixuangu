from auction_screener.rules import (
    is_auction_limit_up,
    is_main_board,
    is_st,
    numeric_ok,
    sequential_select,
    turnover_pct,
    vol_ratio,
)


def test_main_board_and_st():
    assert is_main_board("600519", "贵州茅台")
    assert is_main_board("000001", "平安银行")
    assert is_main_board("002415", "海康威视")
    assert not is_main_board("300750", "宁德时代")
    assert not is_main_board("688981", "中芯国际")
    assert not is_main_board("830799", "艾融软件")
    assert not is_main_board("600000", "ST示例")
    assert is_st("*ST海泰")
    assert is_st("退市海泰")


def test_auction_limit_up_inverse():
    # 昨收 10，主板涨停 11.00
    assert is_auction_limit_up(11.00, 10.0, "000001", "平安银行")
    assert is_auction_limit_up(10.99, 10.0, "000001", "平安银行")
    assert not is_auction_limit_up(10.50, 10.0, "000001", "平安银行")


def test_vol_ratio_and_turnover():
    # 竞价 2 万手，5日均量 48 万手 → 每分钟 2000 手 → 量比 10
    assert abs(vol_ratio(20_000, 480_000) - 10.0) < 1e-6
    assert abs(turnover_pct(1_000_000, 100_000_000) - 1.0) < 1e-6


def _row(**kwargs):
    base = {
        "code": "000001",
        "name": "平安银行",
        "is_auction_zt": False,
        "auction_shares": 2_000_000,
        "open_pct": 2.0,
        "vol_ratio": 10.0,
        "amt_ratio": 1.2,
        "turnover": 0.5,
        "vol_over_free": 0.01,
    }
    base.update(kwargs)
    return base


def test_numeric_ok_bounds():
    assert numeric_ok(_row())
    assert not numeric_ok(_row(auction_shares=1_000_000))  # 不大于 100 万
    assert not numeric_ok(_row(auction_shares=10_000_000))
    assert not numeric_ok(_row(open_pct=1.0))
    assert not numeric_ok(_row(vol_ratio=8.0))
    assert not numeric_ok(_row(amt_ratio=0.8))
    assert not numeric_ok(_row(turnover=2.0))


def test_sequential_top8_then_filters_then_top5():
    rows = []
    for i in range(12):
        rows.append(
            _row(
                code=f"00000{i}" if i < 10 else f"0000{i}",
                name=f"测试{i}",
                vol_over_free=0.10 - i * 0.005,
                auction_shares=2_000_000,
                # 前8里让第 0、1 只量比不合格，剩下 6 只过过滤，最终前5
                vol_ratio=7.0 if i < 2 else 12.0,
            )
        )
    # 创业板不应进池
    rows.append(_row(code="300001", name="创业", vol_over_free=0.9, vol_ratio=12.0))
    # 竞价涨停取反应剔除
    rows.append(_row(code="600000", name="浦发银行", is_auction_zt=True, vol_over_free=0.9, vol_ratio=12.0))

    out = sequential_select(rows)
    assert all(not r["code"].startswith("300") for r in out["universe"])
    assert all(not r["is_auction_zt"] for r in out["universe"])
    assert len(out["top8"]) == 8
    assert [r["name"] for r in out["top8"]] == [f"测试{i}" for i in range(8)]
    assert len(out["after_numeric"]) == 6
    assert len(out["top5"]) == 5
    assert [r["name"] for r in out["top5"]] == [f"测试{i}" for i in range(2, 7)]

from auction_screener.rules import (
    is_auction_limit_up,
    is_main_board,
    is_st,
    numeric_ok,
    optimized_numeric_ok,
    optimized_select,
    score_lianban,
    sequential_select,
    turnover_pct,
    vol_ratio,
    wr100_ok,
)
from app.service import wr100_select
from auction_screener.trajectory import (
    AuctionTick,
    TrajectoryState,
    hhmmss_from_str,
    score_trajectory,
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
    assert is_auction_limit_up(11.00, 10.0, "000001", "平安银行")
    assert is_auction_limit_up(10.99, 10.0, "000001", "平安银行")
    assert not is_auction_limit_up(10.50, 10.0, "000001", "平安银行")


def test_vol_ratio_and_turnover():
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
        "lbc": 1,
        "zbc": 0,
        "fbt": 93000,
        "mv_yi": 50.0,
        "hs": 5.0,
        "hy": "银行",
    }
    base.update(kwargs)
    return base


def test_numeric_ok_bounds():
    assert numeric_ok(_row())
    assert not numeric_ok(_row(auction_shares=1_000_000))
    assert not numeric_ok(_row(auction_shares=10_000_000))
    assert not numeric_ok(_row(open_pct=1.0))
    assert not numeric_ok(_row(vol_ratio=8.0))
    assert not numeric_ok(_row(amt_ratio=0.8))
    assert not numeric_ok(_row(turnover=2.0))


def test_optimized_tightens_useless_caps():
    # 原版能过、优化版应拒绝：量比 50、金额比 20、涨幅 9%
    assert numeric_ok(_row(vol_ratio=50, amt_ratio=20, open_pct=9.0, turnover=0.5))
    assert not optimized_numeric_ok(_row(vol_ratio=50, amt_ratio=1.2, open_pct=3.0))
    assert not optimized_numeric_ok(_row(vol_ratio=12, amt_ratio=20, open_pct=3.0))
    assert not optimized_numeric_ok(_row(vol_ratio=12, amt_ratio=1.2, open_pct=9.0))
    assert not optimized_numeric_ok(_row(vol_ratio=12, amt_ratio=1.2, open_pct=3.0, turnover=0.1))
    assert not optimized_numeric_ok(_row(lbc=6, open_pct=3.0))
    assert not optimized_numeric_ok(_row(zbc=3, open_pct=3.0))
    assert not optimized_numeric_ok(_row(open_pct=3.0, hs=12.8))  # 金帝类昨换手
    assert not optimized_numeric_ok(_row(open_pct=3.95, lbc=2, hs=5.0))  # 二板偏高开
    assert optimized_numeric_ok(_row(open_pct=3.0, vol_ratio=12, amt_ratio=1.5, turnover=0.6))


def test_review_20260904_jindi_vs_hailiang():
    """金帝冲板回落应剔除；海量一进二应保留且分更高。"""
    from auction_screener.rules import wr100_ok
    from app.service import wr100_select

    jindi = _row(
        code="603270",
        name="金帝股份",
        open_pct=3.95,
        lbc=2,
        zbc=0,
        fbt=93351,
        hs=12.77,
        mv_yi=24.7,
        zt_days=4,
        zt_ct=3,
        hy="通用设备",
        vol_ratio=12,
        amt_ratio=1.5,
        turnover=0.6,
    )
    hailiang = _row(
        code="603138",
        name="海量数据",
        open_pct=3.45,
        lbc=1,
        zbc=1,
        fbt=93226,
        hs=3.35,
        mv_yi=41.8,
        zt_days=1,
        zt_ct=1,
        hy="IT服务Ⅱ",
        vol_ratio=12,
        amt_ratio=1.5,
        turnover=0.6,
    )
    assert not wr100_ok(jindi)
    assert not optimized_numeric_ok(jindi)
    assert wr100_ok(hailiang)
    out = wr100_select([jindi, hailiang], top_n=3)
    assert [r["name"] for r in out["top5"]] == ["海量数据"]
    sj, _ = score_lianban(jindi)
    sh, _ = score_lianban(hailiang)
    assert sh > sj


def test_sequential_top8_then_filters_then_top5():
    rows = []
    for i in range(12):
        rows.append(
            _row(
                code=f"00000{i}" if i < 10 else f"0000{i}",
                name=f"测试{i}",
                vol_over_free=0.10 - i * 0.005,
                auction_shares=2_000_000,
                vol_ratio=7.0 if i < 2 else 12.0,
            )
        )
    rows.append(_row(code="300001", name="创业", vol_over_free=0.9, vol_ratio=12.0))
    rows.append(_row(code="600000", name="浦发银行", is_auction_zt=True, vol_over_free=0.9, vol_ratio=12.0))

    out = sequential_select(rows)
    assert all(not r["code"].startswith("300") for r in out["universe"])
    assert all(not r["is_auction_zt"] for r in out["universe"])
    assert len(out["top8"]) == 8
    assert [r["name"] for r in out["top8"]] == [f"测试{i}" for i in range(8)]
    assert len(out["after_numeric"]) == 6
    assert len(out["top5"]) == 5
    assert [r["name"] for r in out["top5"]] == [f"测试{i}" for i in range(2, 7)]


def test_optimized_select_ranks_by_score():
    rows = [
        _row(code="000001", name="弱板", open_pct=1.8, fbt=145000, zbc=1, lbc=1, vol_over_free=0.02, hy="A", hs=5),
        _row(code="000002", name="强板", open_pct=3.5, fbt=93000, zbc=0, lbc=1, vol_over_free=0.015, hy="A", hs=4),
        _row(code="000003", name="巨量", open_pct=3.0, vol_ratio=40, amt_ratio=10, vol_over_free=0.05, hy="A"),
        _row(code="300001", name="创业", open_pct=3.5, vol_over_free=0.09, hy="A"),
    ]
    # 同板块再补两只，形成共振
    rows.append(_row(code="000004", name="同伴1", open_pct=3.0, hy="A", vol_over_free=0.01))
    rows.append(_row(code="000005", name="同伴2", open_pct=3.0, hy="A", vol_over_free=0.01))
    out = optimized_select(rows, top_n=3)
    names = [r["name"] for r in out["top5"]]
    assert "巨量" not in names
    assert "创业" not in names
    assert names[0] == "强板"
    assert out["top5"][0]["score"] >= out["top5"][-1]["score"]


def test_score_lianban_prefers_early_seal():
    early, _ = score_lianban(_row(fbt=93000, zbc=0, open_pct=3.5, lbc=2))
    late, _ = score_lianban(_row(fbt=145000, zbc=2, open_pct=3.5, lbc=2))
    assert early > late


def test_trajectory_rising_after_920():
    st = TrajectoryState()
    st.add(AuctionTick(ts=91530, px=10.20, prev_close=10.0, vol_shares=500_000))
    st.add(AuctionTick(ts=92010, px=10.25, prev_close=10.0, vol_shares=800_000))
    st.add(AuctionTick(ts=92300, px=10.40, prev_close=10.0, vol_shares=1_200_000, bid1_vol=10000, bid1_px=10.4, ask1_vol=1000, ask1_px=10.41))
    out = score_trajectory(st)
    assert out["traj_label"] == "升势确认"
    assert out["traj_score"] > 0


def test_trajectory_dump_after_fake_spike():
    st = TrajectoryState()
    st.add(AuctionTick(ts=91600, px=10.80, prev_close=10.0, vol_shares=900_000))
    st.add(AuctionTick(ts=92030, px=10.50, prev_close=10.0, vol_shares=1_000_000))
    st.add(AuctionTick(ts=92400, px=10.20, prev_close=10.0, vol_shares=1_100_000))
    out = score_trajectory(st)
    assert out["traj_label"] == "冲高回落"
    assert out["traj_score"] < 0


def test_hhmmss_parse():
    assert hhmmss_from_str("09:20:15") == 92015
    assert hhmmss_from_str("92015") == 92015

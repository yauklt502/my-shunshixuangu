from auction_screener.rules import (
    yijin2_ok,
    yijin2_select,
    score_yijin2,
    wr100_ok,
)


def _ashare(**kw):
    base = {
        "code": "600108",
        "name": "亚盛集团",
        "is_auction_zt": False,
        "open_pct": 1.01,
        "lbc": 1,
        "zbc": 1,
        "fbt": 94055,
        "hs": 9.7,
        "mv_yi": 77.0,
        "hy": "种植业",
        "vol_over_free": 0.01,
        "auction_shares": 2_000_000,
        "vol_ratio": 10,
        "amt_ratio": 1.2,
        "turnover": 0.5,
    }
    base.update(kw)
    return base


def test_yijin2_catches_yasheng_and_haitong():
    yasheng = _ashare()
    haitong = _ashare(
        code="603162",
        name="海通发展",
        open_pct=0.98,
        zbc=5,
        fbt=93424,
        hs=18.4,
        mv_yi=56.0,
        hy="航运港口",
    )
    jindi = _ashare(
        code="603270",
        name="金帝股份",
        open_pct=3.95,
        lbc=2,
        zbc=0,
        hs=12.8,
        mv_yi=25.0,
    )
    hailiang = _ashare(
        code="603138",
        name="海量数据",
        open_pct=3.45,
        lbc=1,
        zbc=1,
        hs=3.35,
        mv_yi=42.0,
    )
    assert yijin2_ok(yasheng)
    assert yijin2_ok(haitong)
    assert not yijin2_ok(jindi)  # 二板偏高开，非弱转强
    assert not yijin2_ok(hailiang)  # 开盘 3.45% 超出弱转强上限
    assert not wr100_ok(yasheng)  # 旧高开方案故意选不中微高开

    out = yijin2_select([yasheng, haitong, jindi, hailiang], top_n=2)
    names = [r["name"] for r in out["top5"]]
    assert "亚盛集团" in names
    assert "海通发展" in names
    assert "金帝股份" not in names
    # 亚盛换手更健康，分应不低于海通
    assert score_yijin2(yasheng)[0] >= score_yijin2(haitong)[0]

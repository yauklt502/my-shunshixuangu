from auction_screener.rules import (
    CAT_1J2,
    CAT_2J3,
    CAT_SHOUBAN,
    erjinsan_ok,
    shouban_ok,
    weak_select,
    yijin2_ok,
    wr100_ok,
)


def _row(**kw):
    base = {
        "code": "600108",
        "name": "亚盛集团",
        "src": "zt",
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


def test_three_categories_separated():
    shouban = _row(
        code="600172",
        name="黄河旋风",
        src="zb",
        lbc=0,
        open_pct=1.2,
        zbc=3,
        hs=15.0,
        mv_yi=80.0,
        hy="通用设备",
    )
    yasheng = _row()
    haitong = _row(
        code="603162",
        name="海通发展",
        open_pct=0.98,
        zbc=5,
        fbt=93424,
        hs=18.4,
        mv_yi=56.0,
        hy="航运港口",
    )
    erban = _row(
        code="600001",
        name="二进三样例",
        lbc=2,
        open_pct=1.1,
        zbc=0,
        fbt=93100,
        hs=6.0,
        mv_yi=40.0,
        hy="示例",
    )
    jindi = _row(
        code="603270",
        name="金帝股份",
        open_pct=3.95,
        lbc=2,
        zbc=0,
        hs=12.8,
        mv_yi=25.0,
    )

    assert shouban_ok(shouban)
    assert not yijin2_ok(shouban)
    assert yijin2_ok(yasheng)
    assert yijin2_ok(haitong)
    assert erjinsan_ok(erban)
    assert not erjinsan_ok(jindi)  # 开盘过高
    assert not shouban_ok(yasheng)  # 涨停池首板走一进二
    assert not wr100_ok(yasheng)

    out = weak_select([shouban, yasheng, haitong, erban, jindi], top_n=2)
    cats = out["categories"]
    assert cats[CAT_SHOUBAN][0]["name"] == "黄河旋风"
    names_1 = [r["name"] for r in cats[CAT_1J2]]
    assert "亚盛集团" in names_1 and "海通发展" in names_1
    assert cats[CAT_2J3][0]["name"] == "二进三样例"
    assert all(r["name"] != "金帝股份" for rows in cats.values() for r in rows)


def test_category_order_in_flat():
    rows = [
        _row(code="600001", name="A首", src="zb", lbc=0, open_pct=1.0, zbc=2, hs=10, mv_yi=50),
        _row(code="600002", name="B一二", lbc=1, open_pct=1.0, zbc=0, hs=8, mv_yi=50),
        _row(code="600003", name="C二三", lbc=2, open_pct=1.0, zbc=0, hs=8, mv_yi=50),
    ]
    out = weak_select(rows, top_n=1)
    flat_names = [r["name"] for r in out["top5"]]
    assert flat_names == ["A首", "B一二", "C二三"]

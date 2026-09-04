from app.service import auction_phase, wr100_ok, wr100_select


def test_auction_phase_keys():
    p = auction_phase(93000)
    assert p["phase"] == "trading"
    assert "clock" in p
    p2 = auction_phase(92200)
    assert p2["phase"] == "decision"


def test_wr100_select():
    rows = [
        {
            "code": "000001",
            "name": "平安银行",
            "is_auction_zt": False,
            "open_pct": 3.5,
            "lbc": 1,
            "zbc": 0,
            "fbt": 93000,
            "mv_yi": 50,
            "hy": "银行",
            "vol_over_free": 0.01,
            "auction_shares": 2_000_000,
            "vol_ratio": 12,
            "amt_ratio": 1.2,
            "turnover": 0.5,
        },
        {
            "code": "000002",
            "name": "过宽",
            "is_auction_zt": False,
            "open_pct": 6.5,
            "lbc": 1,
            "zbc": 0,
            "fbt": 93000,
            "mv_yi": 50,
            "hy": "银行",
            "vol_over_free": 0.02,
        },
    ]
    assert wr100_ok(rows[0])
    assert not wr100_ok(rows[1])
    out = wr100_select(rows, top_n=3)
    assert len(out["top5"]) == 1
    assert out["top5"][0]["code"] == "000001"
    assert out["top5"][0].get("tp_hint") == 0.008

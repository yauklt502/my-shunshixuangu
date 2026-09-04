from strategy.engine import (
    Candidate,
    pick_confirmed_leaders,
    resolve_board_path,
    score_for_leader_confirm,
    _is_yizi,
)


def test_yizi_detection():
    assert _is_yizi(92500, 0, 0.5) is True
    assert _is_yizi(93006, 0, 5.0) is False
    assert _is_yizi(92500, 2, 0.5) is False


def test_yizi_score_excluded():
    score, _, note = score_for_leader_confirm(
        open_pct=10.0,
        sealed=True,
        is_yizi=True,
        open_count=0,
        seal_fund_yi=5.0,
        turnover=0.5,
        prev_boards=4,
        change_pct=10.0,
        today_boards=5,
    )
    assert score <= -100
    assert "一字" in note


def test_height_beats_low_board_auction():
    """高度龙应压过低位 2 板强竞价。"""
    high, _, _ = score_for_leader_confirm(
        open_pct=1.0,
        sealed=True,
        is_yizi=False,
        open_count=2,
        seal_fund_yi=0.8,
        turnover=12.0,
        prev_boards=5,
        change_pct=10.0,
        today_boards=6,
    )
    low, _, _ = score_for_leader_confirm(
        open_pct=9.0,
        sealed=True,
        is_yizi=False,
        open_count=0,
        seal_fund_yi=4.0,
        turnover=6.0,
        prev_boards=1,
        change_pct=10.0,
        today_boards=2,
    )
    assert high > low


def test_failed_promotion_not_picked_over_sealed():
    failed = Candidate(
        code="1",
        name="失败高位",
        industry="",
        prev_boards=4,
        prev_days=5,
        target_boards=5,
        open_pct=7.0,
        price=1.0,
        change_pct=-9.9,
        turnover=20.0,
        sealed=False,
        is_yizi=False,
        first_seal="-",
        open_count=0,
        seal_fund_yi=0.0,
        amount_yi=1.0,
        main_net_yi=None,
        score=20,
        score_detail={},
        rank_note="",
        status="晋级失败对照",
        role="掉队对照",
    )
    leader = Candidate(
        code="2",
        name="深中华A",
        industry="",
        prev_boards=5,
        prev_days=6,
        target_boards=6,
        open_pct=1.0,
        price=10.0,
        change_pct=10.0,
        turnover=12.0,
        sealed=True,
        is_yizi=False,
        first_seal="09:32:24",
        open_count=2,
        seal_fund_yi=0.6,
        amount_yi=5.0,
        main_net_yi=None,
        score=160,
        score_detail={},
        rank_note="",
        status="非一字6板确认",
        role="真龙头候选",
    )
    low = Candidate(
        code="3",
        name="弱二板",
        industry="",
        prev_boards=1,
        prev_days=2,
        target_boards=2,
        open_pct=9.0,
        price=8.0,
        change_pct=10.0,
        turnover=5.0,
        sealed=True,
        is_yizi=False,
        first_seal="09:30:00",
        open_count=0,
        seal_fund_yi=2.0,
        amount_yi=2.0,
        main_net_yi=None,
        score=90,
        score_detail={},
        rank_note="",
        status="非一字2板确认",
        role="真龙头候选",
    )
    picks = pick_confirmed_leaders([failed, low, leader], n=2)
    assert picks[0].name == "深中华A"
    assert all(p.sealed for p in picks)
    assert failed not in picks


def test_resolve_board_path():
    assert resolve_board_path(sealed=True, yesterday_ct=6, today_lbc=6) == (5, 6)
    assert resolve_board_path(sealed=False, yesterday_ct=4, today_lbc=0) == (4, 5)


if __name__ == "__main__":
    test_yizi_detection()
    test_yizi_score_excluded()
    test_height_beats_low_board_auction()
    test_failed_promotion_not_picked_over_sealed()
    test_resolve_board_path()
    print("ok")

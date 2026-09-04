from strategy.engine import pick_confirmed_leaders, score_for_leader_confirm, _is_yizi


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
    )
    assert score <= -100
    assert "不可交易" in note or "一字" in note


def test_strong_auction_beats_weak_height():
    strong, _, _ = score_for_leader_confirm(
        open_pct=7.0,
        sealed=True,
        is_yizi=False,
        open_count=0,
        seal_fund_yi=4.0,
        turnover=6.0,
        prev_boards=3,
        change_pct=10.0,
    )
    weak, _, _ = score_for_leader_confirm(
        open_pct=1.0,
        sealed=True,
        is_yizi=False,
        open_count=2,
        seal_fund_yi=0.6,
        turnover=12.0,
        prev_boards=6,
        change_pct=10.0,
    )
    assert strong > weak


def test_pick_skips_yizi():
    from strategy.engine import Candidate

    yizi = Candidate(
        code="1",
        name="一字",
        industry="",
        prev_boards=4,
        prev_days=4,
        target_boards=5,
        open_pct=10.0,
        price=1.0,
        change_pct=10.0,
        turnover=0.5,
        sealed=True,
        is_yizi=True,
        first_seal="09:25:00",
        open_count=0,
        seal_fund_yi=5.0,
        amount_yi=0.1,
        main_net_yi=None,
        score=-100,
        score_detail={},
        rank_note="",
        status="",
        role="高度锚",
    )
    a = Candidate(
        code="2",
        name="万向德农",
        industry="种植业",
        prev_boards=5,
        prev_days=8,
        target_boards=6,
        open_pct=9.5,
        price=10.0,
        change_pct=10.0,
        turnover=5.0,
        sealed=True,
        is_yizi=False,
        first_seal="09:30:06",
        open_count=0,
        seal_fund_yi=4.2,
        amount_yi=1.5,
        main_net_yi=None,
        score=90,
        score_detail={},
        rank_note="",
        status="",
        role="真龙头候选",
    )
    b = Candidate(
        code="3",
        name="青山纸业",
        industry="造纸",
        prev_boards=3,
        prev_days=3,
        target_boards=4,
        open_pct=6.9,
        price=3.8,
        change_pct=10.0,
        turnover=5.5,
        sealed=True,
        is_yizi=False,
        first_seal="09:30:33",
        open_count=0,
        seal_fund_yi=4.0,
        amount_yi=4.5,
        main_net_yi=None,
        score=85,
        score_detail={},
        rank_note="",
        status="",
        role="真龙头候选",
    )
    picks = pick_confirmed_leaders([yizi, a, b], n=2)
    assert [p.name for p in picks] == ["万向德农", "青山纸业"]


if __name__ == "__main__":
    test_yizi_detection()
    test_yizi_score_excluded()
    test_strong_auction_beats_weak_height()
    test_pick_skips_yizi()
    print("ok")

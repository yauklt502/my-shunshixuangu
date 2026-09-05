"""像人一样戴三顶帽子：火车头、情绪龙头、空间高标，再决定盯哪一只。

人不会只认「主线第一封」。先封的可能是一字，人气第一的可能是独立游资，
板最高的可能带着板块没跟风。三路都摆出来，盯的那只要说得清为什么。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dragon.defs import volume_ok_for_watch
from dragon.score import ScoredStock


@dataclass
class Decision:
    locomotive: ScoredStock | None = None
    sentiment: ScoredStock | None = None
    height: ScoredStock | None = None
    watch: ScoredStock | None = None
    reason: str = ""
    notes: list[str] = field(default_factory=list)
    watch_hat: str = ""


def _vol(s: ScoredStock) -> str:
    return s.dimensions["volume"].verdict


def _usable(s: ScoredStock) -> bool:
    return bool(s.sealed and s.tradable and volume_ok_for_watch(s.turnover, s.amount_yi, s.open_count, s.yizi))


def _pop_bucket(s: ScoredStock) -> int:
    pop = s.pop_rank if s.pop_rank else 99
    if pop <= 3:
        return 0
    if pop <= 10:
        return 1
    if pop <= 30:
        return 2
    return 3


def _vol_bucket(s: ScoredStock) -> int:
    v = _vol(s)
    if v == "健康换手":
        return 0
    if v in {"换手偏瘦", "换手偏大"}:
        return 1
    return 2


def pick_locomotive(rows: list[ScoredStock]) -> ScoredStock | None:
    """主线里最早封的能买的板。一字 / 爆量 / 烂板直接跳过。"""
    pool = [s for s in rows if s.lane == "主线" and _usable(s)]
    if not pool:
        return None
    pool.sort(
        key=lambda s: (
            s.first_seal_raw or 999999,
            s.open_count,
            _pop_bucket(s),
            _vol_bucket(s),
            -s.boards,
        )
    )
    return pool[0]


def pick_theme_height(rows: list[ScoredStock]) -> ScoredStock | None:
    pool = [s for s in rows if s.lane == "主线" and s.sealed and not s.yizi]
    if not pool:
        return None
    pool.sort(key=lambda s: (-s.boards, _vol_bucket(s), s.open_count, _pop_bucket(s)))
    return pool[0]


def pick_height(rows: list[ScoredStock]) -> ScoredStock | None:
    """全市场非一字最高连板。并列看换手、炸板、人气。"""
    pool = [s for s in rows if s.sealed and not s.yizi]
    if not pool:
        return None
    pool.sort(
        key=lambda s: (
            -s.boards,
            0 if s.lane in {"主线", "次主线"} else 1,
            _vol_bucket(s),
            s.open_count,
            _pop_bucket(s),
        )
    )
    return pool[0]


def sentiment_score(s: ScoredStock) -> float:
    """情绪围着谁转。人气是加分，独立低板一票否决，一字/爆量/烂板重罚。"""
    if not s.sealed:
        return -999.0
    if s.peer_zt <= 1 and s.boards < 4:
        return -80.0
    if s.yizi:
        return -60.0

    score = 0.0
    if s.pop_rank and s.pop_rank <= 3:
        score += 40.0
    elif s.pop_rank and s.pop_rank <= 10:
        score += 25.0
    elif s.pop_rank and s.pop_rank <= 30:
        score += 12.0

    if s.lane == "主线":
        score += 20.0
    elif s.lane == "次主线":
        score += 12.0
    elif s.boards >= 4:
        score += 10.0

    if s.boards >= 5:
        score += 16.0
    elif s.boards >= 3:
        score += 12.0
    elif s.boards >= 2:
        score += 8.0
    elif s.boards == 1:
        score += 2.0

    v = _vol(s)
    if v == "健康换手":
        score += 10.0
    elif v in {"换手偏瘦", "换手偏大"}:
        score += 4.0
    if s.climax:
        score -= 30.0
    if s.rotten:
        score -= 25.0
    if s.yizi:
        score -= 40.0

    rec = s.dimensions["recognition"].verdict
    if rec in {"人气前三", "高度辨识"}:
        score += 8.0
    elif rec in {"人气前十", "成交额焦点"}:
        score += 4.0
    return score


def pick_sentiment(rows: list[ScoredStock]) -> ScoredStock | None:
    """今天情绪围着谁转。独立1–2板即使人气第一也只是热点。"""
    scored: list[tuple[float, ScoredStock]] = []
    for s in rows:
        pts = sentiment_score(s)
        if pts < 28.0:
            continue
        if s.yizi or not s.sealed:
            continue
        scored.append((pts, s))
    if not scored:
        return None
    scored.sort(
        key=lambda x: (
            -x[0],
            0 if x[1].lane == "主线" else 1,
            _pop_bucket(x[1]),
            -x[1].boards,
            x[1].open_count,
        )
    )
    return scored[0][1]


def _same(a: ScoredStock | None, b: ScoredStock | None) -> bool:
    return bool(a and b and a.code == b.code)


def _label(s: ScoredStock | None) -> str:
    if not s:
        return "无"
    pop = f"人气{s.pop_rank}" if s.pop_rank else "人气未上榜"
    return f"{s.name}（{s.boards}板·{s.theme}·{pop}）"


def _next_mainline(rows: list[ScoredStock], skip: ScoredStock | None) -> ScoredStock | None:
    pool = [s for s in rows if s.lane == "主线" and _usable(s) and (not skip or s.code != skip.code)]
    if not pool:
        return None
    pool.sort(key=lambda s: (s.first_seal_raw or 999999, s.open_count, _vol_bucket(s), -s.boards))
    return pool[0]


def wear_hats(
    rows: list[ScoredStock],
    *,
    locomotive: ScoredStock | None,
    sentiment: ScoredStock | None,
    height: ScoredStock | None,
) -> None:
    hats: dict[str, list[str]] = {}

    def add(s: ScoredStock | None, hat: str) -> None:
        if not s:
            return
        hats.setdefault(s.code, []).append(hat)

    add(locomotive, "火车头")
    add(sentiment, "情绪龙头")
    add(height, "空间高标")
    for s in rows:
        s.hats = hats.get(s.code, [])
        if "情绪龙头" in s.hats and "火车头" in s.hats:
            s.role = "情绪龙头"
            s.status = "主线火车头兼情绪龙"
        elif "情绪龙头" in s.hats:
            s.role = "情绪龙头"
            s.status = "今天情绪围着它转"
        elif "火车头" in s.hats:
            s.role = "火车头"
            s.status = "主线里先起来的能买的板"
        elif "空间高标" in s.hats:
            s.role = "空间高标"
            s.status = "非一字最高板，高度对照"
        elif s.lane == "独立" and s.boards < 4:
            s.role = s.role or "独立票"
        elif s.lane in {"支线", "次主线"} and s.role not in {"空间龙", "见顶观察", "高度锚", "独立票"}:
            if s.role in {"主线龙", "先锋", "龙头候选"}:
                s.role = f"{s.lane}对照"


def decide(
    rows: list[ScoredStock],
    *,
    mainline_name: str | None,
    mode: str,
) -> Decision:
    loco = pick_locomotive(rows)
    theme_h = pick_theme_height(rows)
    height = pick_height(rows)
    sentiment = pick_sentiment(rows)
    notes: list[str] = []

    # 主线里如果后封的身位明显更高，人会认板块高标，不认首板先锋。
    if loco and theme_h and not _same(loco, theme_h) and _usable(theme_h):
        if theme_h.boards >= loco.boards + 1 and _vol(theme_h) != "爆量见顶":
            notes.append(f"主线里{theme_h.name}比先封的{loco.name}高{theme_h.boards - loco.boards}板，火车头改认身位")
            loco = theme_h

    watch: ScoredStock | None = None
    hat = ""
    reason = ""

    sent_usable = bool(sentiment and _usable(sentiment))
    loco_usable = bool(loco and _usable(loco))
    height_usable = bool(height and _usable(height))

    if sent_usable and sentiment and sentiment.climax:
        sent_usable = False
        notes.append(f"{sentiment.name}人气在，但量已经散了，情绪龙不当盯")

    if sent_usable and sentiment:
        watch, hat = sentiment, "情绪龙头"
        if _same(sentiment, loco):
            reason = f"{_label(sentiment)}又是主线火车头，情绪和带动叠在一起，盯它。"
        elif _same(sentiment, height):
            reason = f"{_label(sentiment)}是空间高标，人气也在它身上，今天情绪就在高度上，盯它。"
        elif sentiment.lane != "主线":
            reason = (
                f"{_label(sentiment)}不在主线{mainline_name or ''}，但叫得出来。"
                f"主线火车头是{_label(loco)}，先认情绪，火车头当对照。"
            )
        else:
            reason = f"{_label(sentiment)}人气和辨识度在主线里最像龙。火车头是{_label(loco)}，空间是{_label(height)}。"
    elif loco_usable and loco:
        watch, hat = loco, "火车头"
        if sentiment and not sent_usable:
            reason = f"情绪龙{_label(sentiment)}已经散了，退回主线火车头{_label(loco)}。"
        else:
            reason = f"没有更像情绪的票，盯主线火车头{_label(loco)}。空间高标{_label(height)}只对照。"
    else:
        nxt = _next_mainline(rows, loco)
        if nxt:
            watch, hat = nxt, "主线次选"
            reason = f"火车头买不到或已经散了，主线往后顺到{_label(nxt)}。"
        elif height_usable and height:
            watch, hat = height, "空间高标"
            reason = f"主线没有能买的板，才盯空间高标{_label(height)}。"
        else:
            reason = "今天没有能买的龙：主线不成形，或者只剩一字/爆量/烂板。"

    if watch and _vol(watch) in {"换手偏瘦", "换手偏大"}:
        notes.append(f"{watch.name}{_vol(watch)}，能盯，但仓位要轻")
    if height and watch and not _same(height, watch):
        if height.peer_zt <= 1:
            notes.append(f"{height.name}是高度，但板块没跟风，不当唯一盯")
        else:
            notes.append(f"空间对照：{_label(height)}")
    if loco and watch and not _same(loco, watch):
        notes.append(f"火车头对照：{_label(loco)}")

    wear_hats(rows, locomotive=loco, sentiment=sentiment, height=height)
    if watch:
        if hat and hat not in watch.hats:
            watch.hats = [hat] + list(watch.hats)

    return Decision(
        locomotive=loco,
        sentiment=sentiment,
        height=height,
        watch=watch,
        reason=reason,
        notes=notes,
        watch_hat=hat,
    )


def watch_action(mode: str, watch: ScoredStock | None, hat: str) -> str:
    if not watch:
        return "今日无龙，空仓看戏"
    who = f"{watch.name}（{hat or '定龙'}）"
    if mode == "盘中":
        return f"盘中只跟{who}，另外两路只对照，不换来换去"
    return f"明天开盘只盯{who}，不在杂毛里找补"

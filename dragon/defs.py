"""定龙头用到的硬定义。人看盘先问「这是什么」，再问「盯谁」。

一字 / 烂板 / 爆量 是否决项，不是分数游戏。
主线 / 次主线 / 支线 / 独立 是通道，不是把票扔进垃圾桶。
火车头 / 情绪龙头 / 空间高标 是三顶帽子，可以戴在同一只上，也可以分开。
"""

from __future__ import annotations

from typing import Any

# 页面和 API 共用，改定义先改这里。
DEFINITIONS: list[dict[str, str]] = [
    {
        "name": "一字板",
        "rule": "首封≤09:25:05，且盘中未开板，且换手<3%。",
        "use": "买不到。不当火车头、不当情绪龙、不当盯。只当高度锚。",
    },
    {
        "name": "烂板",
        "rule": "炸≥6次；或炸≥3次且换手≥20%。",
        "use": "封不住。主线里往后顺一位，不跟它定情绪。",
    },
    {
        "name": "爆量见顶",
        "rule": "换手≥35%；或换手≥28%且炸≥2次。",
        "use": "量已经散了。降级对照，不盯。",
    },
    {
        "name": "健康换手",
        "rule": "换手5–22%，且成交额≥1.5亿。",
        "use": "抛压被接住。3–5%偏瘦、22–28%偏大，能当候选，不宜当唯一盯。",
    },
    {
        "name": "主线",
        "rule": "非「其他/ST/未知」，涨停家数最多且≥2。家数并列先比成交，再比最高板。",
        "use": "先定板块。情绪通常围着主线转。",
    },
    {
        "name": "次主线",
        "rule": "家数≥2，且家数≥主线−1；或最高板≥4且家数≥主线−2。",
        "use": "不是空气。里面的高标可以当空间/情绪对照。",
    },
    {
        "name": "支线",
        "rule": "不是主线/次主线，但家数≥2或最高板≥3。",
        "use": "高标留下对照，不进主线火车头池。",
    },
    {
        "name": "独立票",
        "rule": "主题只有1家，且连板<4。",
        "use": "游资热点。人气再高也不当情绪龙。",
    },
    {
        "name": "空间高标",
        "rule": "全市场非一字最高连板。并列看人气、换手健康、炸得少。4板+即使主题只有1家也算空间龙。",
        "use": "高度对照。板块没跟风时不当唯一盯。",
    },
    {
        "name": "火车头",
        "rule": "主线里最早封的可交易板：跳过一字、爆量、烂板。",
        "use": "谁先把主线拉起来。先封的那只如果买不到，就看下一只。",
    },
    {
        "name": "情绪龙头",
        "rule": "今天情绪围着谁转：人气能叫出来，最好在主线，必须能买。不是谁板最高，也不是谁最先封。",
        "use": "独立1–2板即使人气第一也只是热点。独立4板+且有辨识度，可以兼总龙和情绪。人气是加分，不是硬门槛。",
    },
    {
        "name": "盯1只",
        "rule": "情绪龙健康就盯它；它散了退回火车头；火车头也废就主线下一只；主线没有能买的，才盯空间高标。",
        "use": "盘中跟、盘后盯同一只。另外两路只对照，不换来换去。",
    },
]


JUNK_THEMES = frozenset({"其他", "ST股", "未知"})


def is_yizi(first_seal: int, open_count: int, turnover: float) -> bool:
    """9:25 附近封死、未开板、换手极低 = 一字无量。"""
    if open_count > 0 or first_seal <= 0:
        return False
    return first_seal <= 92505 and turnover < 3.0


def is_climax(turnover: float, open_count: int) -> bool:
    return turnover >= 35.0 or (turnover >= 28.0 and open_count >= 2)


def is_rotten(open_count: int, turnover: float) -> bool:
    if open_count >= 6:
        return True
    return open_count >= 3 and turnover >= 20.0


def is_healthy_volume(turnover: float, amount_yi: float, yizi: bool = False) -> bool:
    if yizi:
        return False
    return 5.0 <= turnover <= 22.0 and amount_yi >= 1.5


def is_isolated_small(peer_zt: int, boards: int) -> bool:
    return peer_zt <= 1 and boards < 4


def is_space_dragon(peer_zt: int, boards: int, yizi: bool) -> bool:
    """4板以上即使没跟风，人也当高度/总龙看。一字只当锚。"""
    return boards >= 4 and not yizi and (peer_zt <= 1 or boards >= 4)


def volume_ok_for_watch(turnover: float, amount_yi: float, open_count: int, yizi: bool) -> bool:
    if yizi or is_climax(turnover, open_count) or is_rotten(open_count, turnover):
        return False
    if turnover < 3.0:
        return False
    return True


def lane_of(theme: str, theme_meta: dict[str, Any], mainline: str | None, secondary: str | None) -> str:
    if mainline and theme == mainline:
        return "主线"
    if secondary and theme == secondary:
        return "次主线"
    meta = theme_meta.get(theme) or {}
    count = int(meta.get("count") or 0)
    if count >= 2:
        return "支线"
    return "独立"


def classify_themes(
    ranked: list[dict[str, Any]],
    mainline: dict[str, Any] | None,
    secondary: dict[str, Any] | None,
) -> dict[str, str]:
    main_name = mainline["theme"] if mainline else None
    sec_name = secondary["theme"] if secondary else None
    meta = {x["theme"]: x for x in ranked}
    return {theme: lane_of(theme, meta, main_name, sec_name) for theme in meta}

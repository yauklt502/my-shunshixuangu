from __future__ import annotations

from collections import defaultdict
from typing import Any


ROLE_META = {
    "dragon": {"label": "龙头", "desc": "题材内连板高度最高、带动效应最强", "color": "#c2410c"},
    "mid": {"label": "中位股", "desc": "中期补涨/中位开挂（约3~5板），非龙头", "color": "#b45309"},
    "catchup": {"label": "补涨龙", "desc": "龙头高位或断板窗口下，低位启动承接", "color": "#0369a1"},
    "follower": {"label": "跟风", "desc": "跟随龙头的普通涨停", "color": "#64748b"},
}


def classify_roles(pool: list[dict[str, Any]]) -> dict[str, Any]:
    by_theme: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pool:
        theme = (row.get("industry") or "未分类").strip() or "未分类"
        by_theme[theme].append(dict(row))

    themes_out: list[dict[str, Any]] = []
    flat: list[dict[str, Any]] = []

    for theme, rows in by_theme.items():
        rows.sort(key=lambda x: (-int(x.get("boards") or 0), x.get("first_time") or "99:99:99"))
        max_boards = max((int(r.get("boards") or 0) for r in rows), default=0)

        theme_items: list[dict[str, Any]] = []
        for idx, r in enumerate(rows):
            boards = int(r.get("boards") or 0)
            role, position, reason = "follower", "后排", "普通跟风涨停"
            if idx == 0 and boards >= 2:
                role, position, reason = "dragon", f"高度龙 · {boards}板", f"{theme} 最高连板，定义为龙头"
            elif max_boards >= 5 and boards <= 2 and idx > 0:
                role, position, reason = "catchup", f"低位补涨 · {boards}板", f"龙头已到{max_boards}板，低位启动具备补涨龙气质"
            elif 3 <= boards <= 5 and idx > 0:
                role, position, reason = "mid", f"中位 · {boards}板", "非龙头的中位连板，对应中期补涨/中位开挂"
            elif boards >= max_boards - 1 and boards >= 3 and idx > 0:
                role, position, reason = "mid", f"中高位 · {boards}板", "贴近龙头高度但非定价核心，归为中位"

            item = {
                **r,
                "theme": theme,
                "role": role,
                "role_label": ROLE_META[role]["label"],
                "role_desc": ROLE_META[role]["desc"],
                "role_color": ROLE_META[role]["color"],
                "ladder_rank": idx + 1,
                "theme_max_boards": max_boards,
                "position": position,
                "reason": reason,
            }
            flat.append(item)
            theme_items.append(item)

        themes_out.append(
            {
                "theme": theme,
                "max_boards": max_boards,
                "count": len(rows),
                "dragon": next((x for x in theme_items if x["role"] == "dragon"), None),
                "mid": [x for x in theme_items if x["role"] == "mid"],
                "catchup": [x for x in theme_items if x["role"] == "catchup"],
                "all": theme_items,
            }
        )

    themes_out.sort(key=lambda t: (-t["max_boards"], -t["count"]))
    summary = {
        "dragon": sum(1 for x in flat if x["role"] == "dragon"),
        "mid": sum(1 for x in flat if x["role"] == "mid"),
        "catchup": sum(1 for x in flat if x["role"] == "catchup"),
        "follower": sum(1 for x in flat if x["role"] == "follower"),
        "themes": len(themes_out),
        "total": len(flat),
    }
    contrast = [
        {
            "role": "dragon",
            "label": "龙头",
            "timing": "主线初期~高潮",
            "position": "题材最高板",
            "vs_leader": "本身即定价锚",
            "risk": "情绪退潮时回撤大，但辨识度最高",
        },
        {
            "role": "mid",
            "label": "中位股",
            "timing": "主线中期",
            "position": "约3~5板中位开挂",
            "vs_leader": "伴随扩散，非龙头",
            "risk": "龙头一弱往往先掉队",
        },
        {
            "role": "catchup",
            "label": "补涨龙",
            "timing": "龙头末期/断板前后",
            "position": "低位重新启动",
            "vs_leader": "承接溢出，另起炉灶",
            "risk": "鱼尾阶段接力风险大",
        },
    ]
    return {
        "summary": summary,
        "contrast": contrast,
        "themes": themes_out,
        "stocks": flat,
        "role_meta": ROLE_META,
    }
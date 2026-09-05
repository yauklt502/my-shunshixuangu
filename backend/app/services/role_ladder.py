from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

ROLE_META = {
    "chief": {"label": "日内总龙头", "desc": "全市场最高连板，定价当日高度", "color": "#b91c1c"},
    "sentiment": {"label": "情绪龙头", "desc": "主线题材龙头，代表当日情绪方向", "color": "#a21caf"},
    "dragon2": {"label": "龙二", "desc": "情绪主线内高度/辨识度第二", "color": "#c2410c"},
    "dragon3": {"label": "龙三", "desc": "情绪主线内高度/辨识度第三", "color": "#ea580c"},
    "theme_dragon": {"label": "题材龙", "desc": "支线题材内最高板，非市场总龙", "color": "#c2410c"},
    "dragon": {"label": "龙头", "desc": "龙头家族（总龙/情绪龙/龙二/龙三/题材龙）", "color": "#c2410c"},
    "mid": {"label": "中位股", "desc": "中期补涨/中位开挂（约3~5板），非龙头", "color": "#b45309"},
    "catchup": {"label": "补涨龙", "desc": "龙头高位或断板窗口下，低位启动承接", "color": "#0369a1"},
    "follower": {"label": "跟风", "desc": "跟随龙头的普通涨停", "color": "#64748b"},
}

TITLE_PRIORITY = ("chief", "sentiment", "dragon2", "dragon3", "theme_dragon", "mid", "catchup", "follower")
DRAGON_FAMILY = {"chief", "sentiment", "dragon2", "dragon3", "theme_dragon", "dragon"}


def _boards(row: dict[str, Any]) -> int:
    return int(row.get("boards") or 0)


def _first_time(row: dict[str, Any]) -> str:
    return str(row.get("first_time") or "99:99:99")


def _amount(row: dict[str, Any]) -> float:
    return float(row.get("amount") or 0)


def _sid(row: dict[str, Any]) -> str:
    return str(row.get("symbol") or f"{row.get('market', '')}{row.get('code', '')}")


def _rank_key(row: dict[str, Any], theme_size: int = 0) -> tuple:
    # 更高板 > 更早封 > 更大题材 > 更大成交
    return (-_boards(row), _first_time(row), -theme_size, -_amount(row))


def _public(row: dict[str, Any]) -> dict[str, Any] | None:
    if not row:
        return None
    return {k: v for k, v in row.items() if k != "_titles"}


def detect_emotion_height(pool: list[dict[str, Any]]) -> dict[str, Any]:
    """判断高度是否断档，以及情绪真正落在几板。

    日内总龙头看最高板；若最高板孤立（只有 1 只，且没有差 1 板的衔接），
    情绪下移到下方成簇的高度——那才是当天在打的位置。
    """
    heights = [_boards(r) for r in pool]
    ge2 = [h for h in heights if h >= 2]
    if not heights:
        return {"market_max": 0, "emotion_height": 0, "isolated_height": False}
    market_max = max(heights)
    if not ge2:
        return {"market_max": market_max, "emotion_height": market_max, "isolated_height": False}

    at_max = sum(1 for h in heights if h == market_max)
    at_near = sum(1 for h in heights if h == market_max - 1)
    # 4 板以上且完全没有下一档衔接，视为余波/孤立高度
    isolated = market_max >= 4 and at_max == 1 and at_near == 0

    emotion_height = market_max
    if isolated:
        found = None
        for h in range(market_max - 1, 1, -1):
            if sum(1 for x in heights if x == h) >= 2:
                found = h
                break
        if found is None:
            clustered = Counter(h for h in heights if 2 <= h < market_max)
            if clustered:
                found = max(clustered, key=lambda h: (clustered[h], h))
        if found is not None:
            emotion_height = found
        else:
            isolated = False
            emotion_height = market_max

    return {
        "market_max": market_max,
        "emotion_height": emotion_height,
        "isolated_height": isolated,
        "at_max": at_max,
        "at_near": at_near,
    }


def pick_main_theme(
    by_theme: dict[str, list[dict[str, Any]]],
    emotion_height: int,
) -> str:
    """主线 = 情绪高度附近、跟风最宽、高度仍够的题材。"""
    best = ""
    best_score = (-1, -1, -1, -1)
    for theme, rows in by_theme.items():
        if not rows:
            continue
        max_b = max(_boards(r) for r in rows)
        around = sum(1 for r in rows if abs(_boards(r) - emotion_height) <= 1)
        at_h = sum(1 for r in rows if _boards(r) == emotion_height)
        score = (at_h, around, max_b, len(rows))
        if score > best_score:
            best_score = score
            best = theme
    return best


def classify_roles(pool: list[dict[str, Any]]) -> dict[str, Any]:
    by_theme: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pool:
        theme = (row.get("industry") or "未分类").strip() or "未分类"
        by_theme[theme].append(dict(row))

    theme_sizes = {t: len(rows) for t, rows in by_theme.items()}
    height_info = detect_emotion_height(pool)
    market_max = height_info["market_max"]
    emotion_height = height_info["emotion_height"]
    isolated = height_info["isolated_height"]
    main_theme = pick_main_theme(by_theme, emotion_height) if by_theme else ""

    # —— 市场席位：总龙头 / 情绪龙头 / 龙二 / 龙三 ——
    all_rows = [r for rows in by_theme.values() for r in rows]
    all_rows.sort(key=lambda r: _rank_key(r, theme_sizes.get((r.get("industry") or "").strip() or "未分类", 0)))

    chief = all_rows[0] if all_rows and _boards(all_rows[0]) >= 2 else None

    sentiment = None
    if main_theme and by_theme.get(main_theme):
        candidates = sorted(by_theme[main_theme], key=lambda r: _rank_key(r, theme_sizes[main_theme]))
        # 优先情绪高度上的票，否则题材内最高板
        at_emotion = [r for r in candidates if _boards(r) >= max(2, emotion_height)]
        pool_c = at_emotion or [r for r in candidates if _boards(r) >= 2] or candidates
        sentiment = pool_c[0] if pool_c else None
    if sentiment is None and chief is not None:
        sentiment = chief

    # 若高度并未断档，总龙头通常就是情绪龙头
    if chief is not None and sentiment is not None and not isolated:
        if _boards(chief) >= emotion_height:
            sentiment = chief

    taken = set()
    if chief is not None:
        taken.add(_sid(chief))
    if sentiment is not None:
        taken.add(_sid(sentiment))

    # 龙二龙三只从情绪主线里排，避免把无关支线 2 板硬塞进来
    line_rows = sorted(by_theme.get(main_theme, []), key=lambda r: _rank_key(r, theme_sizes.get(main_theme, 0)))
    seconds: list[dict[str, Any]] = []
    for r in line_rows:
        if _sid(r) in taken:
            continue
        seconds.append(r)
        if len(seconds) >= 2:
            break
    dragon2 = seconds[0] if seconds else None
    dragon3 = seconds[1] if len(seconds) > 1 else None

    titles_by_sid: dict[str, list[str]] = defaultdict(list)

    def award(row: dict[str, Any] | None, key: str) -> None:
        if row is None:
            return
        keys = titles_by_sid[_sid(row)]
        if key not in keys:
            keys.append(key)

    award(chief, "chief")
    award(sentiment, "sentiment")
    award(dragon2, "dragon2")
    award(dragon3, "dragon3")

    themes_out: list[dict[str, Any]] = []
    flat: list[dict[str, Any]] = []

    for theme, rows in by_theme.items():
        rows.sort(key=lambda x: _rank_key(x, len(rows)))
        max_boards = max((_boards(r) for r in rows), default=0)
        is_main = theme == main_theme

        theme_items: list[dict[str, Any]] = []
        for idx, r in enumerate(rows):
            boards = _boards(r)
            sid = _sid(r)
            extra_titles = list(titles_by_sid.get(sid, []))

            role, position, reason = "follower", "后排", "普通跟风涨停"
            if extra_titles:
                role = extra_titles[0]
            elif idx == 0 and boards >= 2:
                role = "theme_dragon"
                extra_titles = ["theme_dragon"]
            elif max_boards >= 5 and boards <= 2 and idx > 0:
                role = "catchup"
            elif 3 <= boards <= 5 and idx > 0:
                role = "mid"
            elif boards >= max_boards - 1 and boards >= 3 and idx > 0:
                role = "mid"

            if role == "chief":
                position, reason = f"总龙头 · {boards}板", f"全市场最高连板 {boards} 板，定价当日高度"
            elif role == "sentiment":
                position, reason = f"情绪龙头 · {boards}板", f"主线「{theme}」龙头，代表当日情绪方向"
            elif role == "dragon2":
                position, reason = f"龙二 · {boards}板", f"主线「{main_theme}」第二梯队"
            elif role == "dragon3":
                position, reason = f"龙三 · {boards}板", f"主线「{main_theme}」第三梯队"
            elif role == "theme_dragon":
                position, reason = f"题材龙 · {boards}板", f"{theme} 最高连板，支线龙头"
            elif role == "catchup":
                position, reason = f"低位补涨 · {boards}板", f"龙头已到{max_boards}板，低位启动具备补涨龙气质"
            elif role == "mid":
                position, reason = f"中位 · {boards}板", "非龙头的中位连板，对应中期补涨/中位开挂"

            # 兼任总龙+情绪龙时，把说明写清楚
            if "chief" in extra_titles and "sentiment" in extra_titles:
                position = f"总龙头·情绪龙 · {boards}板"
                reason = (
                    f"高度未断档，全市场最高板同时就是主线「{theme}」情绪锚"
                    if not isolated
                    else f"兼具最高板与主线「{theme}」情绪锚"
                )
            elif "chief" in extra_titles and isolated:
                reason = f"全市场最高 {boards} 板，但高度断档，情绪已下移到 {emotion_height} 板主线"

            # 展示标签：兼任时拼在一起
            label_keys = extra_titles or [role]
            role_label = "·".join(ROLE_META[k]["label"] for k in label_keys if k in ROLE_META)

            item = {
                **r,
                "theme": theme,
                "role": role,
                "role_label": role_label,
                "role_desc": ROLE_META.get(role, ROLE_META["follower"])["desc"],
                "role_color": ROLE_META.get(role, ROLE_META["follower"])["color"],
                "title_keys": label_keys,
                "titles": [ROLE_META[k]["label"] for k in label_keys if k in ROLE_META],
                "ladder_rank": idx + 1,
                "theme_max_boards": max_boards,
                "is_main_theme": is_main,
                "position": position,
                "reason": reason,
            }
            flat.append(item)
            theme_items.append(item)

        def by_key(key: str) -> list[dict[str, Any]]:
            return [x for x in theme_items if key in (x.get("title_keys") or [x["role"]])]

        themes_out.append(
            {
                "theme": theme,
                "max_boards": max_boards,
                "count": len(rows),
                "is_main": is_main,
                "dragon": next((x for x in theme_items if x["role"] in DRAGON_FAMILY), None),
                "mid": by_key("mid"),
                "catchup": by_key("catchup"),
                "all": theme_items,
            }
        )

    themes_out.sort(key=lambda t: (not t["is_main"], -t["max_boards"], -t["count"]))

    def find_titled(key: str) -> dict[str, Any] | None:
        for x in flat:
            if key in (x.get("title_keys") or []):
                return x
        return None

    chief_out = find_titled("chief")
    sent_out = find_titled("sentiment")
    d2_out = find_titled("dragon2")
    d3_out = find_titled("dragon3")

    if isolated and chief_out and sent_out and _sid(chief_out) != _sid(sent_out):
        note = f"高度断档：总龙头 {chief_out.get('name')} {chief_out.get('boards')}板孤立，情绪落在{emotion_height}板主线「{main_theme}」"
    elif chief_out and sent_out and _sid(chief_out) == _sid(sent_out):
        note = f"高度连续，{chief_out.get('name')} 同时是日内总龙头与情绪龙头"
    else:
        note = "当日龙头席位按连板高度、封板时间、主线宽度推断"

    order = {k: i for i, k in enumerate(TITLE_PRIORITY)}
    flat.sort(key=lambda x: (order.get(x["role"], 99), -_boards(x), _first_time(x)))

    summary = {
        "chief": 1 if chief_out else 0,
        "sentiment": 1 if sent_out else 0,
        "dragon2": 1 if d2_out else 0,
        "dragon3": 1 if d3_out else 0,
        "theme_dragon": sum(1 for x in flat if x["role"] == "theme_dragon"),
        "dragon": sum(1 for x in flat if x["role"] in DRAGON_FAMILY),
        "mid": sum(1 for x in flat if x["role"] == "mid"),
        "catchup": sum(1 for x in flat if x["role"] == "catchup"),
        "follower": sum(1 for x in flat if x["role"] == "follower"),
        "themes": len(themes_out),
        "total": len(flat),
        "same_chief_sentiment": bool(chief_out and sent_out and _sid(chief_out) == _sid(sent_out)),
    }

    contrast = [
        {
            "role": "chief",
            "label": "日内总龙头",
            "timing": "当日最高连板形成后",
            "position": "全市场最高板",
            "vs_leader": "高度锚，空间定价",
            "risk": "若高度断档，可能只是余波，带动有限",
        },
        {
            "role": "sentiment",
            "label": "情绪龙头",
            "timing": "主线被资金认出来之后",
            "position": "最宽主线的龙头（可与总龙同一人）",
            "vs_leader": "方向锚，跟风看它",
            "risk": "主线切换时身份失效最快",
        },
        {
            "role": "dragon2",
            "label": "龙二",
            "timing": "总龙/情绪龙确立后的第二辨识",
            "position": "主线内次高或次早",
            "vs_leader": "总龙的影子，常被当成替补龙",
            "risk": "总龙强时溢价不足，总龙倒了先砸",
        },
        {
            "role": "dragon3",
            "label": "龙三",
            "timing": "龙二之后的第三梯队",
            "position": "主线内第三",
            "vs_leader": "辨识度更弱，更像中军",
            "risk": "容易退化成跟风，空间不如前两名",
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
        "dragon_ladder": {
            "chief": _public(chief_out),
            "sentiment": _public(sent_out),
            "dragon2": _public(d2_out),
            "dragon3": _public(d3_out),
            "market_max_boards": market_max,
            "emotion_height": emotion_height,
            "isolated_height": isolated,
            "main_theme": main_theme,
            "note": note,
        },
    }

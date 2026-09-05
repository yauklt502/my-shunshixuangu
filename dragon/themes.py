"""把东财行业名收成可比较的主题，避免饲料/养殖被拆散后看不出共振。"""

from __future__ import annotations

# 只合并资金明显同一条主线的行业。影视不并进出版，避免烂板污染高度龙。
SUPER_THEME: dict[str, str] = {
    "饲料": "农业养殖",
    "养殖业": "农业养殖",
    "种植业": "农业养殖",
    "动物保健": "农业养殖",
    "渔业": "农业养殖",
    "畜禽饲料": "农业养殖",
    "生猪养殖": "农业养殖",
    "肉鸡养殖": "农业养殖",
    "其他养殖": "农业养殖",
    "海洋捕捞": "农业养殖",
    "动物保健Ⅱ": "农业养殖",
    "动物保健Ⅲ": "农业养殖",
    "农业": "农业养殖",
    "猪肉": "农业养殖",
    "种业": "农业养殖",
    "非白酒": "酒类",
    "白酒": "酒类",
    "啤酒": "酒类",
    "汽车零部": "汽车链",
    "汽车整车": "汽车链",
    "汽车服务": "汽车链",
}


def theme_of(industry: str | None) -> str:
    name = (industry or "").strip() or "未知"
    return SUPER_THEME.get(name, name)


def theme_label(theme: str) -> str:
    return theme or "未知"


# 用来把东财概念名扣回主题，看板块指数红不红。
THEME_KEYS: dict[str, tuple[str, ...]] = {
    "农业养殖": ("饲料", "养殖", "种植", "猪肉", "生猪", "畜禽", "农业", "肉鸡", "水产", "渔业", "粮食", "种业"),
    "酒类": ("酿酒", "白酒", "啤酒", "黄酒"),
    "汽车链": ("汽车", "车路", "智能驾驶"),
    "出版": ("出版", "图书", "传媒"),
    "传媒出版": ("出版", "传媒", "影视", "短剧"),
}


# 选股宝板块名 → 同一条资金主线。不把「大消费」并进农业。
PLATE_GROUPS: list[tuple[tuple[str, ...], str]] = [
    (("养猪", "生猪", "饲料", "农业", "种植", "种业", "禽", "水产", "渔业", "粮食", "玉米", "畜牧"), "农业养殖"),
    (("白酒", "啤酒", "黄酒", "酿酒"), "酒类"),
    (("短剧", "影视", "出版", "传媒", "游戏", "影游"), "传媒"),
    (("汽车", "智能驾驶"), "汽车链"),
]


def plate_theme(plate_name: str | None) -> str:
    name = (plate_name or "").strip() or "其他"
    if name in {"其他", "ST股"}:
        return name
    for words, theme in PLATE_GROUPS:
        if any(w in name for w in words):
            return theme
    return name


def concept_matches_theme(concept_name: str, theme: str) -> bool:
    name = concept_name or ""
    keys = THEME_KEYS.get(theme)
    if keys:
        return any(k in name for k in keys)
    return bool(theme) and theme in name

"""盘中/盘后同一套 6 步：先定板块，再只在主线里定票。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from dragon.score import ScoredStock, num
from dragon.themes import concept_matches_theme, theme_of


def skip_name(name: str) -> bool:
    return "ST" in (name or "").upper()


def rank_themes(zt_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in zt_rows:
        if skip_name(str(row.get("name") or "")):
            continue
        if not row.get("sealed", True):
            continue
        groups[str(row.get("theme") or theme_of(row.get("industry")))].append(row)

    ranked: list[dict[str, Any]] = []
    for theme, xs in groups.items():
        amount_yi = sum(num(x.get("amount")) for x in xs) / 1e8
        max_boards = max(int(x.get("boards") or 0) for x in xs)
        first = sorted(xs, key=lambda x: int(x.get("first_seal") or 999999))[0]
        strength = len(xs) * 25.0 + amount_yi * 1.5 + max_boards * 3.0
        ranked.append(
            {
                "theme": theme,
                "count": len(xs),
                "amount_yi": round(amount_yi, 2),
                "max_boards": max_boards,
                "strength": round(strength, 2),
                "first_name": str(first.get("name") or ""),
                "first_code": str(first.get("code") or ""),
                "first_seal": int(first.get("first_seal") or 0),
            }
        )
    ranked.sort(key=lambda x: (-x["strength"], -x["count"], -x["amount_yi"]))
    return ranked


def pick_mainline(ranked: list[dict[str, Any]]) -> dict[str, Any] | None:
    """涨停家数<2 的主题成不了主线。只取强度第一的那条。「其他」不算主线。"""
    clean = [x for x in ranked if x["theme"] not in {"其他", "ST股", "未知"}]
    if not clean or clean[0]["count"] < 2:
        return None
    return clean[0]


def match_theme_concepts(theme: str, concepts: list[dict]) -> list[dict]:
    hits = []
    for c in concepts:
        name = str(c.get("f14") or "")
        if not concept_matches_theme(name, theme):
            continue
        hits.append(
            {
                "name": name,
                "pct": num(c.get("f3")),
                "up": int(num(c.get("f104"))),
                "down": int(num(c.get("f105"))),
                "lead_name": str(c.get("f128") or ""),
                "lead_code": str(c.get("f140") or ""),
            }
        )
    hits.sort(key=lambda x: -x["pct"])
    return hits


def apply_mainline_lane(scored: list[ScoredStock], mainline: str | None) -> list[ScoredStock]:
    """支线再猛也不进定龙池。"""
    for s in scored:
        s.in_mainline = bool(mainline and s.theme == mainline)
        if not mainline:
            continue
        if s.in_mainline:
            continue
        if s.role in {"高度锚", "独立票", "见顶观察"}:
            s.status = f"支线·{s.status}"
            continue
        s.pass_leader = False
        s.role = "支线"
        s.status = f"今天主线是{mainline}，支线不进定龙池"
    return scored


def _drawdown(s: ScoredStock) -> float:
    ev = s.dimensions.get("resilience")
    if not ev:
        return 0.0
    for line in ev.evidence:
        if "回撤" in line:
            try:
                return float(line.split("回撤")[1].replace("%", ""))
            except (IndexError, ValueError):
                return 0.0
    return 0.0


def pick_watch(mainline_rows: list[ScoredStock]) -> ScoredStock | None:
    """主线里：先封 + 封得死 + 没烂板 + 量能过关。人气前三加权，但不替代封板顺序。"""
    pool = []
    for s in mainline_rows:
        if not s.sealed or s.yizi:
            continue
        vol = s.dimensions["volume"].verdict
        res = s.dimensions["resilience"].verdict
        if vol in {"一字无量", "爆量见顶"}:
            continue
        if res in {"放量烂板", "烂板", "跟跌/掉队"}:
            continue
        pool.append(s)
    if not pool:
        return None

    def key(s: ScoredStock) -> tuple:
        pop = s.pop_rank if s.pop_rank else 99
        pop_bucket = 0 if pop <= 3 else (1 if pop <= 10 else 2)
        vol_ok = 0 if s.dimensions["volume"].verdict == "健康换手" else 1
        return (
            s.first_seal_raw or 999999,
            s.open_count,
            pop_bucket,
            vol_ok,
            -s.boards,
            -s.amount_yi,
        )

    return sorted(pool, key=key)[0]


def build_steps(
    *,
    mode: str,
    mainline: dict[str, Any] | None,
    ranked: list[dict[str, Any]],
    scored: list[ScoredStock],
    broken: list[dict[str, Any]],
    concepts: list[dict],
    indexes: list[dict],
    watch: ScoredStock | None,
) -> tuple[list[dict[str, Any]], str]:
    theme = mainline["theme"] if mainline else None
    main_rows = [s for s in scored if theme and s.theme == theme]
    side = [x for x in ranked[1:4]] if ranked else []
    side_txt = "、".join(f"{x['theme']}{x['count']}只" for x in side) or "无"

    # 1 定板块
    if mainline:
        s1_pass, s1 = True, (
            f"主线={theme}：涨停{mainline['count']}只 / 成交{mainline['amount_yi']}亿 / "
            f"最高{mainline['max_boards']}板。支线{side_txt}不进定龙池。"
        )
    else:
        s1_pass, s1 = False, "没有≥2只涨停的主题，今天不定龙。"

    # 2 涨停时间排序
    ordered = sorted(main_rows, key=lambda s: (s.first_seal_raw or 999999, s.open_count))
    if ordered:
        head = ordered[0]
        firm = "零炸" if head.open_count == 0 else f"炸{head.open_count}次"
        ladder = " → ".join(f"{s.name}{s.first_seal}(炸{s.open_count})" for s in ordered[:5])
        s2_pass = head.open_count <= 2
        s2 = f"火车头初选 {head.name} {head.first_seal} {firm}。主线封板序：{ladder}"
    else:
        s2_pass, s2 = False, "主线没有可排序的涨停。"

    # 3 板块指数 + 跟风 + 炸了散不散
    hot = match_theme_concepts(theme, concepts) if theme else []
    top_c = hot[0] if hot else None
    theme_broken = [b for b in broken if theme_of(b.get("industry")) == theme] if theme else []
    sealed_n = len(main_rows)
    broken_n = len(theme_broken)
    scatter = broken_n / max(1, sealed_n + broken_n)
    if top_c:
        idx_txt = f"{top_c['name']} {top_c['pct']:+.2f}%（上涨{top_c['up']} / 下跌{top_c['down']}）领涨{top_c['lead_name']}"
        red = top_c["pct"] > 0 and top_c["up"] >= 3
    else:
        idx_txt = "未匹配到主题概念指数，改看涨停家数"
        red = sealed_n >= 3
    if scatter >= 0.45:
        scatter_txt = f"炸板{broken_n}只，散掉比例{scatter:.0%}，板块在散"
        s3_pass = False
    else:
        scatter_txt = f"炸板{broken_n}只，散掉比例{scatter:.0%}，板块还没散"
        s3_pass = red
    s3 = f"{idx_txt}。主线仍封{sealed_n}只，{scatter_txt}。"

    # 4 砸盘谁抗谁碎
    idx_txts = "，".join(f"{i.get('name')}{num(i.get('pct')):+.2f}%" for i in indexes[:3]) or "大盘指数暂缺"
    if main_rows:
        hold = sorted(main_rows, key=lambda s: (s.open_count, _drawdown(s), -s.boards))[0]
        frag = sorted(main_rows, key=lambda s: (-s.open_count, _drawdown(s)))[0]
        s4_pass = hold.open_count <= 2
        s4 = (
            f"{idx_txts}。主线最抗：{hold.name}炸{hold.open_count}次；"
            f"先碎：{frag.name}炸{frag.open_count}次。"
        )
    else:
        s4_pass, s4 = False, f"{idx_txts}。主线无样本。"

    # 5 人气
    top3 = [s for s in main_rows if s.pop_rank and s.pop_rank <= 3]
    if watch and watch.pop_rank and watch.pop_rank <= 3:
        s5_pass, s5 = True, f"{watch.name}人气第{watch.pop_rank}，主线里叫得出来。"
    elif top3:
        names = "、".join(f"{s.name}第{s.pop_rank}" for s in top3)
        s5_pass = bool(watch and watch.pop_rank and watch.pop_rank <= 10)
        s5 = f"人气前三在主线的有{names}。" + (
            f"盯的{watch.name}人气第{watch.pop_rank}，共识一般。" if watch and watch.pop_rank else "盯的票未进前十。"
        )
    else:
        s5_pass, s5 = False, "主线没有人气前三，共识偏弱，只能当观察。"

    # 6 量
    if not watch:
        s6_pass, s6 = False, "没有可留的票。"
    else:
        vol = watch.dimensions["volume"].verdict
        s6_pass = vol == "健康换手"
        extra = "留下。" if s6_pass else "降级，只能轻看。"
        if vol in {"一字无量", "爆量见顶"}:
            extra = "放弃。"
            s6_pass = False
        s6 = (
            f"{watch.name}换手{watch.turnover}% / 成交{watch.amount_yi}亿 / "
            f"量比{watch.volume_ratio if watch.volume_ratio is not None else '-'} → {vol}，{extra}"
        )

    action = "盘中只跟这一只，支线再猛也不换" if mode == "盘中" else "明天开盘只盯这一只，不在杂毛里找补"
    titles = [
        ("先定板块再定票", s1_pass, s1),
        ("涨停时间排序", s2_pass, s2),
        ("板块指数红不红", s3_pass, s3),
        ("砸盘谁抗谁碎", s4_pass, s4),
        ("人气能不能叫出来", s5_pass, s5),
        ("最后看量", s6_pass, s6),
    ]
    steps = []
    for i, (title, ok, detail) in enumerate(titles, 1):
        steps.append({"step": i, "title": title, "pass": ok, "detail": detail})
    return steps, action

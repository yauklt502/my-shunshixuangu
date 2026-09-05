"""盘中/盘后同一套：先定板块，再戴三顶帽子，最后盯一只。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from dragon.decide import Decision
from dragon.defs import JUNK_THEMES, classify_themes
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
        # 展示用强度；定主线不靠它，靠家数。
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
    ranked.sort(key=lambda x: (-x["count"], -x["amount_yi"], -x["max_boards"]))
    return ranked


def pick_mainline(ranked: list[dict[str, Any]]) -> dict[str, Any] | None:
    """涨停家数最多且≥2 的主题。并列先比成交，再比最高板。「其他」不算。"""
    clean = [x for x in ranked if x["theme"] not in JUNK_THEMES and x["count"] >= 2]
    if not clean:
        return None
    clean.sort(key=lambda x: (-x["count"], -x["amount_yi"], -x["max_boards"]))
    return clean[0]


def pick_secondary(ranked: list[dict[str, Any]], mainline: dict[str, Any] | None) -> dict[str, Any] | None:
    """家数接近主线，或高度明显在的第二条线。不是空气。"""
    if not mainline:
        return None
    others = [
        x
        for x in ranked
        if x["theme"] not in JUNK_THEMES and x["theme"] != mainline["theme"] and x["count"] >= 2
    ]
    cands = []
    for x in others:
        if x["count"] >= mainline["count"] - 1:
            cands.append(x)
        elif x["max_boards"] >= 4 and x["count"] >= mainline["count"] - 2:
            cands.append(x)
    if not cands:
        return None
    cands.sort(key=lambda x: (-x["count"], -x["max_boards"], -x["amount_yi"]))
    return cands[0]


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


def apply_lanes(
    scored: list[ScoredStock],
    ranked: list[dict[str, Any]],
    mainline: dict[str, Any] | None,
    secondary: dict[str, Any] | None,
) -> list[ScoredStock]:
    """只标通道，不把支线高标踢出对照池。"""
    lanes = classify_themes(ranked, mainline, secondary)
    main_name = mainline["theme"] if mainline else None
    for s in scored:
        s.lane = lanes.get(s.theme) or ("主线" if main_name and s.theme == main_name else "独立")
        s.in_mainline = s.lane == "主线"
        if s.lane == "独立" and s.boards < 4 and s.role not in {"见顶观察", "高度锚"}:
            s.pass_leader = False
        elif s.lane in {"支线", "次主线"} and s.boards >= 4 and s.tradable:
            s.pass_leader = True
            if s.role in {"主线龙", "先锋", "龙头候选"}:
                s.status = f"{s.lane}高标 · 对照，不进火车头池"
        elif s.lane in {"支线", "次主线"} and s.role in {"主线龙", "先锋", "龙头候选"}:
            s.pass_leader = False
            s.status = f"{s.lane}·{s.status}"
    return scored


def apply_mainline_lane(scored: list[ScoredStock], mainline: str | None) -> list[ScoredStock]:
    """兼容旧调用：只知道主线名时，按家数临时标通道。"""
    ranked = []
    groups: dict[str, list[ScoredStock]] = defaultdict(list)
    for s in scored:
        groups[s.theme].append(s)
    for theme, xs in groups.items():
        ranked.append(
            {
                "theme": theme,
                "count": len(xs),
                "amount_yi": round(sum(i.amount_yi for i in xs), 2),
                "max_boards": max(i.boards for i in xs),
            }
        )
    main = next((x for x in ranked if x["theme"] == mainline), None) if mainline else None
    secondary = pick_secondary(ranked, main)
    return apply_lanes(scored, ranked, main, secondary)


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
    """旧接口：主线里挑能买的先封。正式路径走 decide()。"""
    from dragon.decide import pick_locomotive

    for s in mainline_rows:
        if not s.lane:
            s.lane = "主线"
    return pick_locomotive(mainline_rows)


def build_steps(
    *,
    mode: str,
    mainline: dict[str, Any] | None,
    secondary: dict[str, Any] | None,
    ranked: list[dict[str, Any]],
    scored: list[ScoredStock],
    broken: list[dict[str, Any]],
    concepts: list[dict],
    indexes: list[dict],
    decision: Decision,
) -> tuple[list[dict[str, Any]], str]:
    theme = mainline["theme"] if mainline else None
    main_rows = [s for s in scored if s.lane == "主线"]
    watch = decision.watch
    loco = decision.locomotive
    sent = decision.sentiment
    height = decision.height

    side = [x for x in ranked if theme and x["theme"] != theme][:3]
    side_txt = "、".join(f"{x['theme']}{x['count']}只/{x['max_boards']}板" for x in side) or "无"
    sec_txt = ""
    if secondary:
        sec_txt = f"次主线={secondary['theme']}（{secondary['count']}只/{secondary['max_boards']}板）留下对照。"

    if mainline:
        s1_pass, s1 = True, (
            f"主线={theme}：涨停{mainline['count']}只 / 成交{mainline['amount_yi']}亿 / "
            f"最高{mainline['max_boards']}板。{sec_txt}其余{side_txt}不当火车头，高标可以当空间/情绪对照。"
        )
    else:
        s1_pass, s1 = False, "没有≥2只涨停的主题，今天没有主线，只看空间高标和情绪。"

    ordered = sorted(main_rows, key=lambda s: (s.first_seal_raw or 999999, s.open_count))
    if loco:
        skipped = [s for s in ordered if s.first_seal_raw and loco.first_seal_raw and s.first_seal_raw < loco.first_seal_raw]
        skip_txt = ""
        if skipped:
            why = "、".join(
                f"{s.name}({('一字' if s.yizi else '爆量' if s.climax else '烂板' if s.rotten else '跳过')})"
                for s in skipped[:3]
            )
            skip_txt = f"跳过{why}。"
        ladder = " → ".join(f"{s.name}{s.first_seal}(炸{s.open_count})" for s in ordered[:5])
        s2_pass = loco.open_count <= 2
        s2 = f"火车头 {loco.name} {loco.first_seal} 炸{loco.open_count}次。{skip_txt}主线封板序：{ladder}"
    elif ordered:
        head = ordered[0]
        s2_pass = False
        s2 = f"主线先封是{head.name}，但一字/爆量/烂板，没有能买的火车头。"
    else:
        s2_pass, s2 = False, "主线没有可排序的涨停。"

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

    # 人气是加分：能叫出来就过，没上榜不一票否决。
    if sent:
        if sent.pop_rank and sent.pop_rank <= 3:
            s5_pass, s5 = True, f"情绪龙{sent.name}人气第{sent.pop_rank}，叫得出来。"
        elif sent.pop_rank and sent.pop_rank <= 10:
            s5_pass, s5 = True, f"情绪龙{sent.name}人气第{sent.pop_rank}，有共识。"
        elif sent.boards >= 4:
            s5_pass, s5 = True, f"情绪龙{sent.name}没上人气前十，但{sent.boards}板本身就是辨识度。"
        else:
            s5_pass, s5 = True, f"人气榜不全，情绪龙按主线辨识度落到{sent.name}，不当硬门槛否决。"
    elif watch and watch.pop_rank and watch.pop_rank <= 10:
        s5_pass, s5 = True, f"{watch.name}人气第{watch.pop_rank}。"
    else:
        s5_pass, s5 = False, "没有叫得出来的情绪龙。人气只是加分，改看火车头和空间。"

    if not watch:
        s6_pass, s6 = False, "没有可留的票。"
    else:
        vol = watch.dimensions["volume"].verdict
        s6_pass = vol == "健康换手"
        extra = "留下。" if s6_pass else "能盯，仓位要轻。"
        if vol in {"一字无量", "爆量见顶"}:
            extra = "放弃。"
            s6_pass = False
        s6 = (
            f"{watch.name}换手{watch.turnover}% / 成交{watch.amount_yi}亿 / "
            f"量比{watch.volume_ratio if watch.volume_ratio is not None else '-'} → {vol}，{extra}"
        )

    from dragon.decide import watch_action

    action = watch_action(mode, watch, decision.watch_hat)
    titles = [
        ("先定板块再定票", s1_pass, s1),
        ("涨停时间排序", s2_pass, s2),
        ("板块指数红不红", s3_pass, s3),
        ("砸盘谁抗谁碎", s4_pass, s4),
        ("情绪能不能叫出来", s5_pass, s5),
        ("最后看量", s6_pass, s6),
    ]
    steps = []
    for i, (title, ok, detail) in enumerate(titles, 1):
        steps.append({"step": i, "title": title, "pass": ok, "detail": detail})
    return steps, action

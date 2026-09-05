from __future__ import annotations

from collections import defaultdict
from typing import Any

from dragon.decide import decide
from dragon.defs import DEFINITIONS
from dragon.market import concept_index, load_market
from dragon.pipeline import (
    apply_lanes,
    build_steps,
    pick_mainline,
    pick_secondary,
    rank_themes,
)
from dragon.score import ScoredStock, score_stock
from dragon.timeutil import market_session


def _skip(name: str) -> bool:
    return "ST" in (name or "").upper()


def resolve_mode(session: dict, override: str | None = None) -> str:
    if override in {"盘中", "intraday"}:
        return "盘中"
    if override in {"盘后", "review"}:
        return "盘后"
    return "盘中" if session.get("live") else "盘后"


def score_universe(zt_rows: list[dict[str, Any]], *, popularity: dict[str, int], concepts: list[dict]) -> list[ScoredStock]:
    by_theme: dict[str, list[dict]] = defaultdict(list)
    for row in zt_rows:
        if _skip(str(row.get("name") or "")):
            continue
        by_theme[str(row.get("theme") or "未知")].append(row)

    market_max = max((int(r.get("boards") or 0) for r in zt_rows), default=0)
    amount_order = sorted(zt_rows, key=lambda r: -float(r.get("amount") or 0))
    amount_rank = {str(r.get("code")): i for i, r in enumerate(amount_order, 1)}
    cmap = concept_index(concepts)

    scored: list[ScoredStock] = []
    for theme, peers in by_theme.items():
        for row in peers:
            code = str(row["code"])
            concept = cmap.get(code)
            sector_pct = concept.get("pct") if concept else None
            scored.append(
                score_stock(
                    row,
                    theme_peers=peers,
                    market_max_boards=market_max,
                    amount_rank_market=amount_rank.get(code, 99),
                    pop_rank=popularity.get(code),
                    concept=concept,
                    sector_pct=sector_pct,
                )
            )
    scored.sort(key=lambda s: (-s.pass_leader, -s.total, -s.boards, s.open_count, -s.amount_yi))
    return scored


def theme_table(scored: list[ScoredStock], mainline: str | None) -> list[dict[str, Any]]:
    groups: dict[str, list[ScoredStock]] = defaultdict(list)
    for s in scored:
        groups[s.theme].append(s)
    out = []
    for theme, xs in groups.items():
        xs = sorted(xs, key=lambda i: (i.first_seal_raw or 999999, i.open_count, -i.boards))
        head = xs[0]
        lane = xs[0].lane or ("主线" if theme == mainline else "支线")
        out.append(
            {
                "theme": theme,
                "lane": lane,
                "mainline": lane == "主线",
                "count": len(xs),
                "amount_yi": round(sum(i.amount_yi for i in xs), 2),
                "max_boards": max(i.boards for i in xs),
                "first": xs[0].name,
                "first_time": xs[0].first_seal,
                "head": head.name,
                "head_code": head.code,
                "head_role": head.role,
                "members": [
                    {
                        "code": i.code,
                        "name": i.name,
                        "boards": i.boards,
                        "first_seal": i.first_seal,
                        "turnover": i.turnover,
                        "amount_yi": i.amount_yi,
                        "open_count": i.open_count,
                        "pop_rank": i.pop_rank,
                        "volume": i.dimensions["volume"].verdict,
                    }
                    for i in xs
                ],
            }
        )
    order = {"主线": 0, "次主线": 1, "支线": 2, "独立": 3}
    out.sort(key=lambda g: (order.get(g["lane"], 9), -g["count"], -g["amount_yi"]))
    return out


def _pack(stock: ScoredStock | None) -> dict | None:
    return stock.to_dict() if stock else None


def analyze(
    zt_rows: list[dict[str, Any]],
    *,
    popularity: dict[str, int],
    concepts: list[dict],
    broken: list[dict] | None = None,
    indexes: list[dict] | None = None,
    mode: str = "盘后",
) -> dict[str, Any]:
    scored = score_universe(zt_rows, popularity=popularity, concepts=concepts)
    ranked = rank_themes(zt_rows)
    mainline = pick_mainline(ranked)
    secondary = pick_secondary(ranked, mainline)
    main_name = mainline["theme"] if mainline else None
    apply_lanes(scored, ranked, mainline, secondary)
    decision = decide(scored, mainline_name=main_name, mode=mode)
    scored.sort(
        key=lambda s: (
            0 if s.hats else 1,
            0 if s.lane == "主线" else 1,
            s.first_seal_raw or 999999,
            s.open_count,
        )
    )
    steps, action = build_steps(
        mode=mode,
        mainline=mainline,
        secondary=secondary,
        ranked=ranked,
        scored=scored,
        broken=broken or [],
        concepts=concepts,
        indexes=indexes or [],
        decision=decision,
    )
    return {
        "scored": scored,
        "ranked": ranked,
        "mainline": mainline,
        "secondary": secondary,
        "decision": decision,
        "watch": decision.watch,
        "steps": steps,
        "action": action,
        "themes": theme_table(scored, main_name),
    }


async def build_snapshot(date: str | None = None, mode: str | None = None) -> dict[str, Any]:
    session = market_session()
    use_mode = resolve_mode(session, mode)
    market = await load_market(date)
    result = analyze(
        market["zt"],
        popularity=market.get("popularity") or {},
        concepts=market.get("concepts") or [],
        broken=market.get("broken") or [],
        indexes=market.get("indexes") or [],
        mode=use_mode,
    )
    scored = result["scored"]
    decision = result["decision"]
    watch = result["watch"]
    leaders = [s for s in scored if s.hats or (s.pass_leader and s.lane == "主线")]
    return {
        "ok": True,
        "date": market["date"],
        "session": session,
        "mode": use_mode,
        "source": market["source"],
        "warnings": market["warnings"],
        "indexes": market.get("indexes") or [],
        "stats": {
            "zt": len(market["zt"]),
            "broken": len(market["broken"]),
            "scored": len(scored),
            "leaders": len(leaders),
        },
        "mainline": result["mainline"],
        "secondary": result["secondary"],
        "theme_rank": result["ranked"],
        "steps": result["steps"],
        "watch": _pack(watch),
        "action": result["action"],
        "reason": decision.reason,
        "notes": decision.notes,
        "watch_hat": decision.watch_hat,
        "picks": {
            "watch": _pack(watch),
            "locomotive": _pack(decision.locomotive),
            "sentiment": _pack(decision.sentiment),
            "height": _pack(decision.height),
            "mainline": _pack(decision.locomotive),
            "volume": _pack(
                max(
                    (s for s in scored if s.lane == "主线" and s.tradable),
                    key=lambda s: s.amount_yi,
                    default=None,
                )
            ),
        },
        "leaders": [s.to_dict() for s in leaders],
        "board": [s.to_dict() for s in scored],
        "themes": result["themes"],
        "definitions": DEFINITIONS,
        "method": {
            "title": "10秒定龙头",
            "order": [
                "先定板块再定票",
                "涨停时间排序",
                "板块指数红不红",
                "砸盘谁抗谁碎",
                "情绪能不能叫出来",
                "最后看量",
            ],
            "rule": "先定板块。火车头、情绪龙头、空间高标三路对照，最后盯一只。",
        },
    }

"""先 · 比 · 独 选股引擎。"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

CN = timezone(timedelta(hours=8))


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "" or v == "-":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _fmt_seal(v: Any) -> str:
    try:
        n = int(v)
    except (TypeError, ValueError):
        return "-"
    if n <= 0:
        return "-"
    if n >= 100000:
        s = f"{n:06d}"
        return f"{s[:2]}:{s[2:4]}:{s[4:]}"
    if n >= 1000:
        s = f"{n:04d}"
        return f"{s[:2]}:{s[2:]}"
    return str(v)


def recent_trade_dates(n: int = 40) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    day = datetime.now(CN).date()
    while len(out) < n:
        if day.weekday() < 5:
            ymd = day.strftime("%Y%m%d")
            label = day.strftime("%Y-%m-%d")
            week = "一二三四五六日"[day.weekday()]
            out.append({"date": ymd, "label": f"{label} 周{week}"})
        day -= timedelta(days=1)
    return out


def score_candidates(bundle: dict[str, Any]) -> dict[str, Any]:
    limit_up = list(bundle.get("limit_up") or [])
    broken = list(bundle.get("broken") or [])
    boards = list(bundle.get("boards") or [])

    hot_boards = [b for b in boards if _f(b.get("change_pct")) >= 1.2][:12]
    hot_names = {str(b.get("name") or "") for b in hot_boards}

    industry_zt: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in limit_up:
        ind = (row.get("industry") or "未知").strip() or "未知"
        industry_zt[ind].append(row)

    broken_codes = {x.get("code") for x in broken}
    scored: list[dict[str, Any]] = []

    for row in limit_up:
        code = row.get("code") or ""
        if not code:
            continue
        industry = (row.get("industry") or "").strip()
        peers = industry_zt.get(industry) or [row]
        peer_pcts = sorted((_f(p.get("change_pct")) for p in peers), reverse=True)
        my_pct = _f(row.get("change_pct"))
        boards_n = int(_f(row.get("boards") or 1))
        open_count = int(_f(row.get("open_count")))
        turnover = _f(row.get("turnover"))
        seal = _f(row.get("seal_amount"))
        is_yizi = bool(row.get("is_yizi"))
        first_seal = row.get("first_seal")

        in_hot = any(
            (industry and industry in bn) or (bn and bn in industry) for bn in hot_names if bn
        )
        peer_count = len(peers)

        xian = 0.0
        xian_notes: list[str] = []
        if in_hot or peer_count >= 2:
            xian += 28
            xian_notes.append("赛道共识启动")
        if peer_count >= 3:
            xian += 10
            xian_notes.append(f"同题材涨停{peer_count}")
        if boards_n >= 2:
            xian += min(boards_n * 6, 24)
            xian_notes.append(f"{boards_n}板高度")
        if not is_yizi:
            xian += 8
            xian_notes.append("非一字可交易")
        else:
            xian -= 12
            xian_notes.append("一字仅作高度锚")

        bi = 0.0
        bi_notes: list[str] = []
        if peer_pcts:
            rank = peer_pcts.index(my_pct) + 1 if my_pct in peer_pcts else len(peer_pcts)
            rel = 1.0 - (rank - 1) / max(len(peer_pcts), 1)
            bi += rel * 22
            bi_notes.append("题材内涨幅最强" if rank == 1 else f"题材内第{rank}/{len(peer_pcts)}")
        if open_count == 0:
            bi += 16
            bi_notes.append("零开板")
        elif open_count == 1:
            bi += 8
            bi_notes.append("轻分歧")
        else:
            bi -= min(open_count * 4, 16)
            bi_notes.append(f"开板{open_count}次")
        if seal >= 2e8:
            bi += 12
            bi_notes.append("封单厚")
        elif seal >= 5e7:
            bi += 6
        elif 0 < seal < 2e7:
            bi -= 4
            bi_notes.append("封单偏薄")
        if 3 <= turnover <= 25:
            bi += 8
            bi_notes.append("换手适中")
        elif turnover > 35:
            bi -= 6
            bi_notes.append("换手过高")

        du = 0.0
        du_notes: list[str] = []
        max_boards = max(int(_f(p.get("boards") or 1)) for p in peers)
        if boards_n >= max_boards and boards_n >= 2:
            du += 22
            du_notes.append("高度定义板块")
        same_broken = sum(1 for b in broken if (b.get("industry") or "") == industry)
        if same_broken and code not in broken_codes and open_count <= 1:
            du += 18
            du_notes.append("题材分歧下仍强封")
        try:
            fbt = int(first_seal or 0)
        except (TypeError, ValueError):
            fbt = 0
        if not is_yizi and 92500 < fbt <= 100000:
            du += 14
            du_notes.append("早盘引领封板")
        elif not is_yizi and fbt > 130000:
            du -= 6
            du_notes.append("午后被动跟随")
        if peer_count == 1 and boards_n >= 2:
            du += 8
            du_notes.append("高位独立")

        total = round(xian * 0.34 + bi * 0.33 + du * 0.33, 2)
        if total >= 38 and not is_yizi:
            role = "核心领涨"
        elif is_yizi:
            role = "高度锚"
        elif total >= 30:
            role = "观察"
        else:
            role = "弱"

        scored.append(
            {
                **row,
                "first_seal_text": _fmt_seal(first_seal),
                "score": total,
                "score_xian": round(xian, 2),
                "score_bi": round(bi, 2),
                "score_du": round(du, 2),
                "role": role,
                "notes": xian_notes + bi_notes + du_notes,
                "peer_count": peer_count,
                "in_hot_board": bool(in_hot),
            }
        )

    scored.sort(key=lambda x: (0 if x["role"] == "核心领涨" else 1, -x["score"], -_f(x.get("boards"))))
    leaders = [x for x in scored if x["role"] == "核心领涨"][:8]
    anchors = [x for x in scored if x.get("is_yizi")][:8]
    watch = [x for x in scored if x["role"] == "观察"][:12]

    return {
        "hot_boards": hot_boards,
        "leaders": leaders,
        "anchors": anchors,
        "watch": watch,
        "all": scored,
        "stats": {
            "limit_up": len(limit_up),
            "broken": len(broken),
            "leader_count": len(leaders),
            "hot_board_count": len(hot_boards),
        },
        "theory": {
            "xian": "先：大盘/赛道放量启动时，锁定资金共识标的",
            "bi": "比：同赛道比结构、量价、封板质量",
            "du": "独：分歧抗跌、启动领涨、定义板块节奏的核心领涨",
        },
    }
"""非一字晋级 · 龙头确认引擎。

回测纠偏后的口径：
1. 一字只作高度锚，不进确认榜
2. 确认榜只从「今日成功晋级封板」的非一字里选
3. 高度优先（真龙头），封板质量次之，竞价再次之
4. 复盘日不用实时行情竞价（会被今天价格污染），改用首封时间估竞价强度
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


def _num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _is_yizi(fbt: Any, zbc: Any, hs: float | None = None) -> bool:
    """一字板：9:25 封死且未开板；换手极低作辅助。"""
    try:
        fbt_i = int(fbt) if fbt is not None else -1
    except (TypeError, ValueError):
        fbt_i = -1
    try:
        zbc_i = int(zbc) if zbc is not None else 0
    except (TypeError, ValueError):
        zbc_i = 0
    if fbt_i == 92500 and zbc_i == 0:
        if hs is None or hs < 3.0:
            return True
    return False


def _fmt_time(fbt: Any) -> str:
    try:
        n = int(fbt)
    except (TypeError, ValueError):
        return "-"
    if n <= 0:
        return "-"
    s = f"{n:06d}"
    return f"{s[0:2]}:{s[2:4]}:{s[4:6]}"


def estimate_open_pct_from_fbt(fbt: Any) -> float | None:
    """无可靠竞价数据时，用首封时间粗估竞价强弱。"""
    try:
        n = int(fbt)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    if n <= 92500:
        return 9.8
    if n <= 93030:
        return 8.0
    if n <= 93300:
        return 6.0
    if n <= 94000:
        return 4.0
    if n <= 100000:
        return 2.0
    if n <= 103000:
        return 1.0
    return 0.0


def resolve_board_path(
    *,
    sealed: bool,
    yesterday_ct: int,
    today_lbc: int,
) -> tuple[int, int]:
    """修正晋级路径。

    东财「昨日涨停」池在成功晋级时，zttj.ct 常被刷新成今日高度，
    会导致错误的 2→2 / 6→6。成功封板时用 today_lbc-1 反推昨高度。
    """
    if sealed and today_lbc >= 1:
        prev = max(0, today_lbc - 1)
        return prev, today_lbc
    prev = max(0, yesterday_ct)
    return prev, prev + 1


@dataclass
class Candidate:
    code: str
    name: str
    industry: str
    prev_boards: int
    prev_days: int
    target_boards: int
    open_pct: float | None
    price: float | None
    change_pct: float | None
    turnover: float | None
    sealed: bool
    is_yizi: bool
    first_seal: str
    open_count: int
    seal_fund_yi: float
    amount_yi: float
    main_net_yi: float | None
    score: float
    score_detail: dict[str, float]
    rank_note: str
    status: str
    role: str


def score_for_leader_confirm(
    *,
    open_pct: float | None,
    sealed: bool,
    is_yizi: bool,
    open_count: int,
    seal_fund_yi: float,
    turnover: float | None,
    prev_boards: int,
    change_pct: float | None,
    today_boards: int | None = None,
) -> tuple[float, dict[str, float], str]:
    """高度优先的龙头确认打分。"""
    detail: dict[str, float] = {}
    notes: list[str] = []

    if is_yizi:
        return -100.0, {"yizi": -100.0}, "一字锁仓 · 只看高度结构，不可交易确认"

    boards = today_boards if (sealed and today_boards) else (prev_boards + (1 if sealed else 0))

    # 1) 高度：真龙头核心
    if sealed:
        height = boards * 18.0
        if boards >= 6:
            height += 30.0
            notes.append(f"高度龙{boards}板确认")
        elif boards >= 5:
            height += 22.0
            notes.append(f"高位龙头{boards}板确认")
        elif boards >= 4:
            height += 14.0
            notes.append(f"中高位{boards}板确认")
        elif boards >= 3:
            height += 8.0
            notes.append(f"中位{boards}板确认")
        else:
            height += 0.0
            notes.append(f"低位{boards}板（弱于高度龙）")
    else:
        # 晋级失败：高度尝试仅作对照，大幅降权
        height = prev_boards * 3.0 - 40.0
        notes.append(f"晋级失败对照（昨{prev_boards}板）")
    detail["height"] = height

    # 2) 封板质量
    seal = 0.0
    if sealed:
        seal += 30.0
        if open_count == 0:
            seal += 16.0
            notes.append("零炸板")
        elif open_count == 1:
            seal += 8.0
            notes.append("轻分歧")
        elif open_count <= 3:
            seal += 2.0
            notes.append(f"炸{open_count}次")
        else:
            seal -= 18.0
            notes.append(f"重分歧炸{open_count}")
        if seal_fund_yi >= 3.0:
            seal += 10.0
            notes.append("封单厚")
        elif seal_fund_yi >= 1.5:
            seal += 6.0
        elif seal_fund_yi >= 0.8:
            seal += 3.0
        elif seal_fund_yi < 0.4:
            seal -= 8.0
            notes.append("封单薄")
    else:
        chg = change_pct or 0.0
        if chg >= 7.0:
            seal -= 5.0
            notes.append("冲板未确认")
        else:
            seal -= 15.0
    detail["seal"] = seal

    # 3) 竞价（辅助，不可压过高度）
    auction = 0.0
    if open_pct is None:
        notes.append("缺竞价")
    elif open_pct >= 9.5:
        auction = 12.0
        notes.append("竞价近顶")
    elif open_pct >= 6.0:
        auction = 16.0
        notes.append("竞价强")
    elif open_pct >= 4.0:
        auction = 12.0
        notes.append("竞价偏强")
    elif open_pct >= 2.0:
        auction = 6.0
        notes.append("竞价一般")
    elif open_pct >= 0:
        auction = 2.0
        notes.append("竞价弱")
    else:
        auction = -8.0
        notes.append("竞价低开")
    detail["auction"] = auction

    # 4) 换手
    turn = 0.0
    hs = turnover or 0.0
    if sealed:
        if 3.0 <= hs <= 20.0:
            turn = 8.0
            notes.append("换手健康")
        elif 20.0 < hs <= 30.0:
            turn = 2.0
            notes.append("换手偏大")
        elif hs > 30.0:
            turn = -6.0
            notes.append("换手过大")
        elif 0 < hs < 3.0 and not is_yizi:
            turn = 1.0
    detail["turnover"] = turn

    total = round(height + seal + auction + turn, 2)
    detail["total"] = total
    return total, detail, " · ".join(notes)


def build_candidates(
    yesterday_pool: list[dict[str, Any]],
    today_zt: list[dict[str, Any]],
    quotes: dict[str, dict[str, Any]],
    *,
    min_prev_boards: int = 1,
    historical: bool = False,
) -> list[Candidate]:
    zt_map = {str(x.get("c")): x for x in today_zt}
    out: list[Candidate] = []

    for y in yesterday_pool:
        code = str(y.get("c") or "")
        if not code:
            continue
        zttj = y.get("zttj") or {}
        raw_ct = int(zttj.get("ct") or 0)
        prev_days = int(zttj.get("days") or 0)
        name = str(y.get("n") or "")
        if "ST" in name.upper():
            continue

        zt = zt_map.get(code)
        sealed = zt is not None
        fbt = zt.get("fbt") if zt else None
        zbc = int(zt.get("zbc") or 0) if zt else 0
        today_lbc = int(zt.get("lbc") or 0) if zt else 0

        prev_boards, target_boards = resolve_board_path(
            sealed=sealed,
            yesterday_ct=raw_ct,
            today_lbc=today_lbc or max(raw_ct, 1),
        )
        # 过滤：至少尝试晋级到 2 板（昨已有1板+）
        if sealed and target_boards < 2:
            continue
        if (not sealed) and raw_ct < min_prev_boards:
            continue

        quote = quotes.get(code) or {}
        pre = _num(quote.get("f18"))
        opn = _num(quote.get("f17"))
        px = _num(quote.get("f2"))
        chg = quote.get("f3")
        change_pct = _num(chg) if chg is not None else None
        turnover = (
            _num(zt.get("hs")) if zt and zt.get("hs") is not None
            else (_num(quote.get("f8")) if quote.get("f8") is not None else _num(y.get("hs")))
        )

        if historical:
            # 复盘禁用实时竞价，避免串日
            open_pct = estimate_open_pct_from_fbt(fbt) if sealed else None
        else:
            open_pct = ((opn / pre) - 1.0) * 100.0 if pre > 0 and opn > 0 else None
            if open_pct is None and sealed:
                open_pct = estimate_open_pct_from_fbt(fbt)

        main_net = quote.get("f62")
        main_net_yi = _num(main_net) / 1e8 if main_net is not None else None

        hs_for_yizi = _num(zt.get("hs") if zt else turnover)
        is_yizi = bool(zt and _is_yizi(fbt, zbc, hs_for_yizi))
        seal_fund_yi = _num(zt.get("fund") if zt else 0) / 1e8
        amount_yi = _num(zt.get("amount") if zt else y.get("amount")) / 1e8

        if change_pct is None and y.get("zdp") is not None:
            change_pct = _num(y.get("zdp"))
        if px <= 0 and y.get("p") is not None:
            px = _num(y.get("p")) / 1000.0
        if px <= 0 and zt and zt.get("p") is not None:
            px = _num(zt.get("p")) / 1000.0

        score, detail, note = score_for_leader_confirm(
            open_pct=open_pct,
            sealed=sealed,
            is_yizi=is_yizi,
            open_count=zbc,
            seal_fund_yi=seal_fund_yi,
            turnover=turnover,
            prev_boards=prev_boards,
            change_pct=change_pct,
            today_boards=target_boards if sealed else None,
        )

        if is_yizi:
            status = "一字高度锚"
            role = "高度锚"
        elif sealed:
            status = f"非一字{target_boards}板确认"
            role = "真龙头候选"
        elif (change_pct or 0) >= 7:
            status = "冲板待确认"
            role = "观察"
        else:
            status = "晋级失败对照"
            role = "掉队对照"

        out.append(
            Candidate(
                code=code,
                name=name,
                industry=str(y.get("hybk") or (zt or {}).get("hybk") or ""),
                prev_boards=prev_boards,
                prev_days=prev_days,
                target_boards=target_boards,
                open_pct=round(open_pct, 2) if open_pct is not None else None,
                price=round(px, 2) if px else None,
                change_pct=round(change_pct, 2) if change_pct is not None else None,
                turnover=round(turnover, 2) if turnover is not None else None,
                sealed=sealed,
                is_yizi=is_yizi,
                first_seal=_fmt_time(fbt),
                open_count=zbc,
                seal_fund_yi=round(seal_fund_yi, 2),
                amount_yi=round(amount_yi, 2),
                main_net_yi=round(main_net_yi, 2) if main_net_yi is not None else None,
                score=score,
                score_detail=detail,
                rank_note=note,
                status=status,
                role=role,
            )
        )

    # 也把「今日涨停但昨日池缺失」的高位非一字补进来（高度龙兜底）
    seen = {c.code for c in out}
    for x in today_zt:
        code = str(x.get("c") or "")
        if not code or code in seen:
            continue
        name = str(x.get("n") or "")
        if "ST" in name.upper():
            continue
        lbc = int(x.get("lbc") or 1)
        if lbc < 3:
            continue
        fbt = x.get("fbt")
        zbc = int(x.get("zbc") or 0)
        hs = _num(x.get("hs"))
        is_yizi = _is_yizi(fbt, zbc, hs)
        if is_yizi:
            continue
        prev = lbc - 1
        open_pct = None if historical else None
        open_pct = estimate_open_pct_from_fbt(fbt)
        seal_fund_yi = _num(x.get("fund")) / 1e8
        score, detail, note = score_for_leader_confirm(
            open_pct=open_pct,
            sealed=True,
            is_yizi=False,
            open_count=zbc,
            seal_fund_yi=seal_fund_yi,
            turnover=hs,
            prev_boards=prev,
            change_pct=_num(x.get("zdp")),
            today_boards=lbc,
        )
        out.append(
            Candidate(
                code=code,
                name=name,
                industry=str(x.get("hybk") or ""),
                prev_boards=prev,
                prev_days=int((x.get("zttj") or {}).get("days") or lbc),
                target_boards=lbc,
                open_pct=round(open_pct, 2) if open_pct is not None else None,
                price=round(_num(x.get("p")) / 1000.0, 2),
                change_pct=round(_num(x.get("zdp")), 2),
                turnover=round(hs, 2),
                sealed=True,
                is_yizi=False,
                first_seal=_fmt_time(fbt),
                open_count=zbc,
                seal_fund_yi=round(seal_fund_yi, 2),
                amount_yi=round(_num(x.get("amount")) / 1e8, 2),
                main_net_yi=None,
                score=score,
                score_detail=detail,
                rank_note=note + " · 高度池补录",
                status=f"非一字{lbc}板确认",
                role="真龙头候选",
            )
        )

    out.sort(
        key=lambda c: (
            0 if (c.sealed and not c.is_yizi) else 1,
            -c.score,
            -c.target_boards,
            c.open_count,
        )
    )
    return out


def pick_confirmed_leaders(candidates: list[Candidate], n: int = 2) -> list[Candidate]:
    """主输出：已成功晋级的非一字真龙头（高度优先）。"""
    sealed = [c for c in candidates if c.sealed and not c.is_yizi]
    if not sealed:
        weak = [c for c in candidates if not c.is_yizi and (c.change_pct or 0) >= 7]
        return weak[:n]

    high = [c for c in sealed if c.target_boards >= 3]
    pool = high if high else sealed
    picked = pool[:n]
    if len(picked) < n:
        for c in sealed:
            if c in picked:
                continue
            picked.append(c)
            if len(picked) >= n:
                break
    return picked


def build_ladder(today_zt: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for x in today_zt:
        name = str(x.get("n") or "")
        if "ST" in name.upper():
            continue
        fbt = x.get("fbt")
        zbc = int(x.get("zbc") or 0)
        hs = _num(x.get("hs"))
        is_yizi = _is_yizi(fbt, zbc, hs)
        zttj = x.get("zttj") or {}
        rows.append(
            {
                "code": x.get("c"),
                "name": name,
                "boards": int(x.get("lbc") or 1),
                "days": zttj.get("days"),
                "ct": zttj.get("ct"),
                "price": round(_num(x.get("p")) / 1000.0, 2),
                "change_pct": round(_num(x.get("zdp")), 2),
                "first_seal": _fmt_time(fbt),
                "open_count": zbc,
                "seal_fund_yi": round(_num(x.get("fund")) / 1e8, 2),
                "amount_yi": round(_num(x.get("amount")) / 1e8, 2),
                "turnover": round(hs, 2),
                "industry": x.get("hybk") or "",
                "is_yizi": is_yizi,
                "board_type": "一字(不可买)" if is_yizi else "非一字",
            }
        )
    rows.sort(key=lambda r: (-r["boards"], r["open_count"], -r["seal_fund_yi"]))
    return rows


def confirm_summary(
    candidates: list[Candidate],
    ladder: list[dict[str, Any]],
    picks: list[Candidate],
) -> dict[str, Any]:
    height = ladder[0] if ladder else None
    real_height = next((r for r in ladder if not r["is_yizi"]), None)
    yizi_height = next((r for r in ladder if r["is_yizi"]), None)

    failed = [c for c in candidates if (not c.sealed) and c.prev_boards >= 3][:5]

    verdict = "待竞价/开盘确认"
    if picks:
        top = picks[0]
        if top.sealed and top.target_boards >= 5 and top.open_count <= 2:
            verdict = f"真龙头确认：{top.name}（{top.prev_boards}→{top.target_boards}板）"
        elif top.sealed and top.target_boards >= 3:
            verdict = f"龙头确认：{top.name}（{top.prev_boards}→{top.target_boards}板，非一字）"
        elif top.sealed:
            verdict = f"低位晋级观察：{top.name}（{top.prev_boards}→{top.target_boards}板；当日无更高非一字）"
        else:
            verdict = f"尚未确认，关注：{top.name}"

    return {
        "verdict": verdict,
        "height_anchor": height,
        "yizi_height_note": (
            f"{yizi_height['name']} 为一字高度锚，买不进，只作结构参考"
            if yizi_height
            else "今日暂无一字高度锚"
        ),
        "tradable_height": real_height,
        "confirmed_picks": [c.name for c in picks],
        "failed_high": [
            {"name": c.name, "code": c.code, "prev_boards": c.prev_boards, "change_pct": c.change_pct}
            for c in failed
        ],
    }


def candidates_to_dict(items: list[Candidate]) -> list[dict[str, Any]]:
    return [asdict(c) for c in items]

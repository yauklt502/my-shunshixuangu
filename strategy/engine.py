"""非一字晋级 · 龙头确认引擎。

目标不是「找一字高度」，而是确认：
1. 市场高度锚（含一字，只看结构）
2. 可交易真龙头（非一字，竞价+封板质量）
3. 今日最可能晋级的两只非一字（龙头确认主输出）
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
    role: str  # 高度锚 / 真龙头候选 / 掉队对照


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
) -> tuple[float, dict[str, float], str]:
    """龙头确认打分：一字只记结构，不进可交易确认榜。"""
    detail: dict[str, float] = {}
    notes: list[str] = []

    if is_yizi:
        # 一字：买不进，仅作高度参考，不参与真龙头排序
        return -100.0, {"yizi": -100.0}, "一字锁仓 · 只看高度结构，不可交易确认"

    auction = 0.0
    if open_pct is None:
        notes.append("缺竞价")
    elif open_pct >= 9.5:
        auction = 28.0
        notes.append("竞价近顶")
    elif open_pct >= 6.0:
        auction = 40.0
        notes.append("竞价强 · 龙头确认信号")
    elif open_pct >= 4.0:
        auction = 34.0
        notes.append("竞价偏强")
    elif open_pct >= 2.0:
        auction = 18.0
        notes.append("竞价一般")
    elif open_pct >= 0:
        auction = 6.0
        notes.append("竞价弱 · 高度难确认")
    else:
        auction = -15.0
        notes.append("竞价低开 · 掉队风险")
    detail["auction"] = auction

    seal = 0.0
    if sealed:
        seal += 25.0
        if open_count == 0:
            seal += 18.0
            notes.append("零炸板 · 承接确认")
        elif open_count == 1:
            seal += 8.0
            notes.append("轻分歧仍封")
        elif open_count <= 3:
            seal += 2.0
            notes.append(f"炸{open_count}次")
        else:
            seal -= 12.0
            notes.append(f"重分歧炸{open_count} · 龙头不稳")
        if seal_fund_yi >= 4.0:
            seal += 12.0
            notes.append("封单厚")
        elif seal_fund_yi >= 2.0:
            seal += 8.0
        elif seal_fund_yi >= 1.0:
            seal += 4.0
        elif seal_fund_yi < 0.5:
            seal -= 8.0
            notes.append("封单薄")
    else:
        chg = change_pct or 0.0
        if chg >= 7.0:
            seal += 8.0
            notes.append("冲板中 · 待确认")
        elif chg >= 3.0:
            seal += 2.0
            notes.append("跟涨偏弱")
        else:
            seal -= 20.0
            notes.append("未晋级 · 对照样本")
    detail["seal"] = seal

    turn = 0.0
    hs = turnover or 0.0
    if sealed:
        if 3.0 <= hs <= 18.0:
            turn = 10.0
            notes.append("真实换手")
        elif 18.0 < hs <= 28.0:
            turn = 4.0
            notes.append("换手偏大")
        elif hs > 28.0:
            turn = -6.0
            notes.append("换手过大")
        elif 0 < hs < 3.0:
            turn = 2.0
    detail["turnover"] = turn

    height = 0.0
    if prev_boards >= 6:
        height = 6.0 if (open_pct or 0) >= 4.0 else -2.0
        notes.append("高度龙观察")
    elif prev_boards >= 4:
        height = 10.0
        notes.append("中高位真龙头候选")
    elif prev_boards == 3:
        height = 12.0
        notes.append("中位确认核心")
    elif prev_boards == 2:
        height = 10.0
        notes.append("低位晋级确认")
    else:
        height = 2.0
    detail["height"] = height

    total = round(auction + seal + turn + height, 2)
    detail["total"] = total
    return total, detail, " · ".join(notes)


def build_candidates(
    yesterday_pool: list[dict[str, Any]],
    today_zt: list[dict[str, Any]],
    quotes: dict[str, dict[str, Any]],
    *,
    min_prev_boards: int = 2,
) -> list[Candidate]:
    zt_map = {str(x.get("c")): x for x in today_zt}
    out: list[Candidate] = []

    for y in yesterday_pool:
        code = str(y.get("c") or "")
        if not code:
            continue
        zttj = y.get("zttj") or {}
        prev_ct = int(zttj.get("ct") or 0)
        prev_days = int(zttj.get("days") or 0)
        if prev_ct < min_prev_boards:
            continue

        name = str(y.get("n") or "")
        if "ST" in name.upper():
            continue

        quote = quotes.get(code) or {}
        pre = _num(quote.get("f18"))
        opn = _num(quote.get("f17"))
        px = _num(quote.get("f2"))
        chg = quote.get("f3")
        change_pct = _num(chg) if chg is not None else None
        turnover = (
            _num(quote.get("f8")) if quote.get("f8") is not None else _num(y.get("hs"))
        )
        open_pct = ((opn / pre) - 1.0) * 100.0 if pre > 0 and opn > 0 else None
        main_net = quote.get("f62")
        main_net_yi = _num(main_net) / 1e8 if main_net is not None else None

        zt = zt_map.get(code)
        sealed = zt is not None
        fbt = zt.get("fbt") if zt else None
        zbc = int(zt.get("zbc") or 0) if zt else 0
        hs_for_yizi = _num(zt.get("hs") if zt else turnover)
        is_yizi = bool(zt and _is_yizi(fbt, zbc, hs_for_yizi))
        seal_fund_yi = _num(zt.get("fund") if zt else 0) / 1e8
        amount_yi = _num(zt.get("amount") if zt else y.get("amount")) / 1e8
        today_lbc = int(zt.get("lbc") or prev_ct + 1) if zt else prev_ct

        if change_pct is None and y.get("zdp") is not None:
            change_pct = _num(y.get("zdp"))
        if px <= 0 and y.get("p") is not None:
            px = _num(y.get("p")) / 1000.0

        score, detail, note = score_for_leader_confirm(
            open_pct=open_pct,
            sealed=sealed,
            is_yizi=is_yizi,
            open_count=zbc,
            seal_fund_yi=seal_fund_yi,
            turnover=turnover,
            prev_boards=prev_ct,
            change_pct=change_pct,
        )

        if is_yizi:
            status = "一字高度锚"
            role = "高度锚"
        elif sealed:
            status = "非一字晋级确认"
            role = "真龙头候选"
        elif (change_pct or 0) >= 7:
            status = "冲板待确认"
            role = "真龙头候选"
        else:
            status = "掉队对照"
            role = "掉队对照"

        out.append(
            Candidate(
                code=code,
                name=name,
                industry=str(y.get("hybk") or (zt or {}).get("hybk") or ""),
                prev_boards=prev_ct,
                prev_days=prev_days,
                target_boards=prev_ct + 1 if not sealed else today_lbc,
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

    out.sort(key=lambda c: c.score, reverse=True)
    return out


def pick_confirmed_leaders(candidates: list[Candidate], n: int = 2) -> list[Candidate]:
    """主输出：今日最可能完成龙头确认的两只非一字。"""
    picked: list[Candidate] = []
    for c in candidates:
        if c.is_yizi:
            continue
        if c.sealed or (c.change_pct or 0) >= 5.0 or (c.open_pct or 0) >= 3.0:
            picked.append(c)
        if len(picked) >= n:
            break
    if len(picked) < n:
        for c in candidates:
            if c.is_yizi or c in picked:
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
    rows.sort(key=lambda r: (-r["boards"], -r["seal_fund_yi"]))
    return rows


def confirm_summary(
    candidates: list[Candidate],
    ladder: list[dict[str, Any]],
    picks: list[Candidate],
) -> dict[str, Any]:
    """龙头确认结论摘要。"""
    height = ladder[0] if ladder else None
    real_height = next((r for r in ladder if not r["is_yizi"]), None)
    yizi_height = next((r for r in ladder if r["is_yizi"]), None)

    verdict = "待竞价/开盘确认"
    if picks:
        top = picks[0]
        if top.sealed and top.open_count == 0 and (top.open_pct or 0) >= 4:
            verdict = f"真龙头倾向确认：{top.name}（竞价强 + 零炸板）"
        elif top.sealed:
            verdict = f"真龙头观察：{top.name}（已晋级，看封板质量）"
        else:
            verdict = f"尚未确认，关注竞价最强：{top.name}"

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
    }


def candidates_to_dict(items: list[Candidate]) -> list[dict[str, Any]]:
    return [asdict(c) for c in items]

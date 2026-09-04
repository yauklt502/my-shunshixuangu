"""清醒龙头战法 —— 选股引擎。

对应视频《龙头战法到底最重要的是什么》框架：
1. 高度聚焦：谁满足观察条件再研究谁
2. 不替市场提前下结论：没走出强度的不硬做
3. 看核心表现：强弱可能已切换 / 结构失效
4. 区分主线与支线：优先全局带动性核心
5. 不被漂亮图形骗：看懂弱势信号
6. 接受回撤：把风险写进评分
7. 交易的清醒：管理注意力 —— 输出「聚焦 / 观察 / 回避」
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.models import Board, Candidate, LimitBreakInfo, LimitUpInfo, MarketSnapshot, Stock


NOISE_BOARD_KEYWORDS = (
    "昨日", "前日", "连板", "涨停", "跌停", "破板", "炸板", "打板",
    "首板", "二板", "三板", "历史新高", "历史新低", "近期新高", "近期新低",
    "近期解禁", "公告", "ST", "次新股", "沪股通", "深股通",
    "融资融券", "转融通", "高开低走", "低开高走", "高换手", "成交活跃",
    "含一字", "题材股", "热股", "多板", "东方财富",
)


@dataclass
class StrategyParams:
    top_boards: int = 12
    leaders_per_board: int = 3
    min_board_members: int = 4
    min_change_pct: float = 3.0
    focus_score: float = 72.0
    watch_score: float = 55.0


def is_noise_board(name: str) -> bool:
    return any(k in name for k in NOISE_BOARD_KEYWORDS)


def is_st(name: str) -> bool:
    n = name.replace(" ", "").upper()
    return "ST" in n


def format_fbt(value: int | None) -> str | None:
    if not value:
        return None
    s = str(int(value)).zfill(6)
    return f"{s[:2]}:{s[2:4]}:{s[4:6]}"


def board_strength(board: Board) -> float:
    """板块强度：涨幅 + 资金 + 上涨家数占比。"""
    score = 0.0
    pct = board.change_percent or 0.0
    score += max(min(pct * 8.0, 40.0), -20.0)
    inflow = board.main_net_inflow or 0.0
    if inflow > 0:
        score += min(inflow / 1e8 * 6.0, 18.0)
    elif inflow < 0:
        score += max(inflow / 1e8 * 4.0, -12.0)
    members = board.member_count
    if members > 0:
        up_ratio = (board.up_count or 0) / members
        score += up_ratio * 20.0
    amount = board.amount or 0.0
    score += min(amount / 1e9 * 5.0, 12.0)
    if board.kind == "concept":
        score += 2.0  # 题材主线略加权（可带动性）
    return score


def stock_relative_strength(stock: Stock, board: Board) -> float:
    sp = stock.change_percent or 0.0
    bp = board.change_percent or 0.0
    return sp - bp


def detect_weakness(
    stock: Stock,
    board: Board,
    zt: LimitUpInfo | None,
    zb: LimitBreakInfo | None,
    board_leaders_avg_pct: float,
) -> list[str]:
    """看懂弱势 / 结构失效信号。"""
    flags: list[str] = []
    pct = stock.change_percent
    if zb and not zt:
        flags.append(f"炸板{zb.open_count}次")
    if zt and zt.open_count >= 2:
        flags.append(f"开板{zt.open_count}次·封单不稳")
    if pct is not None and board.change_percent is not None:
        if board.change_percent >= 2.0 and pct < board.change_percent - 3.0:
            flags.append("板块强个股弱·可能被压制")
    if pct is not None and board_leaders_avg_pct > 7.0 and pct < board_leaders_avg_pct - 4.0:
        flags.append("相对龙一龙二掉队")
    if (stock.main_net_inflow or 0) < -5e7 and (pct or 0) > 5:
        flags.append("上涨放主力流出·资金换方向嫌疑")
    if zt is None and pct is not None and pct >= 9.5:
        flags.append("接近涨停未封·带动性待确认")
    return flags


def score_candidate(
    stock: Stock,
    board: Board,
    board_score: float,
    board_rank: int,
    zt: LimitUpInfo | None,
    zb: LimitBreakInfo | None,
    rs: float,
    weakness: list[str],
) -> tuple[float, list[str], list[str]]:
    """综合得分 + 标签 + 理由。"""
    score = board_score * 0.35
    tags: list[str] = []
    reasons: list[str] = []

    # 全局带动性：靠前主线加权
    if board_rank == 0:
        score += 18
        tags.append("主线核心位")
        reasons.append("所在板块为当日最强主线之一")
    elif board_rank <= 2:
        score += 12
        tags.append("主线梯队")
    elif board_rank <= 5:
        score += 6
        tags.append("支线偏强")
    else:
        tags.append("局部热闹")
        reasons.append("板块排名靠后，警惕把局部当中心")

    pct = stock.change_percent or 0.0
    score += max(min(pct * 2.2, 28.0), -15.0)

    if zt:
        score += 16
        tags.append(f"{zt.consecutive_boards}连板" if zt.consecutive_boards > 1 else "涨停")
        kind = "竞价封" if zt.first_seal_time and zt.first_seal_time <= 92559 else "盘中封"
        reasons.append(f"{format_fbt(zt.first_seal_time) or '--'}{kind}")
        if zt.consecutive_boards >= 2:
            score += min(zt.consecutive_boards * 3.0, 12.0)
            reasons.append("连板高度抬升辨识度")
        if zt.open_count == 0:
            score += 4
        else:
            score -= min(zt.open_count * 3.0, 10.0)
    elif zb:
        score -= 8
        tags.append("炸板")
        reasons.append("曾封后打开，带动性存疑")

    # 相对强度：走出强度才值得研究
    if rs >= 2.0:
        score += min(rs * 2.5, 14.0)
        reasons.append(f"相对板块超强 {rs:+.1f}%")
    elif rs <= -2.0:
        score -= min(abs(rs) * 2.0, 12.0)
        reasons.append(f"相对板块偏弱 {rs:+.1f}%")

    amount = stock.amount or 0.0
    if amount >= 5e8:
        score += 6
        tags.append("放量")
    elif amount >= 2e8:
        score += 3

    # 弱势扣分 —— 看懂弱的东西
    score -= min(len(weakness) * 5.5, 22.0)
    for w in weakness:
        reasons.append(f"弱势：{w}")

    # 漂亮图形不等于可做：无涨停、无相对强度、仅高涨幅时略降权
    if not zt and rs < 1.0 and pct >= 5.0:
        score -= 4
        reasons.append("涨幅尚可但未确认带动性")

    return score, tags, reasons


def attention_for(score: float, weakness: list[str], params: StrategyParams) -> str:
    if len(weakness) >= 3 or score < params.watch_score - 8:
        return "回避"
    if score >= params.focus_score and len(weakness) <= 1:
        return "聚焦"
    return "观察"


def pick_board_leaders(
    stocks: list[Stock],
    board: Board,
    zt_by_code: dict[str, LimitUpInfo],
    zb_by_code: dict[str, LimitBreakInfo],
    limit: int,
) -> list[tuple[Stock, float]]:
    """板块内按强度排序，筛掉 ST / 无行情。"""
    scored: list[tuple[Stock, float]] = []
    for s in stocks:
        if is_st(s.name):
            continue
        if s.price is None or s.change_percent is None:
            continue
        zt = zt_by_code.get(s.code)
        base = (s.change_percent or 0.0)
        if zt:
            base += 20 + zt.consecutive_boards * 3 - zt.open_count * 2
            if zt.first_seal_time and zt.first_seal_time <= 92559:
                base += 5
        elif zb_by_code.get(s.code):
            base -= 5
        base += min((s.amount or 0) / 1e8, 8.0)
        scored.append((s, base))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def run_strategy(snapshot: MarketSnapshot, params: StrategyParams | None = None) -> list[Candidate]:
    params = params or StrategyParams()
    boards = [
        b
        for b in snapshot.boards
        if not is_noise_board(b.name) and b.member_count >= params.min_board_members
    ]
    boards = sorted(boards, key=board_strength, reverse=True)[: params.top_boards]
    if not boards:
        return []

    board_scores = [(b, board_strength(b)) for b in boards]
    candidates: list[Candidate] = []

    for board_rank, (board, bscore) in enumerate(board_scores):
        stocks = snapshot.stocks_by_board.get(board.code) or []
        leaders = pick_board_leaders(
            stocks,
            board,
            snapshot.zt_by_code,
            snapshot.zb_by_code,
            params.leaders_per_board + 2,
        )
        if not leaders:
            continue

        top_pcts = [s.change_percent or 0.0 for s, _ in leaders[:2]]
        leaders_avg = sum(top_pcts) / max(len(top_pcts), 1)

        for local_idx, (stock, _) in enumerate(leaders[: params.leaders_per_board]):
            if (stock.change_percent or 0.0) < params.min_change_pct and stock.code not in snapshot.zt_by_code:
                # 高度聚焦：未满足观察条件，跳过
                continue
            zt = snapshot.zt_by_code.get(stock.code)
            zb = snapshot.zb_by_code.get(stock.code)
            rs = stock_relative_strength(stock, board)
            weakness = detect_weakness(stock, board, zt, zb, leaders_avg)
            score, tags, reasons = score_candidate(
                stock, board, bscore, board_rank, zt, zb, rs, weakness
            )
            attention = attention_for(score, weakness, params)
            rank_label = ["龙一", "龙二", "龙三"][local_idx] if local_idx < 3 else f"龙{local_idx+1}"
            if board_rank == 0 and local_idx == 0 and zt:
                rank_label = "总龙头候选"

            candidates.append(
                Candidate(
                    rank_label=rank_label,
                    code=stock.code,
                    name=stock.name,
                    board_name=board.name,
                    board_kind=board.kind,
                    change_percent=stock.change_percent,
                    price=stock.price,
                    amount=stock.amount,
                    score=score,
                    tags=tags,
                    reasons=reasons,
                    is_limit_up=bool(zt),
                    is_broken=bool(zb and not zt),
                    consecutive_boards=zt.consecutive_boards if zt else None,
                    first_seal_time=format_fbt(zt.first_seal_time if zt else (zb.first_seal_time if zb else None)),
                    attention=attention,
                    weakness_flags=weakness,
                    source=stock.source or snapshot.source,
                )
            )

    # 去重：同代码保留最高分
    best: dict[str, Candidate] = {}
    for c in candidates:
        prev = best.get(c.code)
        if prev is None or c.score > prev.score:
            best[c.code] = c

    ordered = sorted(best.values(), key=lambda c: c.score, reverse=True)

    # 注意力管理：聚焦最多标 8 只，其余降为观察
    focus_count = 0
    for c in ordered:
        if c.attention == "聚焦":
            focus_count += 1
            if focus_count > 8:
                c.attention = "观察"
                c.reasons.append("注意力配额已满，降为观察")
    return ordered

"""五维打分：每分都对应可核对的量价/封板/板块数字，不靠口感。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from dragon.defs import is_climax, is_rotten, is_yizi
from dragon.themes import theme_of
from dragon.timeutil import fmt_hhmmss

# 给旧测试和回测对照留别名，定义以 dragon.defs 为准。
__all__ = [
    "Dimension",
    "ScoredStock",
    "WEIGHTS",
    "drive_score",
    "height_score",
    "is_yizi",
    "num",
    "recognition_score",
    "resilience_score",
    "score_stock",
    "volume_verdict",
]


def num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "-" or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def volume_verdict(
    *,
    turnover: float,
    amount_yi: float,
    volume_ratio: float | None,
    open_count: int,
    yizi: bool,
) -> tuple[str, float, list[str]]:
    """量能裁判。返回 (结论, 0-100分, 证据句)。"""
    reasons: list[str] = []
    hs = turnover
    reasons.append(f"换手{hs:.2f}%")
    reasons.append(f"成交{amount_yi:.2f}亿")
    if volume_ratio is not None and volume_ratio > 0:
        reasons.append(f"量比{volume_ratio:.2f}")

    if yizi:
        return "一字无量", 8.0, reasons + ["9:25锁死且换手<3%，没有交换，不能定龙"]

    if is_climax(hs, open_count):
        score = 18.0
        if amount_yi >= 10:
            score += 4.0
        return "爆量见顶", score, reasons + ["换手≥35%，或≥28%且已开板，按见顶降权"]

    if 5.0 <= hs <= 22.0 and amount_yi >= 1.5:
        score = 88.0
        if 8.0 <= hs <= 16.0:
            score += 6.0
        if amount_yi >= 5.0:
            score += 4.0
        if volume_ratio is not None and 1.2 <= volume_ratio <= 6.0:
            score += 2.0
        return "健康换手", min(score, 100.0), reasons + ["换手在5-22%，抛压被接住"]

    if 22.0 < hs < 28.0:
        score = 58.0
        if open_count >= 6:
            score -= 12.0
        return "换手偏大", score, reasons + ["接力还在，但已接近消耗区"]

    if 3.0 <= hs < 5.0:
        score = 52.0 if amount_yi >= 2.0 else 42.0
        return "换手偏瘦", score, reasons + ["换手偏少，筹码交换不充分"]

    if hs < 3.0:
        return "量能不足", 28.0, reasons + ["换手过低，更像锁仓或流动性差"]

    return "量能一般", 48.0, reasons


def drive_score(
    *,
    peer_zt: int,
    first_rank: int,
    amount_share: float,
    concept_lead: bool,
    concept_up: int,
    concept_pct: float | None,
) -> tuple[str, float, list[str]]:
    reasons: list[str] = []
    reasons.append(f"同主题涨停{peer_zt}只")
    reasons.append(f"主题内第{first_rank}个封板")
    reasons.append(f"占主题涨停成交额{amount_share * 100:.1f}%")
    if concept_lead:
        reasons.append(f"东财概念领涨（板块涨{concept_pct or 0:.2f}% / 上涨{concept_up}家）")

    if peer_zt <= 1 and not concept_lead:
        return "独立板", 16.0, reasons + ["板块没有跟风：低板是独立票，4板以上先当总龙/高度看"]

    if peer_zt <= 1 and concept_lead and concept_up >= 5:
        return "概念领涨", 62.0, reasons + ["行业池里是孤板，但概念指数有跟风"]

    score = 40.0
    if peer_zt >= 8:
        score += 28.0
    elif peer_zt >= 5:
        score += 22.0
    elif peer_zt >= 3:
        score += 16.0
    elif peer_zt == 2:
        score += 10.0

    if first_rank == 1:
        score += 18.0
        tag = "火车头"
    elif first_rank == 2:
        score += 8.0
        tag = "龙二"
    else:
        score -= 6.0
        tag = "跟风板"

    if amount_share >= 0.45:
        score += 8.0
        reasons.append("主题量能主力")
    elif amount_share >= 0.25:
        score += 4.0

    if concept_lead:
        score += 10.0
    if concept_up >= 10:
        score += 4.0

    score = max(0.0, min(score, 100.0))
    if tag == "跟风板" and peer_zt >= 2:
        return "跟风板", min(score, 55.0), reasons
    if tag == "火车头" and peer_zt >= 3:
        return "火车头", score, reasons
    if tag == "火车头":
        return "有带动", score, reasons
    return tag, score, reasons


def resilience_score(
    *,
    sealed: bool,
    open_count: int,
    change_pct: float,
    turnover: float,
    high: float | None,
    price: float | None,
    pre_close: float | None,
    sector_pct: float | None,
) -> tuple[str, float, list[str]]:
    reasons: list[str] = []
    reasons.append(f"炸板{open_count}次")
    reasons.append(f"涨幅{change_pct:.2f}%")

    dd = 0.0
    if high and price and high > 0:
        dd = (high - price) / high * 100.0
        reasons.append(f"相对最高价回撤{dd:.2f}%")

    rs = None
    if sector_pct is not None:
        rs = change_pct - sector_pct
        reasons.append(f"相对板块超额{rs:+.2f}pct")

    if sealed and open_count == 0:
        return "零炸抗揍", 92.0, reasons + ["封住后没开板"]
    if sealed and open_count <= 2:
        score = 78.0 if open_count == 1 else 72.0
        return "轻分歧回封", score, reasons + ["开板次数少，承接力还在"]
    if sealed and open_count <= 5:
        return "多次回封", 52.0, reasons + ["分歧明显，先看量能不能缩"]
    if sealed and open_count > 5:
        extra = "放量烂板" if turnover >= 15 else "烂板"
        return extra, 24.0 if turnover >= 20 else 30.0, reasons + ["炸太多次，抗跌性差"]

    if not sealed and change_pct >= 7.0:
        return "冲板未确认", 38.0, reasons
    if rs is not None and rs >= 3 and change_pct > 0:
        return "相对抗跌", 58.0, reasons
    return "跟跌/掉队", 18.0, reasons


def recognition_score(
    *,
    pop_rank: int | None,
    amount_rank_market: int,
    amount_rank_theme: int,
    is_height_leader: bool,
    boards: int,
) -> tuple[str, float, list[str]]:
    reasons: list[str] = []
    if pop_rank:
        reasons.append(f"东财人气榜第{pop_rank}")
    else:
        reasons.append("人气榜未进前100，用人气以外的硬数据")
    reasons.append(f"涨停池成交额第{amount_rank_market}")
    reasons.append(f"主题内成交额第{amount_rank_theme}")
    if is_height_leader:
        reasons.append(f"{boards}板是该主题最高标")

    score = 28.0
    tag = "辨识度一般"
    if pop_rank and pop_rank <= 3:
        score = 94.0
        tag = "人气前三"
    elif pop_rank and pop_rank <= 10:
        score = 78.0
        tag = "人气前十"
    elif pop_rank and pop_rank <= 30:
        score = 62.0
        tag = "有讨论度"
    elif amount_rank_market <= 3:
        score = 70.0
        tag = "成交额焦点"
    elif amount_rank_theme == 1 and boards >= 2:
        score = 66.0
        tag = "主题量能第一"

    if is_height_leader and boards >= 4:
        score = max(score, 74.0)
        tag = "高度辨识" if not (pop_rank and pop_rank <= 10) else tag
        score = min(100.0, score + 6.0)
    return tag, min(score, 100.0), reasons


def height_score(
    *,
    boards: int,
    theme_max: int,
    market_max: int,
    peer_zt: int,
) -> tuple[str, float, list[str]]:
    reasons = [f"连板{boards}", f"主题最高{theme_max}板", f"市场最高{market_max}板"]
    if boards <= 0:
        return "无板", 0.0, reasons
    if boards >= 5 and boards >= theme_max:
        return "空间高标", 100.0, reasons + ["市场级空间标杆"]
    if boards >= 3 and boards >= theme_max:
        return "板块高标", 86.0, reasons
    if boards >= theme_max and boards == 2:
        score = 72.0 if peer_zt >= 2 else 60.0
        return "二板身位", score, reasons + ["二板定龙观察位"]
    if boards < theme_max:
        return "中位补涨", 32.0, reasons + ["身位落后，不是龙"]
    if boards == 1:
        return "首板试错", 28.0 if peer_zt < 3 else 40.0, reasons
    return "身位一般", 50.0, reasons


WEIGHTS = {
    "volume": 0.30,
    "drive": 0.25,
    "resilience": 0.15,
    "recognition": 0.15,
    "height": 0.15,
}


@dataclass
class Dimension:
    key: str
    name: str
    verdict: str
    score: float
    evidence: list[str]


@dataclass
class ScoredStock:
    code: str
    name: str
    industry: str
    theme: str
    price: float
    change_pct: float
    boards: int
    first_seal: str
    first_seal_raw: int
    open_count: int
    turnover: float
    amount_yi: float
    volume_ratio: float | None
    seal_fund_yi: float
    circ_yi: float
    volume_share: float
    peer_zt: int
    first_rank: int
    pop_rank: int | None
    yizi: bool
    sealed: bool
    dimensions: dict[str, Dimension] = field(default_factory=dict)
    total: float = 0.0
    role: str = ""
    status: str = ""
    why: str = ""
    pass_leader: bool = False
    in_mainline: bool = False
    lane: str = ""
    tags: list[str] = field(default_factory=list)
    tradable: bool = False
    climax: bool = False
    rotten: bool = False
    hats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def score_stock(
    row: dict[str, Any],
    *,
    theme_peers: list[dict[str, Any]],
    market_max_boards: int,
    amount_rank_market: int,
    pop_rank: int | None,
    concept: dict[str, Any] | None,
    sector_pct: float | None,
) -> ScoredStock:
    code = str(row["code"])
    name = str(row["name"])
    industry = str(row.get("industry") or "")
    theme = str(row.get("theme") or theme_of(industry))
    turnover = num(row.get("turnover"))
    amount = num(row.get("amount"))
    amount_yi = amount / 1e8
    boards = int(row.get("boards") or 0)
    first_raw = int(row.get("first_seal") or 0)
    open_count = int(row.get("open_count") or 0)
    sealed = bool(row.get("sealed", True))
    yizi = is_yizi(first_raw, open_count, turnover)
    vr = row.get("volume_ratio")
    volume_ratio = num(vr) if vr not in (None, "", "-") else None
    if volume_ratio is not None and volume_ratio <= 0:
        volume_ratio = None

    peers = [p for p in theme_peers if p.get("sealed", True)]
    peer_zt = max(1, len(peers))
    ordered = sorted(peers, key=lambda x: int(x.get("first_seal") or 999999))
    first_rank = 1
    for i, p in enumerate(ordered, 1):
        if str(p.get("code")) == code:
            first_rank = i
            break
    theme_amount = sum(num(p.get("amount")) for p in peers) or 1.0
    amount_share = amount / theme_amount if theme_amount else 0.0
    theme_max = max((int(p.get("boards") or 0) for p in peers), default=boards)
    amount_rank_theme = 1 + sum(1 for p in peers if num(p.get("amount")) > amount)

    concept = concept or {}
    concept_lead = bool(concept.get("lead_code") == code or concept.get("lead_name") == name)
    vol_v, vol_s, vol_e = volume_verdict(
        turnover=turnover,
        amount_yi=amount_yi,
        volume_ratio=volume_ratio,
        open_count=open_count,
        yizi=yizi,
    )
    drv_v, drv_s, drv_e = drive_score(
        peer_zt=peer_zt,
        first_rank=first_rank,
        amount_share=amount_share,
        concept_lead=concept_lead,
        concept_up=int(concept.get("up") or 0),
        concept_pct=concept.get("pct"),
    )
    res_v, res_s, res_e = resilience_score(
        sealed=sealed,
        open_count=open_count,
        change_pct=num(row.get("change_pct")),
        turnover=turnover,
        high=row.get("high"),
        price=row.get("price"),
        pre_close=row.get("pre_close"),
        sector_pct=sector_pct,
    )
    rec_v, rec_s, rec_e = recognition_score(
        pop_rank=pop_rank,
        amount_rank_market=amount_rank_market,
        amount_rank_theme=amount_rank_theme,
        is_height_leader=boards >= theme_max and boards >= 2,
        boards=boards,
    )
    h_v, h_s, h_e = height_score(
        boards=boards,
        theme_max=theme_max,
        market_max=market_max_boards,
        peer_zt=peer_zt,
    )

    dims = {
        "volume": Dimension("volume", "换手量能", vol_v, round(vol_s, 1), vol_e),
        "drive": Dimension("drive", "带动性", drv_v, round(drv_s, 1), drv_e),
        "resilience": Dimension("resilience", "抗跌性", res_v, round(res_s, 1), res_e),
        "recognition": Dimension("recognition", "辨识度", rec_v, round(rec_s, 1), rec_e),
        "height": Dimension("height", "高度身位", h_v, round(h_s, 1), h_e),
    }
    total = (
        dims["volume"].score * WEIGHTS["volume"]
        + dims["drive"].score * WEIGHTS["drive"]
        + dims["resilience"].score * WEIGHTS["resilience"]
        + dims["recognition"].score * WEIGHTS["recognition"]
        + dims["height"].score * WEIGHTS["height"]
    )

    isolated = peer_zt <= 1
    climax = vol_v == "爆量见顶" or is_climax(turnover, open_count)
    rotten = is_rotten(open_count, turnover) or res_v in {"放量烂板", "烂板"}
    tradable = bool(sealed and not yizi and not climax and not rotten)
    tags: list[str] = []
    if yizi:
        tags.append("一字")
    if climax:
        tags.append("爆量")
    if rotten:
        tags.append("烂板")
    if vol_v == "健康换手":
        tags.append("健康换手")
    elif vol_v == "换手偏瘦":
        tags.append("偏瘦")
    elif vol_v == "换手偏大":
        tags.append("偏大")
    if isolated and boards < 4:
        tags.append("独立")
    elif isolated and boards >= 4:
        tags.append("总龙观察")
    if pop_rank and pop_rank <= 3:
        tags.append("人气前三")
    elif pop_rank and pop_rank <= 10:
        tags.append("人气前十")
    if boards >= 4 and not yizi:
        tags.append("高标")

    # 角色先按票本身定性，通道（主线/支线）和帽子（火车头/情绪/空间）后面再戴。
    if yizi:
        role, status, ok = "高度锚", "一字无量 · 只看高度，不当交易龙", False
        total = min(total, 35.0)
    elif climax:
        role, status, ok = "见顶观察", "量能见顶 · 不予定龙", False
        total = min(total, 48.0)
    elif isolated and boards < 4:
        role, status, ok = "独立票", "同主题没有跟风 · 游资热点，不当情绪龙", False
        total = min(total, 42.0)
    elif drv_v == "独立板" and boards < 4:
        role, status, ok = "独立票", "带不动板块 · 不当情绪龙", False
        total = min(total, 42.0)
    elif isolated and boards >= 4:
        role, status, ok = "空间龙", "板块没跟风，先当总龙/高度看", tradable
        if not tradable:
            status = "高度在，但量或板已经散了"
    elif drv_v == "跟风板":
        role, status, ok = "跟风", "身位或封板顺序落后", False
        total = min(total, 58.0)
    elif not sealed:
        role, status, ok = "观察", "今日未封死", False
    else:
        has_drive = drv_v in {"火车头", "有带动", "概念领涨", "龙二"}
        healthy = vol_v in {"健康换手", "换手偏大", "换手偏瘦"}
        ok = has_drive and healthy and boards >= 1 and tradable
        if boards >= 4 and has_drive and vol_v == "健康换手":
            role, status = "空间龙", "高度 + 带动 + 健康换手"
        elif drv_v == "火车头" and boards >= 2:
            role, status = "主线龙", "主题里先起来的，量能对得上"
        elif drv_v in {"火车头", "有带动", "概念领涨"} and boards == 1:
            role, status = "先锋", "首板先起来，先看能不能晋级"
        elif has_drive:
            role, status = "龙头候选", "五维过线"
        else:
            role, status, ok = "观察", "带动不足", False

    why_parts = [
        f"{name} {boards}板",
        f"换手{turnover:.1f}%/{vol_v}",
        f"成交{amount_yi:.2f}亿",
        f"{theme}同向涨停{peer_zt}只（第{first_rank}封）",
        f"炸{open_count}次",
    ]
    if pop_rank:
        why_parts.append(f"人气第{pop_rank}")

    return ScoredStock(
        code=code,
        name=name,
        industry=industry,
        theme=theme,
        price=round(num(row.get("price")), 2),
        change_pct=round(num(row.get("change_pct")), 2),
        boards=boards,
        first_seal=fmt_hhmmss(first_raw),
        first_seal_raw=first_raw,
        open_count=open_count,
        turnover=round(turnover, 2),
        amount_yi=round(amount_yi, 2),
        volume_ratio=round(volume_ratio, 2) if volume_ratio is not None else None,
        seal_fund_yi=round(num(row.get("seal_fund")) / 1e8, 2),
        circ_yi=round(num(row.get("circ_mv")) / 1e8, 2),
        volume_share=round(amount_share, 4),
        peer_zt=peer_zt,
        first_rank=first_rank,
        pop_rank=pop_rank,
        yizi=yizi,
        sealed=sealed,
        dimensions=dims,
        total=round(total, 2),
        role=role,
        status=status,
        why=" · ".join(why_parts),
        pass_leader=ok,
        tags=tags,
        tradable=tradable,
        climax=climax,
        rotten=rotten,
    )

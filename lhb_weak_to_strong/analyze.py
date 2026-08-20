"""Pipeline: fetch → filter → seat enrich → score → summarize."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .fetch import fetch_buy_seats, fetch_lhb_detail, normalize_date, seat_quality
from .methods import PLAYBOOK_STEPS, PUBLIC_METHODS
from .score import ANCHOR_CASES, SCORE_VERSION, passes_hard_filters, score_candidate

RESEARCH_PATH = Path(__file__).resolve().parents[1] / "data" / "research_summary.json"
RESEARCH_CACHE_FALLBACK = (
    Path(__file__).resolve().parents[1] / "data" / "lhb_cache" / "research_summary.json"
)


def _row_to_dict(row: pd.Series) -> dict[str, Any]:
    return {k: row[k] for k in row.index}


def analyze_trade_date(
    trade_date: str,
    enrich_seats: bool = True,
    use_cache: bool = True,
    min_net: float = 0.0,
    min_ratio: float = 0.0,
) -> dict[str, Any]:
    """Analyze one trade date and return structured weak-to-strong signals."""
    iso, ymd = normalize_date(trade_date)
    raw = fetch_lhb_detail(iso, iso, use_cache=use_cache)
    if raw.empty:
        return {
            "trade_date": iso,
            "score_version": SCORE_VERSION,
            "raw_count": 0,
            "candidates": [],
            "rejected": [],
            "cluster_count": 0,
            "summary": {"message": "当日无龙虎榜数据或非交易日"},
        }

    # Deduplicate multi-reason listings: keep max net buy row per code
    work = raw.copy()
    work["代码"] = work["代码"].astype(str)
    work = work.sort_values("龙虎榜净买额", ascending=False)
    work = work.drop_duplicates(subset=["代码"], keep="first")

    prelim: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for _, row in work.iterrows():
        d = _row_to_dict(row)
        ok, reason = passes_hard_filters(d)
        if not ok:
            rejected.append(
                {
                    "code": str(d.get("代码")),
                    "name": str(d.get("名称")),
                    "chg": float(d.get("涨跌幅") or 0),
                    "net": float(d.get("龙虎榜净买额") or 0),
                    "reason": reason,
                }
            )
            continue
        net = float(d.get("龙虎榜净买额") or 0)
        ratio = float(d.get("净买额占总成交比") or 0)
        if net < min_net or ratio < min_ratio:
            rejected.append(
                {
                    "code": str(d.get("代码")),
                    "name": str(d.get("名称")),
                    "chg": float(d.get("涨跌幅") or 0),
                    "net": net,
                    "reason": f"未达自定义门槛 net>={min_net} ratio>={min_ratio}",
                }
            )
            continue
        prelim.append(d)

    cluster_count = len(prelim)
    candidates: list[dict[str, Any]] = []
    for d in prelim:
        seat: dict[str, Any] = {}
        if enrich_seats:
            try:
                buy_df = fetch_buy_seats(str(d["代码"]), iso, use_cache=use_cache)
                seat = seat_quality(buy_df)
            except Exception as exc:  # noqa: BLE001 — keep pipeline alive
                seat = {
                    "n_inst": 0,
                    "n_north": 0,
                    "n_hot": 0,
                    "inst_net": 0.0,
                    "north_net": 0.0,
                    "hot_net": 0.0,
                    "buy_seats": [],
                    "seat_error": str(exc),
                }
        scored = score_candidate(d, seat=seat, cluster_count=cluster_count)
        candidates.append(scored)

    candidates.sort(key=lambda x: (x.get("score") or 0, x.get("net") or 0), reverse=True)

    # Contrast set: big drop but net sell (弱势出货)
    weak_dump = []
    for _, row in work.iterrows():
        d = _row_to_dict(row)
        chg = float(d.get("涨跌幅") or 0)
        net = float(d.get("龙虎榜净买额") or 0)
        name = str(d.get("名称") or "")
        code = str(d.get("代码") or "")
        from .score import is_excluded

        if is_excluded(code, name):
            continue
        if chg <= -7 and net <= 0:
            weak_dump.append(
                {
                    "code": code,
                    "name": name,
                    "chg": chg,
                    "net": net,
                    "ratio": float(d.get("净买额占总成交比") or 0),
                    "t1": d.get("上榜后1日"),
                    "t5": d.get("上榜后5日"),
                }
            )
    weak_dump.sort(key=lambda x: x["net"])

    s_count = sum(1 for c in candidates if c.get("tier") == "S")
    a_count = sum(1 for c in candidates if c.get("tier") == "A")
    index_ctx = _index_context(iso)
    research = _load_research()

    summary = {
        "message": (
            f"{iso} 弱转强候选 {cluster_count} 只"
            f"（S级 {s_count} / A级 {a_count}）；"
            f"对照弱势出货 {len(weak_dump)} 只"
        ),
        "cluster_flag": cluster_count >= 3,
        "playbook": _playbook(cluster_count, candidates, index_ctx),
        "index": index_ctx,
    }

    return {
        "trade_date": iso,
        "score_version": SCORE_VERSION,
        "raw_count": int(len(raw)),
        "cluster_count": cluster_count,
        "candidates": candidates,
        "weak_dump": weak_dump[:15],
        "rejected_sample": rejected[:20],
        "anchor_cases": ANCHOR_CASES,
        "methods": PUBLIC_METHODS,
        "research": research,
        "summary": summary,
    }


def _load_research() -> dict[str, Any] | None:
    for path in (RESEARCH_PATH, RESEARCH_CACHE_FALLBACK):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
    return None


def _index_context(trade_date: str) -> dict[str, Any]:
    """Attach SH composite day/next change when available."""
    try:
        import akshare as ak

        iso, _ = normalize_date(trade_date)
        idx = ak.stock_zh_index_daily(symbol="sh000001")
        idx["date"] = pd.to_datetime(idx["date"]).dt.strftime("%Y-%m-%d")
        idx = idx.sort_values("date").reset_index(drop=True)
        idx["pct"] = idx["close"].pct_change() * 100
        hit = idx.index[idx["date"] == iso]
        if len(hit) == 0:
            return {}
        i = int(hit[0])
        day_pct = float(idx.loc[i, "pct"]) if pd.notna(idx.loc[i, "pct"]) else None
        next_pct = None
        if i + 1 < len(idx):
            next_pct = float(idx.loc[i + 1, "pct"]) if pd.notna(idx.loc[i + 1, "pct"]) else None
        # Cluster quality heuristic: same-day index not in freefall AND
        # (if known) next day not continuing deep red.
        quality = "unknown"
        if day_pct is not None:
            if day_pct <= -1.5:
                quality = "caution_waterfall"
            elif day_pct >= 0.5:
                quality = "bounce_day"
            else:
                quality = "neutral_chop"
        if next_pct is not None:
            if next_pct >= 0.2:
                quality = "confirmed_bounce" if day_pct is not None and day_pct > -2 else "next_green"
            elif next_pct <= -1.0:
                quality = "confirmed_waterfall"
        return {
            "index": "上证指数",
            "idx_day_pct": None if day_pct is None else round(day_pct, 2),
            "idx_next_pct": None if next_pct is None else round(next_pct, 2),
            "cluster_regime": quality,
        }
    except Exception as exc:  # noqa: BLE001
        return {"index_error": str(exc)}


def _playbook(
    cluster_count: int,
    candidates: list[dict[str, Any]],
    index_ctx: dict[str, Any] | None = None,
) -> list[str]:
    steps = list(PLAYBOOK_STEPS)
    if cluster_count >= 3:
        steps.insert(0, f"今日共振信号开启（{cluster_count}只），可提高试错优先级")
        regime = (index_ctx or {}).get("cluster_regime")
        if regime in {"caution_waterfall", "confirmed_waterfall"}:
            steps.insert(1, "⚠ 大盘仍处杀跌/续跌环境：共振可能是假信号，降仓或观望")
        elif regime in {"bounce_day", "confirmed_bounce", "next_green"}:
            steps.insert(1, "✓ 大盘止跌/反弹环境：共振质量更接近 7/20、8/3 一类反击日")
    top = [c for c in candidates if c.get("tier") in {"S", "A"}]
    if top:
        names = "、".join(f"{c['name']}({c['code']})" for c in top[:4])
        steps.append(f"重点池：{names}")
    return steps


def run_backtest_summary(
    start_date: str,
    end_date: str,
    min_net: float = 3e7,
    min_ratio: float = 1.5,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Lightweight stats without seat enrichment (fast)."""
    iso_s, _ = normalize_date(start_date)
    iso_e, _ = normalize_date(end_date)
    raw = fetch_lhb_detail(iso_s, iso_e, use_cache=use_cache)
    if raw.empty:
        return {"start": iso_s, "end": iso_e, "n": 0}

    d = raw.copy()
    d["代码"] = d["代码"].astype(str)
    from .score import is_excluded

    mask = []
    for _, row in d.iterrows():
        mask.append(not is_excluded(str(row["代码"]), str(row["名称"])))
    d = d[mask]
    d = d.sort_values("龙虎榜净买额", ascending=False).drop_duplicates(
        subset=["代码", "上榜日"], keep="first"
    )

    wts = d[(d["涨跌幅"] <= -7) & (d["龙虎榜净买额"] > 0)].copy()
    dump = d[(d["涨跌幅"] <= -7) & (d["龙虎榜净买额"] <= 0)].copy()
    filtered = wts[(wts["龙虎榜净买额"] >= min_net) & (wts["净买额占总成交比"] >= min_ratio)].copy()

    def _stats(frame: pd.DataFrame) -> dict[str, Any]:
        t1 = pd.to_numeric(frame["上榜后1日"], errors="coerce").dropna()
        t5 = pd.to_numeric(frame["上榜后5日"], errors="coerce").dropna()
        return {
            "n": int(len(frame)),
            "t1_n": int(len(t1)),
            "t1_mean": round(float(t1.mean()), 2) if len(t1) else None,
            "t1_median": round(float(t1.median()), 2) if len(t1) else None,
            "t1_win": round(float((t1 > 0).mean() * 100), 1) if len(t1) else None,
            "t5_mean": round(float(t5.mean()), 2) if len(t5) else None,
            "t5_win": round(float((t5 > 0).mean() * 100), 1) if len(t5) else None,
        }

    # cluster-day subset
    day_counts = filtered.groupby("上榜日").size()
    cluster_days = set(day_counts[day_counts >= 3].index.astype(str))
    cluster = filtered[filtered["上榜日"].astype(str).isin(cluster_days)]

    return {
        "start": iso_s,
        "end": iso_e,
        "score_version": SCORE_VERSION,
        "filters": {"min_net": min_net, "min_ratio": min_ratio, "chg_max": -7},
        "weak_to_strong_raw": _stats(wts),
        "weak_dump": _stats(dump),
        "weak_to_strong_filtered": _stats(filtered),
        "cluster_days_filtered": _stats(cluster),
        "note": (
            "粗筛胜率接近硬币；加净买额/占比门槛后略改善。"
            "同日≥3只共振需叠加大盘止跌才有效："
            "反击日（如7/20、8/3）胜率高，续跌日（如7/3、7/10）胜率接近0。"
            "样本随区间变化，不构成收益承诺。"
        ),
    }

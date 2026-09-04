"""选股服务：三种策略扫描 + 盘前快照。"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Callable

from auction_screener.fetch import (
    CST,
    auction_from_trends,
    fetch_live_quotes,
    fetch_trends,
    latest_zt_date,
)
from auction_screener.rules import (
    is_auction_limit_up,
    is_main_board,
    optimized_select,
    score_lianban,
    sequential_select,
    turnover_pct,
    vol_over_free,
    vol_ratio,
)
from auction_screener.trajectory import (
    AuctionTick,
    TrajectoryState,
    hhmmss_from_str,
    score_trajectory,
)

# 回测胜率100%硬条件
WR100_OPEN_LO = 3.0
WR100_OPEN_HI = 5.0
WR100_TOP_N = 3
WR100_TP = 0.008


def now_hhmmss(now: datetime | None = None) -> int:
    now = now or datetime.now(CST)
    return now.hour * 10000 + now.minute * 100 + now.second


def auction_phase(ts: int | None = None) -> dict[str, Any]:
    ts = now_hhmmss() if ts is None else ts
    if 91500 <= ts < 92000:
        phase, tip = "observe", "09:15–09:20 可撤单，只观察"
    elif 92000 <= ts < 92500:
        phase, tip = "decision", "09:20–09:25 主决策窗"
    elif 92500 <= ts < 93000:
        phase, tip = "lock", "09:25–09:30 锁定标的，准备挂单"
    elif 93000 <= ts < 150000:
        phase, tip = "trading", "已开盘，可用分时回放扫描"
    else:
        phase, tip = "idle", "非竞价决策时段"
    return {"ts": ts, "phase": phase, "tip": tip, "clock": f"{ts // 10000:02d}:{(ts // 100) % 100:02d}:{ts % 100:02d}"}


def zt_prev_close(zt: dict[str, Any]) -> float:
    p = float(zt.get("p") or 0)
    if p > 1000:
        return p / 1000.0
    return p


def enrich_from_trends(zt: dict[str, Any]) -> dict[str, Any] | None:
    code, name = zt["c"], zt["n"]
    payload = fetch_trends(code, ndays=5)
    auction = auction_from_trends(payload)
    if not auction:
        return None
    prev = auction["prev_close"] or zt_prev_close(zt)
    ltsz = float(zt.get("ltsz") or 0)
    free = (ltsz / prev) if prev else 0.0
    today = auction["today_auction"]
    yest = auction["yest_auction"]
    open_px = today["px"]
    shares = today["vol_lots"] * 100.0
    open_pct = (open_px / prev - 1) * 100 if prev else 0.0
    amt_ratio = (today["amt"] / yest["amt"]) if yest["amt"] else 0.0
    mv_yi = ltsz / 1e8 if ltsz else 0.0
    return {
        "code": code,
        "name": name,
        "hy": zt.get("hybk") or "",
        "lbc": int(zt.get("lbc") or 0) or 1,
        "zbc": int(zt.get("zbc") or 0),
        "fbt": int(zt.get("fbt") or 150000),
        "hs": float(zt.get("hs") or 0),
        "mv_yi": round(mv_yi, 2),
        "prev": round(prev, 3),
        "open": round(open_px, 3),
        "open_pct": round(open_pct, 2),
        "is_auction_zt": is_auction_limit_up(open_px, prev, code, name),
        "auction_shares": shares,
        "auction_lots": today["vol_lots"],
        "auction_amt": today["amt"],
        "yest_auction_amt": yest["amt"],
        "amt_ratio": round(amt_ratio, 3),
        "vol_ratio": round(vol_ratio(today["vol_lots"], auction["avg5_lots"]), 2),
        "turnover": round(turnover_pct(shares, free), 4),
        "vol_over_free": vol_over_free(shares, free),
        "free_float": free,
        "trade_date": auction["today"],
        "zt_date": auction["yesterday"],
    }


def wr100_ok(row: dict[str, Any]) -> bool:
    open_pct = float(row.get("open_pct") or 0)
    if not (WR100_OPEN_LO < open_pct < WR100_OPEN_HI):
        return False
    lbc = int(row.get("lbc") or 1)
    if not (1 <= lbc <= 4):
        return False
    if int(row.get("zbc") or 0) > 1:
        return False
    mv = float(row.get("mv_yi") or 0)
    if mv > 0 and not (20 < mv < 150):
        return False
    if int(row.get("fbt") or 150000) > 100000:
        return False
    if row.get("is_auction_zt"):
        return False
    return True


def wr100_select(rows: list[dict[str, Any]], top_n: int = WR100_TOP_N) -> dict[str, list[dict[str, Any]]]:
    from collections import Counter

    universe = []
    for row in rows:
        code = str(row.get("code") or "")
        name = str(row.get("name") or "")
        if not is_main_board(code, name):
            continue
        if row.get("is_auction_zt"):
            continue
        universe.append(row)
    plate = Counter(str(r.get("hy") or "") for r in universe if r.get("hy"))
    passed = []
    for row in universe:
        if not wr100_ok(row):
            continue
        sc, reasons = score_lianban(row, plate)
        item = dict(row)
        item["score"] = round(sc, 2)
        item["reasons"] = reasons + [f"止盈建议+{WR100_TP * 100:.1f}%"]
        item["tp_hint"] = WR100_TP
        passed.append(item)
    ranked = sorted(passed, key=lambda r: (float(r.get("score") or 0), float(r.get("vol_over_free") or 0)), reverse=True)
    return {
        "universe": universe,
        "after_numeric": ranked,
        "top5": ranked[:top_n],
        "top8": ranked[: max(8, top_n)],
    }


def _public_row(r: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "code", "name", "hy", "lbc", "zbc", "fbt", "mv_yi", "open", "prev", "open_pct",
        "auction_shares", "vol_ratio", "amt_ratio", "turnover", "vol_over_free",
        "score", "reasons", "traj_label", "traj_score", "tp_hint", "is_auction_zt",
    )
    out = {k: r.get(k) for k in keys if k in r}
    if out.get("auction_shares") is not None:
        out["auction_wan"] = round(float(out["auction_shares"]) / 1e4, 1)
    return out


def scan_pool(
    mode: str = "optimized",
    *,
    top_n: int = 5,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """用昨涨停池 + 分时首根（竞价）扫描。"""
    t0 = time.time()
    now = datetime.now(CST)
    zt_date, pool = latest_zt_date(now)
    cands = [x for x in pool if is_main_board(x["c"], x["n"])]
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    done = 0

    def _prog(msg: str) -> None:
        if progress:
            progress(msg)

    _prog(f"昨涨停 {zt_date} 主板候选 {len(cands)}")
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(enrich_from_trends, zt): zt for zt in cands}
        for fut in as_completed(futs):
            zt = futs[fut]
            done += 1
            try:
                row = fut.result()
                if row:
                    rows.append(row)
                else:
                    errors.append(f"{zt['c']} 无竞价")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{zt['c']} {exc}")
            if done % 5 == 0 or done == len(cands):
                _prog(f"拉取竞价 {done}/{len(cands)} 成功 {len(rows)}")

    if mode == "baseline":
        picked = sequential_select(rows)
        title = "原版·竞价涨停取反"
    elif mode == "wr100":
        picked = wr100_select(rows, top_n=min(top_n, WR100_TOP_N))
        title = "胜率100%方案（+0.8%止盈）"
    else:
        picked = optimized_select(rows, top_n=top_n)
        title = "连板优化 v2"

    phase = auction_phase()
    return {
        "ok": True,
        "mode": mode,
        "title": title,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "zt_date": zt_date,
        "trade_date": rows[0]["trade_date"] if rows else None,
        "zt_total": len(pool),
        "main_n": len(cands),
        "fetched": len(rows),
        "elapsed_sec": round(time.time() - t0, 1),
        "phase": phase,
        "top": [_public_row(r) for r in picked.get("top5", [])],
        "pool": [_public_row(r) for r in picked.get("after_numeric", picked.get("top8", []))[:30]],
        "errors_n": len(errors),
        "tip": (
            "开盘买入，挂 +0.8% 限价止盈；未触及收盘卖。回测同票拿到收盘胜率约53%。"
            if mode == "wr100"
            else "9:25后结果更稳；盘前请用「盘前盯盘」。研究用，不构成投资建议。"
        ),
    }


_BASE_CACHE: dict[str, Any] = {"zt_date": "", "bases": [], "states": {}}


def _build_preopen_bases(pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cands = [x for x in pool if is_main_board(x["c"], x["n"])]
    bases: list[dict[str, Any]] = []
    for zt in cands:
        code, name = zt["c"], zt["n"]
        prev = zt_prev_close(zt)
        ltsz = float(zt.get("ltsz") or 0)
        free = (ltsz / prev) if prev else 0.0
        yamt = 0.0
        a5 = 0.0
        try:
            payload = fetch_trends(code, ndays=5)
            auction = auction_from_trends(payload)
            if auction:
                yamt = float(auction["yest_auction"]["amt"] or 0)
                a5 = float(auction["avg5_lots"] or 0)
                if not prev:
                    prev = float(auction["prev_close"] or 0)
                    free = (ltsz / prev) if prev else 0.0
        except Exception:  # noqa: BLE001
            pass
        bases.append(
            {
                "code": code,
                "name": name,
                "hy": zt.get("hybk") or "",
                "lbc": int(zt.get("lbc") or 0) or 1,
                "zbc": int(zt.get("zbc") or 0),
                "fbt": int(zt.get("fbt") or 150000),
                "mv_yi": round(ltsz / 1e8, 2) if ltsz else 0.0,
                "prev": prev,
                "free_float": free,
                "yest_auction_amt": yamt,
                "avg5_lots": a5,
            }
        )
    return bases


def preopen_snapshot(mode: str = "optimized", top_n: int = 5) -> dict[str, Any]:
    """盘前：缓存昨涨停底池，用实时盘口 + 走势打分。"""
    now = datetime.now(CST)
    zt_date, pool = latest_zt_date(now)
    if _BASE_CACHE.get("zt_date") != zt_date or not _BASE_CACHE.get("bases"):
        _BASE_CACHE["zt_date"] = zt_date
        _BASE_CACHE["bases"] = _build_preopen_bases(pool)
        _BASE_CACHE["states"] = {}

    bases: list[dict[str, Any]] = _BASE_CACHE["bases"]
    states: dict[str, TrajectoryState] = _BASE_CACHE["states"]
    quotes = fetch_live_quotes([b["code"] for b in bases], prefer="sina")
    ts = now_hhmmss()
    rows: list[dict[str, Any]] = []
    for base in bases:
        code = base["code"]
        q = quotes.get(code)
        if not q:
            continue
        prev = float(q.get("prev") or base.get("prev") or 0)
        px = float(q.get("px") or 0)
        if px <= 0 or prev <= 0:
            continue
        tick_ts = hhmmss_from_str(str(q.get("time") or "")) or ts
        shares = float(q.get("vol_shares") or 0)
        lots = shares / 100.0
        amt = float(q.get("amt") or 0)
        tick = AuctionTick(
            ts=tick_ts,
            px=px,
            prev_close=prev,
            vol_shares=shares,
            amt=amt,
            bid1_vol=float(q.get("bid1_vol") or 0),
            bid1_px=float(q.get("bid1_px") or 0),
            ask1_vol=float(q.get("ask1_vol") or 0),
            ask1_px=float(q.get("ask1_px") or 0),
        )
        st = states.setdefault(code, TrajectoryState())
        st.add(tick)
        traj = score_trajectory(st)
        yamt = float(base.get("yest_auction_amt") or 0)
        free = float(base.get("free_float") or 0)
        open_pct = (px / prev - 1) * 100
        row = {
            **base,
            "open": round(px, 3),
            "open_pct": round(open_pct, 2),
            "is_auction_zt": is_auction_limit_up(px, prev, code, base["name"]),
            "auction_shares": shares,
            "auction_lots": lots,
            "auction_amt": amt,
            "amt_ratio": round((amt / yamt) if yamt else 0.0, 3),
            "vol_ratio": round(vol_ratio(lots, float(base.get("avg5_lots") or 0)), 2),
            "turnover": round(turnover_pct(shares, free), 4),
            "vol_over_free": vol_over_free(shares, free),
            "traj_score": traj.get("traj_score", 0),
            "traj_label": traj.get("traj_label", ""),
        }
        rows.append(row)

    if mode == "wr100":
        picked = wr100_select(rows, top_n=min(top_n, WR100_TOP_N))
        title = "盘前·胜率100%"
    elif mode == "baseline":
        picked = sequential_select(rows)
        title = "盘前·原版"
    else:
        picked = optimized_select(rows, top_n=top_n)
        title = "盘前·连板优化"

    phase = auction_phase(ts)
    return {
        "ok": True,
        "mode": mode,
        "title": title,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "zt_date": zt_date,
        "main_n": len(bases),
        "quoted": len(rows),
        "phase": phase,
        "top": [_public_row(r) for r in picked.get("top5", [])],
        "pool": [_public_row(r) for r in picked.get("after_numeric", [])[:30]],
        "tip": phase["tip"] + " · 研究用，不构成投资建议。",
    }


STRATEGIES = [
    {
        "id": "optimized",
        "name": "连板优化",
        "desc": "收紧量比/金额比，加高度·炸板·市值，综合分排序 Top5",
    },
    {
        "id": "wr100",
        "name": "胜率100%",
        "desc": "回测 36 笔全胜方案：涨幅3–5%，每天最多3只，开盘后 +0.8% 止盈",
    },
    {
        "id": "baseline",
        "name": "原版公式",
        "desc": "你的原始问财条件：竞价涨停取反 + 量占自由前5",
    },
]

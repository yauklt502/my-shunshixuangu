"""选股服务：弱转强（首板/一进二/二进三）+ 其他策略 + 盘前快照。"""

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
    latest_zb_date,
    latest_zt_date,
)
from auction_screener.rules import (
    CATEGORY_ORDER,
    WEAK_TOP_PER_CAT,
    is_auction_limit_up,
    is_main_board,
    optimized_select,
    score_lianban,
    sequential_select,
    turnover_pct,
    vol_over_free,
    vol_ratio,
    weak_select,
    wr100_ok,
    yijin2_select,
)
from auction_screener.trajectory import (
    AuctionTick,
    TrajectoryState,
    hhmmss_from_str,
    score_trajectory,
)

WR100_TOP_N = 3
WR100_TP = 0.008
WEAK_MODES = ("weak", "yijin2")


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


def enrich_from_trends(zt: dict[str, Any], *, src: str = "zt") -> dict[str, Any] | None:
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
    zttj = zt.get("zttj") or {}
    if not isinstance(zttj, dict):
        zttj = {}
    # 炸板池无 lbc；首板候选记 0
    if src == "zb":
        lbc = 0
    else:
        lbc = int(zt.get("lbc") or 0) or 1
    return {
        "code": code,
        "name": name,
        "src": src,
        "hy": zt.get("hybk") or "",
        "lbc": lbc,
        "zbc": int(zt.get("zbc") or 0),
        "fbt": int(zt.get("fbt") or 150000),
        "hs": float(zt.get("hs") or 0),
        "zt_days": int(zttj.get("days") or 0),
        "zt_ct": int(zttj.get("ct") or 0),
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
        "category", "src",
    )
    out = {k: r.get(k) for k in keys if k in r}
    if out.get("auction_shares") is not None:
        out["auction_wan"] = round(float(out["auction_shares"]) / 1e4, 1)
    return out


def _categories_public(picked: dict[str, Any]) -> list[dict[str, Any]]:
    cats = picked.get("categories") or {}
    out = []
    for name in CATEGORY_ORDER:
        rows = [_public_row(r) for r in cats.get(name, [])]
        out.append({"id": name, "name": name, "count": len(rows), "items": rows})
    # 若只有旧接口单类
    if not cats and picked.get("top5"):
        out = [{"id": "精选", "name": "精选", "count": len(picked["top5"]), "items": [_public_row(r) for r in picked["top5"]]}]
    return out


def _fetch_rows(
    items: list[tuple[dict[str, Any], str]],
    *,
    progress: Callable[[str], None] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    done = 0
    seen: set[str] = set()

    def _prog(msg: str) -> None:
        if progress:
            progress(msg)

    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(enrich_from_trends, zt, src=src): (zt, src) for zt, src in items}
        for fut in as_completed(futs):
            zt, src = futs[fut]
            done += 1
            try:
                row = fut.result()
                if row and row["code"] not in seen:
                    seen.add(row["code"])
                    rows.append(row)
                elif not row:
                    errors.append(f"{zt['c']} 无竞价")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{zt['c']} {exc}")
            if done % 5 == 0 or done == len(items):
                _prog(f"拉取竞价 {done}/{len(items)} 成功 {len(rows)}")
    return rows, errors


def scan_pool(
    mode: str = "weak",
    *,
    top_n: int = 5,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """用昨涨停/炸板 + 分时首根（竞价）扫描。"""
    t0 = time.time()
    now = datetime.now(CST)
    zt_date, pool = latest_zt_date(now)

    def _prog(msg: str) -> None:
        if progress:
            progress(msg)

    items: list[tuple[dict[str, Any], str]] = []
    zb_date = ""
    zb_n = 0
    if mode in WEAK_MODES:
        cands_zt = [x for x in pool if is_main_board(x["c"], x["n"])]
        items.extend((x, "zt") for x in cands_zt)
        try:
            zb_date, zb_pool = latest_zb_date(now)
            cands_zb = [x for x in zb_pool if is_main_board(x["c"], x["n"])]
            # 炸板与涨停去重：涨停优先做晋级
            zt_codes = {x["c"] for x in cands_zt}
            cands_zb = [x for x in cands_zb if x["c"] not in zt_codes]
            items.extend((x, "zb") for x in cands_zb)
            zb_n = len(cands_zb)
            _prog(f"昨涨停 {zt_date} {len(cands_zt)} + 昨炸板 {zb_date} {zb_n}")
        except Exception as exc:  # noqa: BLE001
            _prog(f"昨涨停 {zt_date} {len(cands_zt)}（炸板池暂不可用: {exc}）")
    else:
        cands = [x for x in pool if is_main_board(x["c"], x["n"])]
        items.extend((x, "zt") for x in cands)
        _prog(f"昨涨停 {zt_date} 主板候选 {len(cands)}")

    rows, errors = _fetch_rows(items, progress=progress)

    if mode in WEAK_MODES:
        per = min(max(top_n, 1), WEAK_TOP_PER_CAT)
        if mode == "yijin2":
            picked = yijin2_select(rows, top_n=per)
            title = "一进二弱转强（兼容）"
        else:
            picked = weak_select(rows, top_n=per)
            title = "竞价弱转强 · 首板/一进二/二进三"
    elif mode == "baseline":
        picked = sequential_select(rows)
        title = "原版·竞价涨停取反"
    elif mode == "wr100":
        picked = wr100_select(rows, top_n=min(top_n, WR100_TOP_N))
        title = "胜率优先·高开区间"
    else:
        picked = optimized_select(rows, top_n=top_n)
        title = "连板优化 v2"

    categories = _categories_public(picked) if mode in WEAK_MODES else []
    top = [_public_row(r) for r in picked.get("top5", [])]
    if categories:
        top = [r for cat in categories for r in cat["items"]]

    phase = auction_phase()
    tip = (
        "仓位干满、持股3日收盘卖（回测）。一进二开盘0.5%~1.5%且炸板≤1；二进三换手≤8%。"
        "首板3日胜率约五成只观察。每类最多1只。研究用，不构成投资建议。"
        if mode in WEAK_MODES
        else (
            "开盘买入，挂 +0.8% 限价止盈；未触及收盘卖。"
            if mode == "wr100"
            else "9:25后结果更稳；主策略请用「竞价弱转强」。研究用，不构成投资建议。"
        )
    )
    return {
        "ok": True,
        "mode": mode,
        "title": title,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "zt_date": zt_date,
        "zb_date": zb_date or None,
        "trade_date": rows[0]["trade_date"] if rows else None,
        "zt_total": len(pool),
        "zb_n": zb_n,
        "main_n": len({c for c, _ in ((i[0]["c"], i[1]) for i in items)}),
        "fetched": len(rows),
        "elapsed_sec": round(time.time() - t0, 1),
        "phase": phase,
        "categories": categories,
        "top": top,
        "pool": [_public_row(r) for r in picked.get("after_numeric", picked.get("top8", []))[:40]],
        "errors_n": len(errors),
        "tip": tip,
    }


_BASE_CACHE: dict[str, Any] = {"zt_date": "", "zb_date": "", "bases": [], "states": {}}


def _base_from_pool_item(zt: dict[str, Any], *, src: str) -> dict[str, Any]:
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
    lbc = 0 if src == "zb" else (int(zt.get("lbc") or 0) or 1)
    return {
        "code": code,
        "name": name,
        "src": src,
        "hy": zt.get("hybk") or "",
        "lbc": lbc,
        "zbc": int(zt.get("zbc") or 0),
        "fbt": int(zt.get("fbt") or 150000),
        "hs": float(zt.get("hs") or 0),
        "zt_days": int((zt.get("zttj") or {}).get("days") or 0) if isinstance(zt.get("zttj"), dict) else 0,
        "zt_ct": int((zt.get("zttj") or {}).get("ct") or 0) if isinstance(zt.get("zttj"), dict) else 0,
        "mv_yi": round(ltsz / 1e8, 2) if ltsz else 0.0,
        "prev": prev,
        "free_float": free,
        "yest_auction_amt": yamt,
        "avg5_lots": a5,
    }


def _build_preopen_bases(pool: list[dict[str, Any]], zb_pool: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    bases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for zt in pool:
        if not is_main_board(zt["c"], zt["n"]):
            continue
        if zt["c"] in seen:
            continue
        seen.add(zt["c"])
        bases.append(_base_from_pool_item(zt, src="zt"))
    for zb in zb_pool or []:
        if not is_main_board(zb["c"], zb["n"]):
            continue
        if zb["c"] in seen:
            continue
        seen.add(zb["c"])
        bases.append(_base_from_pool_item(zb, src="zb"))
    return bases


def preopen_snapshot(mode: str = "weak", top_n: int = 5) -> dict[str, Any]:
    """盘前：缓存昨涨停/炸板底池，用实时盘口 + 走势打分。"""
    now = datetime.now(CST)
    zt_date, pool = latest_zt_date(now)
    zb_date, zb_pool = "", []
    if mode in WEAK_MODES:
        try:
            zb_date, zb_pool = latest_zb_date(now)
        except Exception:  # noqa: BLE001
            zb_pool = []

    cache_key = f"{zt_date}|{zb_date}|{mode in WEAK_MODES}"
    if _BASE_CACHE.get("cache_key") != cache_key or not _BASE_CACHE.get("bases"):
        _BASE_CACHE["cache_key"] = cache_key
        _BASE_CACHE["zt_date"] = zt_date
        _BASE_CACHE["zb_date"] = zb_date
        _BASE_CACHE["bases"] = _build_preopen_bases(pool, zb_pool if mode in WEAK_MODES else None)
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

    if mode in WEAK_MODES:
        per = min(max(top_n, 1), WEAK_TOP_PER_CAT)
        if mode == "yijin2":
            picked = yijin2_select(rows, top_n=per)
            title = "盘前·一进二（兼容）"
        else:
            picked = weak_select(rows, top_n=per)
            title = "盘前·弱转强（首板/一进二/二进三）"
    elif mode == "wr100":
        picked = wr100_select(rows, top_n=min(top_n, WR100_TOP_N))
        title = "盘前·胜率优先"
    elif mode == "baseline":
        picked = sequential_select(rows)
        title = "盘前·原版"
    else:
        picked = optimized_select(rows, top_n=top_n)
        title = "盘前·连板优化"

    categories = _categories_public(picked) if mode in WEAK_MODES else []
    top = [_public_row(r) for r in picked.get("top5", [])]
    if categories:
        top = [r for cat in categories for r in cat["items"]]

    phase = auction_phase(ts)
    return {
        "ok": True,
        "mode": mode,
        "title": title,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "zt_date": zt_date,
        "zb_date": zb_date or None,
        "main_n": len(bases),
        "quoted": len(rows),
        "phase": phase,
        "categories": categories,
        "top": top,
        "pool": [_public_row(r) for r in picked.get("after_numeric", [])[:40]],
        "tip": phase["tip"] + " · 分类：首板 / 一进二 / 二进三。研究用，不构成投资建议。",
    }


STRATEGIES = [
    {
        "id": "weak",
        "name": "竞价弱转强",
        "desc": "9:30前主策略（回测满仓持股3日冲高胜率）：一进二/二进三收紧；首板仅观察。每类最多1只",
    },
    {
        "id": "wr100",
        "name": "高开止盈",
        "desc": "竞价涨幅3%~4.5%，昨换手≤10%；开盘后 +0.8% 止盈（与弱转强不同）",
    },
    {
        "id": "optimized",
        "name": "连板优化",
        "desc": "收紧量比/金额比，加高度·炸板·市值，综合分排序 Top5",
    },
    {
        "id": "baseline",
        "name": "原版公式",
        "desc": "原始「竞价涨停取反」条件",
    },
]

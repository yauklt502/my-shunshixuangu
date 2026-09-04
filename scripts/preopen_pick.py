#!/usr/bin/env python3
"""09:15–09:25 盘前选股：轮询竞价盘口，按走势 + 连板优化规则出标的。

用法:
  python scripts/preopen_pick.py              # 单次快照（适合 9:25 后）
  python scripts/preopen_pick.py --watch      # 09:15 起轮询，09:25 锁定
  python scripts/preopen_pick.py --watch --once-after 92500

研究用，不构成投资建议。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from auction_screener.fetch import (  # noqa: E402
    CST,
    auction_from_trends,
    fetch_live_quotes,
    fetch_trends,
    latest_zt_date,
)
from auction_screener.rules import (  # noqa: E402
    is_auction_limit_up,
    is_main_board,
    optimized_select,
    turnover_pct,
    vol_over_free,
    vol_ratio,
)
from auction_screener.trajectory import (  # noqa: E402
    AuctionTick,
    TrajectoryState,
    hhmmss_from_str,
    score_trajectory,
)


def now_hhmmss(now: datetime | None = None) -> int:
    now = now or datetime.now(CST)
    return now.hour * 10000 + now.minute * 100 + now.second


def zt_prev_close(zt: dict[str, Any]) -> float:
    p = float(zt.get("p") or 0)
    if p > 1000:
        return p / 1000.0
    return p


def build_base_rows(pool: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """昨涨停主板池 + 昨日竞价额/均量（用于金额比、量比）。"""
    cands = [x for x in pool if is_main_board(x["c"], x["n"])]
    rows: list[dict[str, Any]] = []
    yest_amt: dict[str, float] = {}
    avg5: dict[str, float] = {}
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
        yest_amt[code] = yamt
        avg5[code] = a5
        rows.append(
            {
                "code": code,
                "name": name,
                "hy": zt.get("hybk") or "",
                "lbc": int(zt.get("lbc") or 0) or 1,
                "zbc": int(zt.get("zbc") or 0),
                "fbt": int(zt.get("fbt") or 150000),
                "hs": float(zt.get("hs") or 0),
                "mv_yi": round(ltsz / 1e8, 2) if ltsz else 0.0,
                "prev": prev,
                "free_float": free,
                "yest_auction_amt": yamt,
                "avg5_lots": a5,
                "ltsz": ltsz,
            }
        )
        print(f"\rbase {len(rows)}/{len(cands)}", end="", file=sys.stderr)
    print(file=sys.stderr)
    return rows, yest_amt


def merge_quote(
    base: dict[str, Any],
    quote: dict[str, Any],
    traj: dict[str, Any],
    ts: int,
) -> dict[str, Any]:
    prev = float(quote.get("prev") or base.get("prev") or 0)
    px = float(quote.get("px") or quote.get("open") or 0)
    shares = float(quote.get("vol_shares") or 0)
    if shares <= 0 and quote.get("vol_lots"):
        shares = float(quote["vol_lots"]) * 100.0
    lots = shares / 100.0
    amt = float(quote.get("amt") or 0)
    open_pct = (px / prev - 1) * 100 if prev and px else 0.0
    yamt = float(base.get("yest_auction_amt") or 0)
    free = float(base.get("free_float") or 0)
    row = dict(base)
    row.update(
        {
            "open": round(px, 3),
            "open_pct": round(open_pct, 2),
            "is_auction_zt": is_auction_limit_up(px, prev, base["code"], base["name"]),
            "auction_shares": shares,
            "auction_lots": lots,
            "auction_amt": amt,
            "amt_ratio": round((amt / yamt) if yamt else 0.0, 3),
            "vol_ratio": round(vol_ratio(lots, float(base.get("avg5_lots") or 0)), 2),
            "turnover": round(turnover_pct(shares, free), 4),
            "vol_over_free": vol_over_free(shares, free),
            "traj_score": traj.get("traj_score", 0),
            "traj_label": traj.get("traj_label", ""),
            "traj_detail": traj.get("detail", {}),
            "snapshot_ts": ts,
        }
    )
    return row


def pick_once(
    bases: list[dict[str, Any]],
    states: dict[str, TrajectoryState],
    *,
    top_n: int,
) -> dict[str, list[dict[str, Any]]]:
    codes = [b["code"] for b in bases]
    quotes = fetch_live_quotes(codes, prefer="sina")
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
        tick_ts = ts
        if q.get("time"):
            tick_ts = hhmmss_from_str(str(q["time"])) or ts
        tick = AuctionTick(
            ts=tick_ts,
            px=px,
            prev_close=prev,
            vol_shares=float(q.get("vol_shares") or 0),
            amt=float(q.get("amt") or 0),
            bid1_vol=float(q.get("bid1_vol") or 0),
            bid1_px=float(q.get("bid1_px") or 0),
            ask1_vol=float(q.get("ask1_vol") or 0),
            ask1_px=float(q.get("ask1_px") or 0),
        )
        st = states.setdefault(code, TrajectoryState())
        st.add(tick)
        traj = score_trajectory(st)
        rows.append(merge_quote(base, q, traj, tick_ts))
    return optimized_select(rows, top_n=top_n)


def render(picked: dict[str, list[dict[str, Any]]], meta: dict[str, Any]) -> str:
    lines = [
        f"盘前竞价选股  {meta['generated_at']}  ts={meta.get('ts')}",
        f"昨涨停 {meta['zt_date']}  主板候选 {meta['main_n']}  本轮有效报价 {meta['quoted']}",
        "",
    ]
    if meta.get("phase") == "pre920":
        lines.append("【09:20前】仅观察，不作为最终下单依据")
        lines.append("")
    top = picked["top5"]
    if not top:
        lines.append("（当前无过线标的）")
    for i, r in enumerate(top, 1):
        lines.append(
            f"{i}. {r['name']} {r['code']}  {r['open_pct']:+.2f}%  "
            f"分{r.get('score', 0):.1f}  {r.get('traj_label', '')}  "
            f"量{r['auction_shares']/1e4:.0f}万  量比{r['vol_ratio']:.1f}  "
            f"额比{r['amt_ratio']:.2f}  {r.get('lbc', '?')}板"
        )
        if r.get("reasons"):
            lines.append("   " + "；".join(r["reasons"][:7]))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="竞价时段轮询")
    parser.add_argument("--interval", type=float, default=15.0, help="轮询间隔秒")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument(
        "--lock-after",
        type=int,
        default=92500,
        help="该时刻后输出最终锁定结果并退出（watch 模式）",
    )
    parser.add_argument(
        "--start-after",
        type=int,
        default=91500,
        help="该时刻前等待（watch 模式）",
    )
    args = parser.parse_args()

    now = datetime.now(CST)
    zt_date, pool = latest_zt_date(now)
    print(f"加载昨涨停池 {zt_date} …", file=sys.stderr)
    bases, _ = build_base_rows(pool)
    states: dict[str, TrajectoryState] = {}
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    def run_round() -> dict[str, Any]:
        ts = now_hhmmss()
        picked = pick_once(bases, states, top_n=args.top)
        meta = {
            "generated_at": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S"),
            "zt_date": zt_date,
            "main_n": len(bases),
            "quoted": len(picked.get("universe") or []),
            "ts": ts,
            "phase": "pre920" if ts < 92000 else ("decision" if ts < 92500 else "locked"),
        }
        text = render(picked, meta)
        print(text)
        stamp = datetime.now(CST).strftime("%Y%m%d")
        payload = {**meta, "top5": picked["top5"], "after_numeric": picked.get("after_numeric", [])}
        (out_dir / f"preopen-pick-{stamp}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out_dir / "preopen-pick-latest.txt").write_text(text, encoding="utf-8")
        return {"meta": meta, "picked": picked}

    if not args.watch:
        run_round()
        return 0

    print(
        f"watch 模式：{args.start_after} 后采样，{args.lock_after} 锁定，间隔 {args.interval}s",
        file=sys.stderr,
    )
    while True:
        ts = now_hhmmss()
        if ts < args.start_after:
            time.sleep(min(args.interval, 5))
            continue
        result = run_round()
        if result["meta"]["ts"] >= args.lock_after:
            print("已到锁定时刻，输出最终 Top。", file=sys.stderr)
            break
        # 非交易日/盘后：跑一轮就退，避免空转
        if ts >= 93000 or ts < 90000:
            print("非竞价决策窗，结束 watch。", file=sys.stderr)
            break
        time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

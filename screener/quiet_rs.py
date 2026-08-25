#!/usr/bin/env python3
"""Scan A-shares for quiet grind names that stay green on index-down days.

Usage:
  python3 -m screener.quiet_rs
  python3 -m screener.quiet_rs --index sh000001 --days 15 --top 30
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from screener.fetch import fetch_a_share_snapshot, fetch_index_returns, fetch_klines_many, tencent_symbol
from screener.rules import (
    INDEX_DOWN_PCT,
    TURN_MAX_PCT,
    TURN_MIN_PCT,
    board_limit_pct,
    evaluate_quiet_rs,
    snapshot_today_quiet,
)

ROOT = Path(__file__).resolve().parents[1]


def _circ_shares(row: dict) -> float:
    try:
        px = float(row.get("trade") or 0)
        nmc = float(row.get("nmc") or 0)
    except (TypeError, ValueError):
        return 0.0
    if px <= 0 or nmc <= 0:
        return 0.0
    return nmc * 10000.0 / px


def _is_st(name: str) -> bool:
    n = name.upper()
    return "ST" in n or "退" in name


def keep_snapshot(row: dict) -> bool:
    name = str(row.get("name") or "")
    code = str(row.get("code") or "")
    symbol = str(row.get("symbol") or "")
    if _is_st(name):
        return False
    if symbol.startswith("bj") or code.startswith(("920", "430", "8")):
        return False
    try:
        px = float(row.get("trade") or 0)
        turn = float(row.get("turnoverratio") or 0)
        nmc = float(row.get("nmc") or 0)
    except (TypeError, ValueError):
        return False
    if not (3.0 <= px <= 250.0):
        return False
    # 流通市值 nmc 单位：万元。15 亿 = 150000
    if nmc < 150000:
        return False
    # 预筛：换手不能像游资票。稍放宽以免把窗口内安静、今日略放量的票切掉。
    if turn > 8.0:
        return False
    return True


def load_snapshot(cache: Path | None) -> list[dict]:
    if cache and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    rows = fetch_a_share_snapshot()
    if not rows:
        fallback = Path("/tmp/a_codes.json")
        if fallback.exists():
            rows = json.loads(fallback.read_text(encoding="utf-8"))
    if cache and rows:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def run(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_snap = Path(args.snapshot_cache) if args.snapshot_cache else None
    print(f"index={args.index} window={args.days} workers={args.workers}", flush=True)
    snapshot = load_snapshot(cache_snap)
    if not snapshot:
        print("failed to fetch Sina snapshot", file=sys.stderr)
        return 1
    universe = [r for r in snapshot if keep_snapshot(r)]
    print(f"snapshot={len(snapshot)} universe={len(universe)}", flush=True)

    index_ret = fetch_index_returns(args.index, n=max(40, args.days + 10))
    down_dates = sorted(d for d, r in index_ret.items() if r <= INDEX_DOWN_PCT)
    print(f"index down days (all fetched): {down_dates[-8:]}", flush=True)

    symbols = []
    meta = {}
    for r in universe:
        code = str(r["code"]).zfill(6)
        symbol = tencent_symbol(code, r.get("symbol"))
        symbols.append(symbol)
        meta[symbol] = r

    kcache = Path(args.kline_cache) if args.kline_cache else None

    def prog(done, total, errors):
        print(f"  kline {done}/{total} err={errors}", flush=True)

    bars_map = fetch_klines_many(
        symbols,
        n=max(36, args.days + 8),
        workers=args.workers,
        progress=prog,
        cache_dir=kcache,
    )
    print(f"klines ok={len(bars_map)}", flush=True)

    hits = []
    today_hits = []
    last_index_d = max(index_ret) if index_ret else ""
    last_index_ret = index_ret.get(last_index_d, 0.0)

    for symbol, bars in bars_map.items():
        row = meta[symbol]
        name = str(row.get("name") or "")
        code = str(row.get("code") or "").zfill(6)
        circ = _circ_shares(row)
        if circ <= 0:
            continue
        limit = board_limit_pct(code, name)
        m = evaluate_quiet_rs(
            bars,
            index_ret,
            circ_shares=circ,
            limit_pct=limit,
            window=args.days,
        )
        rec = {
            "code": code,
            "name": name,
            "symbol": symbol,
            "price": float(row.get("trade") or 0),
            "today_pct": float(row.get("changepercent") or 0),
            "nmc_yi": round(float(row.get("nmc") or 0) / 10000.0, 2),
            "limit_pct": limit,
            **{k: getattr(m, k) for k in [
                "ok", "reason", "score", "window_ret_pct", "up_day_ratio",
                "avg_up_pct", "max_up_pct", "avg_turn_pct", "median_turn_pct",
                "last_turn_pct", "vol_ratio", "max_dd_pct", "rs_up_rate",
                "rs_mean_pct", "rs_excess_pct", "down_days", "up_on_down",
            ]},
            "down_day_detail": m.down_day_detail,
        }
        if m.ok:
            hits.append(rec)
        try:
            today_ret = float(row.get("changepercent") or 0)
            today_turn = float(row.get("turnoverratio") or 0)
        except (TypeError, ValueError):
            today_ret, today_turn = 0.0, 0.0
        if snapshot_today_quiet(
            stock_ret_pct=today_ret,
            index_ret_pct=last_index_ret,
            turnover_pct_today=today_turn,
            limit_pct=limit,
        ):
            today_hits.append(rec)

    hits.sort(key=lambda x: (-x["score"], -x["rs_excess_pct"]))
    today_hits.sort(key=lambda x: (-x.get("score") or 0, -x["today_pct"]))

    payload = {
        "index": args.index,
        "window": args.days,
        "last_index_day": last_index_d,
        "last_index_ret_pct": round(last_index_ret, 2),
        "universe": len(universe),
        "hits": hits[: args.top],
        "hit_count": len(hits),
        "today_quiet_if_index_down": today_hits[: args.top],
        "today_count": len(today_hits),
    }
    json_path = out_dir / "quiet-rs-latest.json"
    csv_path = out_dir / "quiet-rs-latest.csv"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = [
        "code", "name", "price", "today_pct", "score", "window_ret_pct",
        "rs_up_rate", "rs_mean_pct", "rs_excess_pct", "avg_up_pct", "max_up_pct",
        "avg_turn_pct", "last_turn_pct", "vol_ratio", "max_dd_pct", "up_day_ratio",
        "nmc_yi", "up_on_down", "down_days",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in hits[: args.top]:
            w.writerow(row)

    print(f"\nhits={len(hits)} top{args.top} -> {csv_path}")
    print(f"today index {last_index_d} {last_index_ret:+.2f}% ; today-quiet={len(today_hits)}")
    print(f"{'code':<8} {'name':<8} {'sc':>6} {'win%':>7} {'rsU':>5} {'rsμ':>6} {'ex':>6} {'upμ':>5} {'toμ':>5} {'dd':>6}")
    for row in hits[: min(20, args.top)]:
        print(
            f"{row['code']:<8} {row['name']:<8} {row['score']:6.1f} {row['window_ret_pct']:7.2f} "
            f"{row['rs_up_rate']:5.2f} {row['rs_mean_pct']:6.2f} {row['rs_excess_pct']:6.2f} "
            f"{row['avg_up_pct']:5.2f} {row['avg_turn_pct']:5.2f} {row['max_dd_pct']:6.2f}"
        )
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Quiet relative-strength A-share scan")
    p.add_argument("--index", default="sh000300", help="sh000300 / sh000001 / sz399006")
    p.add_argument("--days", type=int, default=15)
    p.add_argument("--top", type=int, default=40)
    p.add_argument("--workers", type=int, default=16)
    p.add_argument("--out", default=str(ROOT / "analysis" / "data"))
    p.add_argument("--snapshot-cache", default=str(ROOT / "analysis" / "data" / "cache" / "snapshot.json"))
    p.add_argument("--kline-cache", default=str(ROOT / "analysis" / "data" / "cache" / "kline"))
    args = p.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

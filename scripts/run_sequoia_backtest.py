#!/usr/bin/env python3
"""Run Sequoia-X V2 strategy backtests and write docs/sequoia_x_backtest.md."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sequoia_backtest.backtest import buy_hold_index, evaluate_strategy, next_open_tradable
from sequoia_backtest.data import ensure_data
from sequoia_backtest.report import plot_equity, render_markdown
from sequoia_backtest.signals import STRATEGY_NAMES, compute_all_signals, pivot_ohlcv


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest Sequoia-X V2 strategies")
    parser.add_argument("--download", action="store_true", help="Force re-download from baostock")
    parser.add_argument("--start", default="2024-01-02", help="Evaluation start date")
    parser.add_argument("--end", default="2026-08-04", help="Evaluation end date (leave room for 20d forward)")
    parser.add_argument("--data-start", default="2023-01-01")
    parser.add_argument("--data-end", default="2026-09-01")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--hold-days", type=int, default=5)
    args = parser.parse_args()

    print("loading data...", flush=True)
    ohlcv, meta_df, index_df = ensure_data(
        start=args.data_start,
        end=args.data_end,
        workers=args.workers,
        force=args.download,
    )
    print(
        f"ohlcv rows={len(ohlcv)} symbols={ohlcv['symbol'].nunique()} "
        f"dates={ohlcv['date'].min().date()}..{ohlcv['date'].max().date()}",
        flush=True,
    )

    panels = pivot_ohlcv(ohlcv)
    print("computing signals...", flush=True)
    signals = compute_all_signals(ohlcv)
    tradable = next_open_tradable(panels)

    results = []
    for name in STRATEGY_NAMES:
        print(f"evaluating {name}...", flush=True)
        r = evaluate_strategy(
            name,
            signals[name],
            panels,
            tradable,
            start=args.start,
            end=args.end,
            hold_days=args.hold_days,
        )
        print(
            f"  raw={r.n_raw_signals} trades={r.n_trades} "
            f"nav={r.portfolio['end_nav']:.3f} dd={r.portfolio['max_drawdown']:.2%}",
            flush=True,
        )
        results.append(r)

    hs300_eq, hs300_stats = buy_hold_index(index_df, args.start, args.end)
    out_dir = ROOT / "output"
    docs_dir = ROOT / "docs"
    plot_equity(results, hs300_eq, out_dir / "sequoia_x_equity.png")
    # copy chart next to markdown for relative image path
    import shutil

    docs_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out_dir / "sequoia_x_equity.png", docs_dir / "sequoia_x_equity.png")

    meta = {
        "eval_start": args.start,
        "eval_end": args.end,
        "data_start": str(ohlcv["date"].min().date()),
        "data_end": str(ohlcv["date"].max().date()),
        "n_symbols": int(ohlcv["symbol"].nunique()),
    }
    render_markdown(results, hs300_stats, meta, docs_dir / "sequoia_x_backtest.md")

    summary = {
        "meta": meta,
        "hs300": hs300_stats,
        "strategies": {
            r.name: {
                "n_raw_signals": r.n_raw_signals,
                "n_trades": r.n_trades,
                "event": r.event,
                "portfolio": r.portfolio,
            }
            for r in results
        },
    }
    (out_dir / "sequoia_x_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"wrote {docs_dir / 'sequoia_x_backtest.md'}", flush=True)


if __name__ == "__main__":
    main()

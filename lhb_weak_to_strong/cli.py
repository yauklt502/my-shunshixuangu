#!/usr/bin/env python3
"""CLI for 龙虎榜弱转强分析."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lhb_weak_to_strong.analyze import analyze_trade_date, run_backtest_summary
from lhb_weak_to_strong.report import write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="龙虎榜净买入 · 弱转强买入分析")
    parser.add_argument("--date", required=True, help="交易日 YYYY-MM-DD 或 YYYYMMDD")
    parser.add_argument("--out", default="", help="HTML 输出路径")
    parser.add_argument("--json-out", default="", help="JSON 输出路径")
    parser.add_argument("--no-seats", action="store_true", help="不拉取营业部席位（更快）")
    parser.add_argument("--no-cache", action="store_true", help="禁用本地缓存")
    parser.add_argument("--min-net", type=float, default=0.0, help="净买额下限（元）")
    parser.add_argument("--min-ratio", type=float, default=0.0, help="净买占比下限（%%）")
    parser.add_argument(
        "--backtest-from",
        default="",
        help="附加回测起始日，例如 2026-07-01",
    )
    parser.add_argument("--backtest-to", default="", help="附加回测结束日，默认=分析日")
    args = parser.parse_args(argv)

    result = analyze_trade_date(
        args.date,
        enrich_seats=not args.no_seats,
        use_cache=not args.no_cache,
        min_net=args.min_net,
        min_ratio=args.min_ratio,
    )

    backtest = None
    if args.backtest_from:
        backtest = run_backtest_summary(
            args.backtest_from,
            args.backtest_to or args.date,
            use_cache=not args.no_cache,
        )

    date = result["trade_date"]
    reports_dir = ROOT / "reports"
    out = Path(args.out) if args.out else reports_dir / f"lhb-weak-to-strong-{date}.html"
    write_report(result, out, backtest=backtest)

    json_path = Path(args.json_out) if args.json_out else reports_dir / f"lhb-weak-to-strong-{date}.json"
    payload = {"result": result, "backtest": backtest}
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    # Also refresh reports index
    index = reports_dir / "index.html"
    index.write_text(
        f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/><title>龙虎榜弱转强报告</title>
<style>
body{{font-family:sans-serif;max-width:720px;margin:40px auto;padding:0 16px;background:#111;color:#eee}}
a{{color:#f0c14b}} li{{margin:8px 0}}
</style></head><body>
<h1>龙虎榜弱转强报告索引</h1>
<ul>
<li><a href="lhb-weak-to-strong-{date}.html">{date} 分析</a></li>
<li><a href="lhb-weak-to-strong-2026-08-03.html">2026-08-03 锚定案例</a></li>
</ul>
<p>运行：<code>python3 -m lhb_weak_to_strong.cli --date YYYY-MM-DD --backtest-from 2026-07-01</code></p>
</body></html>
""",
        encoding="utf-8",
    )

    print(f"[ok] {date} candidates={result.get('cluster_count')} html={out} json={json_path}")
    for c in result.get("candidates") or []:
        print(
            f"  [{c.get('tier')}] {c.get('code')} {c.get('name')} "
            f"score={c.get('score')} chg={c.get('chg'):+.2f}% "
            f"net={c.get('net')/1e8:.2f}亿 t1={c.get('t1')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

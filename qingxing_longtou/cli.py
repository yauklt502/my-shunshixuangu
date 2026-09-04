#!/usr/bin/env python3
"""命令行模式：便于无 GUI 环境验证策略与数据源。"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from engine.strategy import StrategyParams, run_strategy
from sources import get_source, source_status
from sources.eastmoney import beijing_ymd


def main() -> int:
    parser = argparse.ArgumentParser(description="清醒龙头战法 CLI")
    parser.add_argument("--source", default="auto", help="auto|eastmoney|tonghuashun|tdx")
    parser.add_argument("--date", default="", help="YYYYMMDD，默认今天(北京)")
    parser.add_argument("--top-boards", type=int, default=12)
    parser.add_argument("--status", action="store_true", help="仅打印数据源状态")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--csv", dest="csv_path", default="", help="导出 CSV 路径")
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()

    if args.status:
        print(json.dumps(source_status(), ensure_ascii=False, indent=2))
        return 0

    source = get_source(args.source)
    snap = source.fetch_snapshot(args.date or beijing_ymd())
    rows = run_strategy(snap, StrategyParams(top_boards=args.top_boards))[: args.limit]

    if args.csv_path:
        path = Path(args.csv_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(rows[0].to_row().keys()) if rows else [
            "关注", "评级", "代码", "名称", "板块", "涨幅%", "现价", "连板", "封板", "得分", "标签", "要点", "弱势信号", "数据源"
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r.to_row())
        print(f"wrote {path} ({len(rows)} rows) source={source.label} date={snap.trade_date}")
        return 0

    if args.json:
        payload = {
            "source": source.label,
            "trade_date": snap.trade_date,
            "notes": snap.notes,
            "candidates": [r.to_row() for r in rows],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"[{source.label}] {snap.trade_date}  candidates={len(rows)}")
    for n in snap.notes:
        print(f"  note: {n}")
    for r in rows:
        row = r.to_row()
        print(
            f"{row['关注']:2} {row['评级']:8} {row['代码']} {row['名称']:8} "
            f"{row['板块']:10} {row['涨幅%']!s:>7} 得分{row['得分']}  {row['标签']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

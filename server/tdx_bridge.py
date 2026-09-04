#!/usr/bin/env python3
"""Thin JSON CLI bridge for eltdx when the HTTP gateway is not running.

Usage:
  python3 server/tdx_bridge.py kline --code sz000001 --period day --count 120
  python3 server/tdx_bridge.py minute --code sz000001
  python3 server/tdx_bridge.py minute --code sz000001 --date 20260903
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def _client(host: str, timeout: float):
    from eltdx import TdxClient

    return TdxClient(host=host, timeout=timeout)


def _bars_payload(series) -> dict:
    return {
        "code": series.code,
        "exchange": series.exchange,
        "period": series.period_name,
        "bars": [
            {
                "time": bar.time.isoformat() if bar.time is not None else None,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume_lots,
                "amount": bar.amount,
                "last_close": (bar.last_close_price_milli or 0) / 1000 if bar.last_close_price_milli else None,
            }
            for bar in series.bars
        ],
    }


def _minute_payload(series) -> dict:
    return {
        "code": series.code,
        "exchange": series.exchange,
        "trading_date": series.trading_date,
        "prev_close": series.prev_close,
        "points": [
            {
                "time": point.time_label,
                "price": point.price,
                "avg": point.avg_price,
                "volume": point.volume,
            }
            for point in series.points
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["kline", "minute"])
    parser.add_argument("--code", required=True)
    parser.add_argument("--period", default="day")
    parser.add_argument("--count", type=int, default=120)
    parser.add_argument("--date", default="")
    parser.add_argument("--host", default=os.environ.get("TDX_HOST", "115.238.90.165:7709"))
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("TDX_TIMEOUT", "8")))
    args = parser.parse_args()

    try:
        client = _client(args.host, args.timeout)
        if args.action == "kline":
            series = client.bars.get(args.code, period=args.period, count=args.count, adjust="qfq")
            payload = _bars_payload(series)
        else:
            if args.date:
                series = client.minutes.history(args.code, args.date)
            else:
                series = client.minutes.today(args.code)
            payload = _minute_payload(series)
        print(json.dumps({"ok": True, "result": payload}, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "errmsg": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Smoke-test Fuyao REST access. Requires FUYAO_API_KEY in env or .env."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from fuyao import FuyaoClient, FuyaoError


def _print(title: str, data: object) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(data, ensure_ascii=False, indent=2)[:1200])


def main() -> int:
    if not (os.environ.get("FUYAO_API_KEY") or os.environ.get("API_KEY")):
        print("Missing FUYAO_API_KEY. Copy .env.example → .env and fill the key.", file=sys.stderr)
        return 2

    client = FuyaoClient()

    try:
        search = client.search_tickers("贵州茅台", limit=3)
        _print("ticker search", search)

        thscode = search["item"][0]["thscode"]
        snap = client.prices_snapshot(thscode)
        _print(f"snapshot {thscode}", snap)

        days = client.trading_days()
        _print("trading days (truncated)", {"count": len(days.get("item") or days.get("items") or []), "sample": (days.get("item") or days.get("items") or [])[:3]})

        hot = client.hot_stock_list()
        _print("hot stock list", hot)

        ladder = client.limit_up_ladder()
        _print("limit-up ladder", ladder)
    except FuyaoError as exc:
        print(f"Fuyao business error: code={exc.code} request_id={exc.request_id} {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    print("\nOK — Fuyao API key and endpoints look healthy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

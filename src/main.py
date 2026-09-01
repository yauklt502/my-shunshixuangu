"""Main trading system orchestrator."""

from __future__ import annotations

import argparse
import json
import logging

from src.backtest import BacktestRunner
from src.common import AppConfig, BarPeriod, Environment

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_backtest(symbol: str = "000001", limit: int = 200) -> None:
    config = AppConfig(environment=Environment.BACKTEST)
    runner = BacktestRunner(config)
    runner.register_default_strategies()
    signals = runner.run(symbol=symbol, period=BarPeriod.DAILY, limit=limit)
    logger.info("Backtest complete: %d signals generated", len(signals))
    print(json.dumps(signals[:10], ensure_ascii=False, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="顺时选股交易系统")
    parser.add_argument("--mode", choices=["backtest", "live"], default="backtest")
    parser.add_argument("--symbol", default="000001")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    if args.mode == "backtest":
        run_backtest(args.symbol, args.limit)
    else:
        logger.warning("Live mode requires broker credentials — use LiveExecutor with broker adapter")


if __name__ == "__main__":
    main()

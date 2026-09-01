"""Main trading system orchestrator."""

from __future__ import annotations

import argparse
import json
import logging
import time

from src.backtest import BacktestRunner
from src.common import AppConfig, BarPeriod, Environment
from src.live import LiveRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_backtest(symbol: str = "000001", limit: int = 200) -> None:
    config = AppConfig(environment=Environment.BACKTEST)
    runner = BacktestRunner(config)
    runner.register_default_strategies()
    signals = runner.run(symbol=symbol, period=BarPeriod.DAILY, limit=limit)
    logger.info("Backtest complete: %d signals generated", len(signals))
    print(json.dumps(signals[:10], ensure_ascii=False, indent=2, default=str))


def run_live(symbols: list[str], poll_interval: float = 5.0) -> None:
    config = AppConfig(environment=Environment.LIVE)
    config.live.symbols = symbols
    config.live.poll_interval_seconds = poll_interval

    runner = LiveRunner(config, on_event=lambda t, d: logger.info("Event [%s]: %s", t, d))
    runner.register_default_strategies()
    runner.start(symbols)
    logger.info("Live mode started (broker=%s). Press Ctrl+C to stop.", config.broker.broker_type)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        runner.stop()
        logger.info("Live mode stopped")


def run_api(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn

    from src.api import app

    logger.info("Starting API server at http://%s:%d", host, port)
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    parser = argparse.ArgumentParser(description="顺时选股交易系统")
    parser.add_argument("--mode", choices=["backtest", "live", "api"], default="backtest")
    parser.add_argument("--symbol", default="000001")
    parser.add_argument("--symbols", default="000001", help="Live mode: comma-separated symbols")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.mode == "backtest":
        run_backtest(args.symbol, args.limit)
    elif args.mode == "live":
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
        run_live(symbols, args.poll_interval)
    else:
        run_api(args.host, args.port)


if __name__ == "__main__":
    main()

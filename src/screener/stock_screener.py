"""Strategy-based stock screener."""

from __future__ import annotations

import logging
from typing import List, Optional

from src.common import BarPeriod, Environment, SignalType
from src.compute import IndicatorPreprocessor
from src.data_source.eastmoney_adapter import EastmoneyAdapter
from src.data_source.pipeline import DataPipeline, get_active_source
from src.strategy.registry import STRATEGY_LABELS, get_strategy

logger = logging.getLogger(__name__)

# Fallback universe when market API unavailable
DEFAULT_UNIVERSE = [
    {"code": "000001", "name": "平安银行", "change_pct": 0},
    {"code": "600519", "name": "贵州茅台", "change_pct": 0},
    {"code": "300750", "name": "宁德时代", "change_pct": 0},
    {"code": "002594", "name": "比亚迪", "change_pct": 0},
    {"code": "601318", "name": "中国平安", "change_pct": 0},
    {"code": "600036", "name": "招商银行", "change_pct": 0},
    {"code": "000858", "name": "五粮液", "change_pct": 0},
    {"code": "601012", "name": "隆基绿能", "change_pct": 0},
    {"code": "002475", "name": "立讯精密", "change_pct": 0},
    {"code": "300059", "name": "东方财富", "change_pct": 0},
    {"code": "601888", "name": "中国中免", "change_pct": 0},
    {"code": "000333", "name": "美的集团", "change_pct": 0},
    {"code": "600900", "name": "长江电力", "change_pct": 0},
    {"code": "002415", "name": "海康威视", "change_pct": 0},
    {"code": "601166", "name": "兴业银行", "change_pct": 0},
]


def get_universe(limit: int = 80) -> List[dict]:
    try:
        stocks = EastmoneyAdapter().fetch_stock_list(limit=limit)
        if stocks:
            return stocks
    except Exception as e:
        logger.warning("Fetch universe failed: %s", e)
    return DEFAULT_UNIVERSE[:limit]


def screen_by_strategy(
    strategy_id: str,
    period: BarPeriod = BarPeriod.DAILY,
    bar_limit: int = 80,
    universe_limit: int = 60,
    symbols: Optional[List[str]] = None,
) -> dict:
    strategy = get_strategy(strategy_id)
    if not strategy:
        return {"ok": False, "message": f"未知策略: {strategy_id}", "results": []}

    if symbols:
        universe = [{"code": s, "name": s, "change_pct": 0} for s in symbols]
    else:
        universe = get_universe(universe_limit)

    pipeline = DataPipeline(Environment.BACKTEST, primary=get_active_source())
    preprocessor = IndicatorPreprocessor()
    results: List[dict] = []

    for item in universe:
        code = item["code"]
        try:
            bars = pipeline.get_historical(code, period, limit=bar_limit)
            if len(bars) < 10:
                continue
            enriched = preprocessor.process(bars, use_cache=False)
            sig = strategy.on_bar(enriched, len(enriched) - 1)
            if sig.signal == SignalType.OPEN_LONG:
                results.append(
                    {
                        "symbol": code,
                        "name": item.get("name", code),
                        "price": round(sig.price, 2),
                        "change_pct": round(float(item.get("change_pct", 0)), 2),
                        "reason": sig.reason,
                        "strategy_id": strategy_id,
                        "strategy_name": STRATEGY_LABELS.get(strategy_id, strategy_id),
                        "signal": sig.signal.value,
                    }
                )
        except Exception as e:
            logger.debug("Screen skip %s: %s", code, e)
            continue

    return {
        "ok": True,
        "strategy_id": strategy_id,
        "strategy_name": STRATEGY_LABELS.get(strategy_id, strategy_id),
        "scanned": len(universe),
        "count": len(results),
        "results": results,
    }

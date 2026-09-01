"""FastAPI server: REST + WebSocket for dashboard and live trading."""

from __future__ import annotations

import asyncio
import json
import logging
import queue
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.backtest import BacktestRunner
from src.common import AppConfig, BarPeriod, Environment
from src.data_source.market import get_klines, get_market_overview, get_quote
from src.data_source.market import check_data_source_health
from src.data_source.pipeline import get_active_source, list_sources, set_active_source
from src.live import LiveRunner
from src.screener import screen_by_strategy
from src.strategy.registry import STRATEGY_LABELS

logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(title="顺时选股 API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_live_runner: LiveRunner | None = None
_ws_clients: Set[WebSocket] = set()
_event_queue: queue.Queue = queue.Queue()


class BacktestRequest(BaseModel):
    symbol: str = "000001"
    limit: int = 200
    period: str = "daily"
    data_source: str | None = None


class LiveStartRequest(BaseModel):
    symbols: list[str] = ["000001"]
    poll_interval: float = 5.0
    period: str = "daily"
    data_source: str | None = None


class DataSourceRequest(BaseModel):
    source: str


class ScreenRequest(BaseModel):
    strategy_id: str = "ma5_climb"
    period: str = "daily"
    bar_limit: int = 80
    universe_limit: int = 60
    data_source: str | None = None


async def _broadcast_ws(event_type: str, data: dict) -> None:
    payload = json.dumps({"type": event_type, "data": data}, ensure_ascii=False, default=str)
    dead: Set[WebSocket] = set()
    for ws in list(_ws_clients):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


async def _poll_event_queue() -> None:
    while True:
        try:
            event_type, data = _event_queue.get_nowait()
            await _broadcast_ws(event_type, data)
        except queue.Empty:
            pass
        await asyncio.sleep(0.15)


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(_poll_event_queue())


def _on_live_event(event_type: str, data: dict) -> None:
    _event_queue.put((event_type, data))


@app.get("/")
async def index():
    dashboard = FRONTEND_DIR / "dashboard.html"
    if dashboard.exists():
        return FileResponse(dashboard)
    return {"message": "顺时选股 API", "docs": "/docs"}


@app.get("/api/data/sources")
async def api_list_sources():
    return {"active": get_active_source(), "sources": list_sources()}


@app.post("/api/data/source")
async def api_set_source(req: DataSourceRequest):
    ok = set_active_source(req.source)
    if not ok:
        return {"ok": False, "message": f"未知数据源: {req.source}"}
    health = check_data_source_health(req.source)
    await _broadcast_ws("data_source_changed", {"source": req.source, "health": health})
    return {"ok": True, "active": get_active_source(), "health": health}


@app.get("/api/data/health")
async def api_data_health(source: str | None = None):
    src = source or get_active_source()
    return check_data_source_health(src)


@app.get("/api/market/overview")
async def api_market_overview(source: str | None = None):
    return get_market_overview(source)


@app.get("/api/market/quote/{symbol}")
async def api_market_quote(symbol: str, source: str | None = None):
    q = get_quote(symbol, source)
    if not q:
        return {"ok": False, "message": "无法获取行情"}
    return {"ok": True, "quote": q}


@app.get("/api/market/klines/{symbol}")
async def api_market_klines(symbol: str, period: str = "daily", limit: int = 120, source: str | None = None):
    bars = get_klines(symbol, period, limit, source)
    return {"ok": True, "symbol": symbol, "count": len(bars), "bars": bars}


@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    if req.data_source:
        set_active_source(req.data_source)
    config = AppConfig(environment=Environment.BACKTEST)
    runner = BacktestRunner(config)
    runner.register_default_strategies()
    period = BarPeriod(req.period)
    signals = runner.run(symbol=req.symbol, period=period, limit=req.limit)
    reports = runner.relational.get_backtest_reports()
    latest = reports[0] if reports else {}
    result = {
        "symbol": req.symbol,
        "data_source": get_active_source(),
        "signal_count": len(signals),
        "signals": signals[:50],
        "report": {
            "total_return": latest.get("total_return"),
            "win_rate": latest.get("win_rate"),
            "profit_loss_ratio": latest.get("profit_loss_ratio"),
            "max_drawdown": latest.get("max_drawdown"),
        },
    }
    await _broadcast_ws("backtest_complete", result)
    return result


@app.get("/api/live/status")
async def live_status():
    if _live_runner:
        return _live_runner.status()
    return {"running": False, "data_source": get_active_source()}


@app.post("/api/live/start")
async def live_start(req: LiveStartRequest):
    global _live_runner
    if _live_runner and _live_runner.is_running:
        return {"ok": False, "message": "实盘已在运行"}

    if req.data_source:
        set_active_source(req.data_source)

    config = AppConfig(environment=Environment.LIVE)
    config.live.symbols = req.symbols
    config.live.poll_interval_seconds = req.poll_interval
    config.live.bar_period = req.period

    _live_runner = LiveRunner(config, on_event=_on_live_event)
    _live_runner.register_default_strategies()
    _live_runner.start(req.symbols)
    return {"ok": True, "status": _live_runner.status(), "data_source": get_active_source()}


@app.post("/api/live/stop")
async def live_stop():
    global _live_runner
    if _live_runner:
        _live_runner.stop()
        status = _live_runner.status()
        _live_runner = None
        return {"ok": True, "status": status}
    return {"ok": False, "message": "未在运行"}


@app.get("/api/strategies")
async def list_strategies():
    from src.strategy.registry import get_all_strategies

    return [
        {"id": s.strategy_id, "name": STRATEGY_LABELS.get(s.strategy_id, s.strategy_id)}
        for s in get_all_strategies()
    ]


@app.post("/api/screen")
async def api_screen(req: ScreenRequest):
    if req.data_source:
        set_active_source(req.data_source)
    period = BarPeriod(req.period)
    result = screen_by_strategy(
        strategy_id=req.strategy_id,
        period=period,
        bar_limit=req.bar_limit,
        universe_limit=req.universe_limit,
    )
    await _broadcast_ws("screen_complete", {"count": result.get("count", 0), "strategy_id": req.strategy_id})
    return result


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.add(ws)
    try:
        await ws.send_text(
            json.dumps(
                {
                    "type": "connected",
                    "data": {"clients": len(_ws_clients), "data_source": get_active_source()},
                },
                ensure_ascii=False,
            )
        )
        while True:
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_text(json.dumps({"type": "pong", "data": {"data_source": get_active_source()}}))
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(ws)


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

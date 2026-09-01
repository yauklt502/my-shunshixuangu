"""FastAPI server: REST + WebSocket for dashboard and live trading."""

from __future__ import annotations

import asyncio
import json
import logging
import queue
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.backtest import BacktestRunner
from src.common import AppConfig, BarPeriod, Environment
from src.live import LiveRunner

logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(title="顺时选股 API", version="0.2.0")
_live_runner: LiveRunner | None = None
_ws_clients: Set[WebSocket] = set()
_event_queue: queue.Queue = queue.Queue()


class BacktestRequest(BaseModel):
    symbol: str = "000001"
    limit: int = 200
    period: str = "daily"


class LiveStartRequest(BaseModel):
    symbols: list[str] = ["000001"]
    poll_interval: float = 5.0
    period: str = "daily"


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


@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    config = AppConfig(environment=Environment.BACKTEST)
    runner = BacktestRunner(config)
    runner.register_default_strategies()
    period = BarPeriod(req.period)
    signals = runner.run(symbol=req.symbol, period=period, limit=req.limit)
    reports = runner.relational.get_backtest_reports()
    latest = reports[0] if reports else {}
    result = {
        "symbol": req.symbol,
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
    return {"running": False}


@app.post("/api/live/start")
async def live_start(req: LiveStartRequest):
    global _live_runner
    if _live_runner and _live_runner.is_running:
        return {"ok": False, "message": "实盘已在运行"}

    config = AppConfig(environment=Environment.LIVE)
    config.live.symbols = req.symbols
    config.live.poll_interval_seconds = req.poll_interval
    config.live.bar_period = req.period

    _live_runner = LiveRunner(config, on_event=_on_live_event)
    _live_runner.register_default_strategies()
    _live_runner.start(req.symbols)
    return {"ok": True, "status": _live_runner.status()}


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

    return [{"id": s.strategy_id, "name": s.strategy_id} for s in get_all_strategies()]


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.add(ws)
    try:
        await ws.send_text(json.dumps({"type": "connected", "data": {"clients": len(_ws_clients)}}))
        while True:
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_text(json.dumps({"type": "pong", "data": {}}))
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(ws)


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

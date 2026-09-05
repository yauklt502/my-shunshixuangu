"""10秒定龙头 · 实时服务。"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from dragon.engine import build_snapshot
from dragon.timeutil import market_session

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
REPORT = ROOT / "data" / "backtest_3m.json"

app = FastAPI(title="10秒定龙头", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

_cache: dict[str, tuple[float, dict]] = {}
CACHE_LIVE = 5.0
CACHE_IDLE = 20.0


def _ttl() -> float:
    return CACHE_LIVE if market_session()["live"] else CACHE_IDLE


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/backtest")
async def backtest_page():
    return FileResponse(STATIC / "backtest.html")


@app.get("/api/backtest")
async def backtest_api():
    if not REPORT.exists():
        return {"ok": False, "error": "还没有回测报告，先运行 python3 -m dragon.backtest"}
    return json.loads(REPORT.read_text("utf-8"))


@app.get("/api/health")
async def health():
    return {"ok": True, **market_session(), "app": "10秒定龙头"}


@app.get("/api/snapshot")
async def snapshot(
    date: str | None = Query(default=None, min_length=8, max_length=8),
    mode: str | None = Query(default=None),
):
    key = f"{date or 'auto'}:{mode or 'auto'}"
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < _ttl():
        payload = dict(hit[1])
        payload["cached"] = True
        return payload
    data = await build_snapshot(date, mode)
    data["cached"] = False
    _cache[key] = (now, data)
    return data


@app.post("/api/refresh")
async def refresh(
    date: str | None = Query(default=None),
    mode: str | None = Query(default=None),
):
    key = f"{date or 'auto'}:{mode or 'auto'}"
    _cache.pop(key, None)
    return await snapshot(date, mode)


@app.on_event("startup")
async def warmup():
    async def _run():
        try:
            await build_snapshot()
        except Exception:
            pass

    asyncio.create_task(_run())

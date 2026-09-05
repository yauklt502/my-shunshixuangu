"""10秒定龙头 · 实时服务。"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from dragon.config import PORT
from dragon.engine import build_snapshot
from dragon.pack import build_zip
from dragon.shot import render_png
from dragon.timeutil import market_session

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
REPORT = ROOT / "data" / "backtest_3m.json"

app = FastAPI(title="10秒定龙头", version="1.1.0")
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
    return {"ok": True, **market_session(), "app": "10秒定龙头", "port": PORT}


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


@app.get("/api/shot.png")
async def shot_png(
    date: str | None = Query(default=None, min_length=8, max_length=8),
    mode: str | None = Query(default=None),
):
    data = await snapshot(date, mode)
    raw, fname = render_png(data)
    ascii_name = f"dinglong-{data.get('date') or 'live'}.png"
    headers = {
        "Content-Disposition": (
            f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(fname)}"
        )
    }
    return Response(raw, media_type="image/png", headers=headers)


@app.get("/download.zip")
async def download_zip():
    raw = build_zip()
    headers = {
        "Content-Disposition": "attachment; filename=\"10s-dinglongtou.zip\"; "
        "filename*=UTF-8''10%E7%A7%92%E5%AE%9A%E9%BE%99%E5%A4%B4.zip"
    }
    return Response(raw, media_type="application/zip", headers=headers)


@app.on_event("startup")
async def warmup():
    async def _run():
        try:
            await build_snapshot()
        except Exception:
            pass

    asyncio.create_task(_run())

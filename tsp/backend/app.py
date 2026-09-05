"""先比独 · Tick Stock Panel API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import config
from backend.sources import eastmoney as em
from backend.sources import get_module, source_health
from backend.strategy.xianbidu import recent_trade_dates, score_candidates

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
CN = timezone(timedelta(hours=8))

app = FastAPI(title="先比独 · Tick Stock Panel", version="0.1.0")


def _today() -> str:
    return datetime.now(CN).strftime("%Y%m%d")


@app.get("/api/health")
async def api_health():
    return {
        "ok": True,
        "now": datetime.now(CN).strftime("%Y-%m-%d %H:%M:%S"),
        "tdx_host": config.TDX_HOST,
        "sources": await source_health(),
    }


@app.get("/api/sources")
async def api_sources():
    return {"sources": config.SOURCES, "default": config.DEFAULT_SOURCE}


@app.get("/api/dates")
async def api_dates(limit: int = Query(40, ge=5, le=120)):
    items = recent_trade_dates(limit)
    return {"dates": items, "today": _today(), "default": items[0]["date"] if items else _today()}


@app.get("/api/screen")
async def api_screen(date: str | None = None, source: str = "eastmoney"):
    d = date if date and len(date) == 8 and date.isdigit() else _today()
    warnings: list[str] = []
    used = source
    try:
        bundle = await get_module(source).market_bundle(d)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"{source} 失败：{exc}，已回退东方财富")
        bundle = await em.market_bundle(d)
        used = "eastmoney"
    result = score_candidates(bundle)
    return {
        "ok": True,
        "date": d,
        "source": bundle.get("source") or used,
        "warnings": warnings,
        "hot_boards": result["hot_boards"],
        "leaders": result["leaders"],
        "anchors": result["anchors"],
        "watch": result["watch"],
        "all": result["all"],
        "stats": result["stats"],
        "theory": result["theory"],
        "updated_at": datetime.now(CN).strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.get("/api/panel/{code}")
async def api_panel(code: str, source: str = Query("tdx")):
    code = em.plain(code)
    mod = get_module(source)
    tdx = get_module("tdx")
    out: dict[str, Any] = {"ok": True, "code": code, "source": source}
    errors: list[str] = []

    try:
        out["depth"] = await (mod.depth(code) if hasattr(mod, "depth") else _quote_as_depth(mod, code))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"depth:{exc}")
        try:
            out["depth"] = await tdx.depth(code)
        except Exception as exc2:  # noqa: BLE001
            errors.append(f"depth_tdx:{exc2}")
            out["depth"] = {"code": code, "bids": [], "asks": [], "price": 0, "pre_close": 0}

    try:
        out["day"] = await (tdx.kline(code, "day", 120) if source == "tdx" else mod.kline_day(code, 120))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"day:{exc}")
        try:
            out["day"] = await em.kline_day(code, 120)
        except Exception as exc2:  # noqa: BLE001
            errors.append(f"day_fallback:{exc2}")
            out["day"] = []

    try:
        out["minute"] = await mod.minute_today(code)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"minute:{exc}")
        try:
            out["minute"] = await em.minute_today(code)
        except Exception as exc2:  # noqa: BLE001
            errors.append(f"minute_fallback:{exc2}")
            out["minute"] = {"code": code, "points": [], "pre_close": 0}

    try:
        out["m1"] = await tdx.kline(code, "1min", 240)
        out["m5"] = await tdx.kline(code, "5min", 120)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"intraday:{exc}")
        out["m1"], out["m5"] = [], []

    out["errors"] = errors
    return out


async def _quote_as_depth(mod, code: str) -> dict[str, Any]:
    q = await mod.quotes([code])
    row = q.get(em.plain(code)) or {}
    return {"code": em.plain(code), **row, "bids": [], "asks": []}


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


def main() -> None:
    import uvicorn

    uvicorn.run("backend.app:app", host=config.HOST, port=config.PORT, reload=False)


if __name__ == "__main__":
    main()
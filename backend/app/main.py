from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.providers.registry import registry
from app.services.role_ladder import classify_roles

app = FastAPI(title="顺势选股 Role Ladder", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins) + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "providers": registry.list_providers(), "active": registry.get().name}


@app.get("/api/providers")
def list_providers() -> dict[str, Any]:
    return {"items": registry.list_providers(), "active": registry.get().name}


@app.post("/api/providers/{name}/activate")
def activate_provider(name: str) -> dict[str, Any]:
    try:
        registry.set_active(name)
    except KeyError as e:
        raise HTTPException(404, f"unknown provider: {name}") from e
    return {"ok": True, "active": name, "items": registry.list_providers()}


@app.get("/api/ladder")
def ladder(date: str = Query("", description="YYYY-MM-DD or YYYYMMDD")) -> dict[str, Any]:
    pool_p = registry.pool_provider()
    try:
        pool = pool_p.limit_up_pool(date)
    except Exception as e:
        raise HTTPException(502, f"limit-up pool failed via {pool_p.name}: {e}") from e
    result = classify_roles(pool)
    result["provider"] = pool_p.name
    result["trade_date"] = date or (pool[0].get("trade_date") if pool else "")
    return result


@app.get("/api/quote/{code}")
def quote(code: str) -> dict[str, Any]:
    p = registry.quote_provider()
    try:
        return p.quote(code)
    except Exception as e:
        try:
            return registry.get("eastmoney").quote(code)
        except Exception as e2:
            raise HTTPException(502, f"{e}; fallback: {e2}") from e2


@app.get("/api/depth/{code}")
def depth(code: str) -> dict[str, Any]:
    p = registry.quote_provider()
    try:
        return p.depth(code)
    except Exception:
        return registry.get("eastmoney").depth(code)


@app.get("/api/kline/daily/{code}")
def daily_kline(code: str, count: int = 120) -> dict[str, Any]:
    p = registry.quote_provider()
    try:
        bars = p.daily_bars(code, count=count)
    except Exception:
        bars = registry.get("eastmoney").daily_bars(code, count=count)
    return {"code": code, "bars": bars, "source": p.name}


@app.get("/api/kline/minute/{code}")
def minute_kline(code: str, period: str = "1m") -> dict[str, Any]:
    p = registry.quote_provider()
    try:
        bars = p.minute_bars(code, period=period)
    except Exception:
        bars = registry.get("eastmoney").minute_bars(code, period=period)
    return {"code": code, "period": period, "bars": bars, "source": p.name}


@app.get("/api/intraday/{code}")
def intraday(code: str) -> dict[str, Any]:
    p = registry.quote_provider()
    try:
        points = p.intraday(code)
    except Exception:
        points = registry.get("eastmoney").intraday(code)
    return {"code": code, "points": points, "source": p.name}


@app.get("/api/stock/panel/{code}")
def stock_panel(code: str) -> dict[str, Any]:
    qp = registry.quote_provider()
    ep = registry.get("eastmoney")

    def _safe(fn, fallback=None):
        try:
            return fn()
        except Exception:
            return fallback() if fallback else None

    quote_data = _safe(lambda: qp.quote(code), lambda: ep.quote(code))
    depth_data = _safe(lambda: qp.depth(code), lambda: ep.depth(code))
    daily = _safe(lambda: qp.daily_bars(code, 120), lambda: ep.daily_bars(code, 120)) or []
    intra = _safe(lambda: qp.intraday(code), lambda: ep.intraday(code)) or []
    m1 = _safe(lambda: qp.minute_bars(code, "1m"), lambda: ep.minute_bars(code, "1m")) or []
    m5 = _safe(lambda: qp.minute_bars(code, "5m"), lambda: ep.minute_bars(code, "5m")) or []
    if quote_data:
        quote_data = {
            **quote_data,
            "change_pct": quote_data.get("change_pct") or quote_data.get("change_pct") or 0,
            "pre_close": quote_data.get("pre_close") or quote_data.get("pre_close") or 0,
        }
    if depth_data:
        depth_data = {
            **depth_data,
            "bids": depth_data.get("bids") or [],
            "asks": depth_data.get("asks") or [],
        }
    return {
        "code": code,
        "quote": quote_data,
        "depth": depth_data,
        "daily": daily,
        "daily_bars": daily,
        "intraday": intra,
        "minute_1m": m1,
        "minute_5m": m5,
        "source": getattr(qp, "name", "unknown"),
    }
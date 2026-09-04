"""顺势选股 · 龙头确认实时服务。

- 多数据源可切换：东方财富 / 同花顺 / 通达信(腾讯免费行情)
- 忽略系统代理，避免 Windows 代理掐断行情
- 行情失败时降级，接口仍返回 200
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from strategy.engine import (
    build_candidates,
    build_ladder,
    candidates_to_dict,
    confirm_summary,
    pick_confirmed_leaders,
)
from strategy.providers.market import SOURCES, load_market


def _china_tz():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("Asia/Shanghai")
    except Exception:
        return timezone(timedelta(hours=8), name="CST")


CN = _china_tz()
ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = FastAPI(title="顺势选股 · 龙头确认", version="1.2.0")


def trading_date(override: str | None = None) -> str:
    if override and len(override) == 8 and override.isdigit():
        return override
    return datetime.now(CN).strftime("%Y%m%d")


def market_session(now: datetime | None = None) -> dict:
    now = now or datetime.now(CN)
    t = now.hour * 100 + now.minute
    weekday = now.weekday()
    if weekday >= 5:
        phase = "休市"
    elif t < 915:
        phase = "盘前"
    elif t < 925:
        phase = "集合竞价"
    elif t < 930:
        phase = "竞价撮合"
    elif t < 1130:
        phase = "上午交易"
    elif t < 1300:
        phase = "午间休市"
    elif t < 1500:
        phase = "下午交易"
    else:
        phase = "已收盘"
    return {
        "phase": phase,
        "now": now.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": weekday,
    }


@app.get("/api/health")
async def health():
    return {"ok": True, **market_session(), "sources": list(SOURCES.values())}


@app.get("/api/sources")
async def sources():
    return {"sources": list(SOURCES.values()), "default": "eastmoney"}


@app.get("/api/leader")
async def leader(
    date: str | None = Query(default=None, description="YYYYMMDD"),
    source: str = Query(default="eastmoney", description="eastmoney|tonghuashun|tongdaxin"),
):
    d = trading_date(date)
    session = market_session()
    warnings: list[str] = []

    try:
        market = await load_market(source, d)
    except Exception as e:  # noqa: BLE001
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "date": d,
                "session": session,
                "source": source,
                "error": f"数据源不可用：{e}",
                "warnings": [str(e)],
                "picks": [],
                "candidates": [],
                "ladder": [],
                "failed": [],
                "yizi_anchors": [],
                "confirm": {
                    "verdict": "数据源暂不可用，请切换东财/同花顺/通达信后重试",
                    "yizi_height_note": "",
                    "tradable_height": None,
                    "height_anchor": None,
                    "confirmed_picks": [],
                },
                "stats": {
                    "zt_count": 0,
                    "candidate_count": 0,
                    "zb_count": 0,
                    "yizi_count": 0,
                    "non_yizi_count": 0,
                },
                "strategy": _strategy_block(),
            },
        )

    yesterday = market["yesterday"]
    today_zt = market["today_zt"]
    zb = market["zb"]
    quotes = market["quotes"]
    warnings.extend(market.get("warnings") or [])

    candidates = build_candidates(yesterday, today_zt, quotes, min_prev_boards=2)
    picks = pick_confirmed_leaders(candidates, n=2)
    ladder = build_ladder(today_zt)
    summary = confirm_summary(candidates, ladder, picks)

    failed = [
        c
        for c in candidates
        if not c.sealed and not c.is_yizi and c.prev_boards >= 2
    ][:12]
    yizi_only = [c for c in candidates if c.is_yizi][:8]

    return {
        "ok": True,
        "date": d,
        "session": session,
        "source": market["source"],
        "source_meta": market["source_meta"],
        "warnings": warnings,
        "strategy": _strategy_block(),
        "confirm": summary,
        "picks": candidates_to_dict(picks),
        "candidates": candidates_to_dict(candidates),
        "yizi_anchors": candidates_to_dict(yizi_only),
        "ladder": ladder,
        "failed": candidates_to_dict(failed),
        "stats": {
            "zt_count": len(ladder),
            "candidate_count": len(candidates),
            "zb_count": len(zb),
            "yizi_count": sum(1 for r in ladder if r["is_yizi"]),
            "non_yizi_count": sum(1 for r in ladder if not r["is_yizi"]),
            "quote_count": len(quotes),
        },
    }


def _strategy_block() -> dict:
    return {
        "name": "龙头确认（非一字）",
        "core": "一字买不进，只作高度锚；真龙头看竞价主动性 + 封板承接。",
        "summary": (
            "以昨日连板股为池，排除一字伪高度，用竞价涨幅、炸板次数、封单厚度"
            "确认今日可交易龙头；主输出最可能完成确认的两只非一字。"
        ),
        "rules": [
            "一字板：只记高度结构，不进可交易确认榜（买不进）",
            "候选池：昨连板 ≥ 2，剔除 ST",
            "龙头确认优先看竞价：理想高开约 4%～9.5%",
            "二次过滤：早封、零炸板、封单厚、真实换手 3%～18%",
            "高度龙若竞价弱/多次炸板 → 高度在，龙头不稳",
            "主输出：综合得分最高的 2 只非一字确认标的",
            "数据源可切换：东方财富 / 同花顺 / 通达信(腾讯免费行情)",
        ],
    }


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")

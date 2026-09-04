"""顺势选股 · 龙头确认实时服务。

一字买不进：只作高度结构参考。
主输出：可交易非一字的龙头确认（竞价 + 封板质量）。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from strategy.engine import (
    build_candidates,
    build_ladder,
    candidates_to_dict,
    confirm_summary,
    pick_confirmed_leaders,
)


def _china_tz():
    """Windows 默认无 IANA 时区库；优先 ZoneInfo，失败则用固定 UTC+8。"""
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("Asia/Shanghai")
    except Exception:
        return timezone(timedelta(hours=8), name="CST")


CN = _china_tz()
ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/",
}

app = FastAPI(title="顺势选股 · 龙头确认", version="1.1.0")


def trading_date(override: str | None = None) -> str:
    if override and len(override) == 8 and override.isdigit():
        return override
    return datetime.now(CN).strftime("%Y%m%d")


async def fetch_json(client: httpx.AsyncClient, url: str) -> dict:
    r = await client.get(url, timeout=20.0)
    r.raise_for_status()
    return r.json()


async def fetch_zt_pool(client: httpx.AsyncClient, date: str) -> list[dict]:
    url = (
        "https://push2ex.eastmoney.com/getTopicZTPool"
        f"?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
        f"&Pageindex=0&pagesize=200&sort=fbt:asc&date={date}"
    )
    data = await fetch_json(client, url)
    return ((data.get("data") or {}).get("pool")) or []


async def fetch_yesterday_zt(client: httpx.AsyncClient, date: str) -> list[dict]:
    url = (
        "https://push2ex.eastmoney.com/getYesterdayZTPool"
        f"?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
        f"&Pageindex=0&pagesize=200&sort=zdp:desc&date={date}"
    )
    data = await fetch_json(client, url)
    return ((data.get("data") or {}).get("pool")) or []


async def fetch_zb_pool(client: httpx.AsyncClient, date: str) -> list[dict]:
    url = (
        "https://push2ex.eastmoney.com/getTopicZBPool"
        f"?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
        f"&Pageindex=0&pagesize=100&sort=fbt:asc&date={date}"
    )
    data = await fetch_json(client, url)
    return ((data.get("data") or {}).get("pool")) or []


async def fetch_quotes(client: httpx.AsyncClient, codes: list[str]) -> dict[str, dict]:
    if not codes:
        return {}
    out: dict[str, dict] = {}
    fields = "f2,f3,f4,f5,f6,f7,f8,f10,f12,f14,f15,f16,f17,f18,f22,f62"
    for i in range(0, len(codes), 80):
        batch = codes[i : i + 80]
        secids = ",".join(
            [("1." + c) if c.startswith("6") else ("0." + c) for c in batch]
        )
        url = (
            "https://push2.eastmoney.com/api/qt/ulist.np/get"
            f"?fltt=2&fields={fields}&secids={secids}"
        )
        data = await fetch_json(client, url)
        for item in ((data.get("data") or {}).get("diff")) or []:
            code = str(item.get("f12") or "")
            if code:
                out[code] = item
    return out


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
    return {"ok": True, **market_session()}


@app.get("/api/leader")
async def leader(date: str | None = Query(default=None, description="YYYYMMDD")):
    d = trading_date(date)
    session = market_session()

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        yesterday, today_zt, zb = await asyncio.gather(
            fetch_yesterday_zt(client, d),
            fetch_zt_pool(client, d),
            fetch_zb_pool(client, d),
        )
        codes: list[str] = []
        for y in yesterday:
            zttj = y.get("zttj") or {}
            if int(zttj.get("ct") or 0) >= 2:
                codes.append(str(y.get("c")))
        for x in today_zt[:40]:
            c = str(x.get("c") or "")
            if c and c not in codes:
                codes.append(c)
        quotes = await fetch_quotes(client, codes)

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
        "date": d,
        "session": session,
        "source": "eastmoney",
        "strategy": {
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
            ],
        },
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
        },
    }


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")

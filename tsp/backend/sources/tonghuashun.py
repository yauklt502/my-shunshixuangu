"""同花顺公开涨停 + 腾讯行情。"""

from __future__ import annotations

from typing import Any

import httpx

from backend.config import UA
from backend.sources import eastmoney as em


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={
            "User-Agent": UA,
            "Referer": "https://data.10jqka.com.cn/",
            "Accept": "application/json, text/plain, */*",
        },
        timeout=httpx.Timeout(20.0, connect=8.0),
        follow_redirects=True,
        trust_env=False,
    )


async def health() -> dict[str, Any]:
    urls = [
        "https://d.10jqka.com.cn/v2/realhead/hs_a/last.js",
        "https://news.10jqka.com.cn/",
        "https://qt.gtimg.cn/q=sz000001",
    ]
    last = "unreachable"
    try:
        async with _client() as c:
            for url in urls:
                try:
                    r = await c.get(url)
                    if r.status_code == 200 and len(r.text) > 20:
                        return {"ok": True, "name": "同花顺", "detail": "可用"}
                    last = f"HTTP {r.status_code}"
                except Exception as exc:  # noqa: BLE001
                    last = str(exc)
        return {"ok": False, "name": "同花顺", "detail": last}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "name": "同花顺", "detail": str(exc)}


async def market_bundle(date: str) -> dict[str, Any]:
    zt: list[dict[str, Any]] = []
    try:
        d = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
        url = (
            "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool"
            f"?page=1&limit=200&filter=HS,GEM2STAR&date={d}"
        )
        async with _client() as c:
            r = await c.get(url)
            if r.status_code == 200:
                info = ((r.json().get("data") or {}).get("info")) or []
                for it in info:
                    zt.append(
                        {
                            "code": str(it.get("code") or ""),
                            "name": str(it.get("name") or ""),
                            "price": em.fnum(it.get("latest")),
                            "change_pct": em.fnum(it.get("change_rate")),
                            "amount": 0.0,
                            "turnover": em.fnum(it.get("turnover_rate")),
                            "seal_amount": em.fnum(it.get("order_amount")),
                            "first_seal": it.get("first_limit_up_time"),
                            "last_seal": it.get("last_limit_up_time"),
                            "open_count": int(em.fnum(it.get("open_num"))),
                            "boards": int(em.fnum(it.get("limit_up_days") or 1)),
                            "industry": str(it.get("reason_type") or ""),
                            "reason": str(it.get("reason_info") or it.get("limit_up_type") or ""),
                            "is_yizi": "一字" in str(it.get("limit_up_type") or ""),
                        }
                    )
    except Exception:  # noqa: BLE001
        zt = []

    base = await em.market_bundle(date)
    if zt:
        base["limit_up"] = zt
    base["source"] = "tonghuashun"
    return base


async def quotes(codes: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not codes:
        return out

    def sym(code: str) -> str:
        c = em.plain(code)
        return ("sh" if c.startswith(("6", "9")) else "sz") + c

    async with httpx.AsyncClient(
        headers={"User-Agent": UA, "Referer": "https://finance.qq.com/"},
        timeout=15.0,
        trust_env=False,
    ) as c:
        for i in range(0, len(codes), 40):
            url = "https://qt.gtimg.cn/q=" + ",".join(sym(x) for x in codes[i : i + 40])
            try:
                r = await c.get(url)
                r.raise_for_status()
            except Exception:  # noqa: BLE001
                continue
            for line in r.text.split(";"):
                line = line.strip()
                if '="' not in line:
                    continue
                parts = line.split('="', 1)[1].rstrip('"').split("~")
                if len(parts) < 6:
                    continue
                code = parts[2]
                price = em.fnum(parts[3])
                pre = em.fnum(parts[4])
                out[code] = {
                    "code": code,
                    "name": parts[1],
                    "price": price,
                    "change_pct": ((price / pre) - 1) * 100 if pre else 0.0,
                    "open": em.fnum(parts[5]),
                    "pre_close": pre,
                    "turnover": em.fnum(parts[38]) if len(parts) > 38 else 0.0,
                }
    return out


async def kline_day(code: str, count: int = 120) -> list[dict[str, Any]]:
    return await em.kline_day(code, count)


async def minute_today(code: str) -> dict[str, Any]:
    data = await em.minute_today(code)
    data["source"] = "tonghuashun"
    return data


async def board_members(board_code: str, limit: int = 60) -> list[dict[str, Any]]:
    return await em.board_members(board_code, limit)
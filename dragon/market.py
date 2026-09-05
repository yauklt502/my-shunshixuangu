"""东方财富公开行情：涨停池、炸板池、概念、人气榜、实时报价。"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from dragon.themes import theme_of
from dragon.timeutil import recent_weekdays, yyyymmdd

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

QUOTE_FIELDS = "f2,f3,f5,f6,f8,f10,f12,f14,f15,f16,f17,f18,f20,f21,f62,f100,f103"


def client_kwargs() -> dict[str, Any]:
    return {
        "headers": {"User-Agent": UA, "Referer": "https://quote.eastmoney.com/"},
        "follow_redirects": True,
        "timeout": httpx.Timeout(18.0, connect=7.0),
        "trust_env": False,
    }


def secid(code: str) -> str:
    code = (code or "").zfill(6)
    if code.startswith(("5", "6", "9")):
        return f"1.{code}"
    return f"0.{code}"


def pop_code(raw: str) -> str:
    return (raw or "")[-6:]


def to_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


async def fetch_json(client: httpx.AsyncClient, url: str, retries: int = 2) -> dict:
    last: Exception | None = None
    for i in range(retries + 1):
        try:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last = e
            await asyncio.sleep(0.3 * (i + 1))
    assert last is not None
    raise last


async def fetch_post_json(client: httpx.AsyncClient, url: str, payload: dict) -> dict:
    r = await client.post(
        url,
        json=payload,
        headers={
            "User-Agent": UA,
            "Content-Type": "application/json",
            "Referer": "https://guba.eastmoney.com/",
        },
    )
    r.raise_for_status()
    return r.json()


async def em_zt_pool(client: httpx.AsyncClient, date: str) -> list[dict]:
    url = (
        "https://push2ex.eastmoney.com/getTopicZTPool"
        f"?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
        f"&Pageindex=0&pagesize=200&sort=fbt:asc&date={date}"
    )
    data = await fetch_json(client, url)
    return ((data.get("data") or {}).get("pool")) or []


async def em_yesterday_zt(client: httpx.AsyncClient, date: str) -> list[dict]:
    url = (
        "https://push2ex.eastmoney.com/getYesterdayZTPool"
        f"?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
        f"&Pageindex=0&pagesize=200&sort=zdp:desc&date={date}"
    )
    data = await fetch_json(client, url)
    return ((data.get("data") or {}).get("pool")) or []


async def em_zb_pool(client: httpx.AsyncClient, date: str) -> list[dict]:
    url = (
        "https://push2ex.eastmoney.com/getTopicZBPool"
        f"?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
        f"&Pageindex=0&pagesize=100&sort=fbt:asc&date={date}"
    )
    data = await fetch_json(client, url)
    return ((data.get("data") or {}).get("pool")) or []


async def em_concepts(client: httpx.AsyncClient) -> list[dict]:
    urls = [
        "https://push2delay.eastmoney.com/api/qt/clist/get?pn=1&pz=80&po=1&np=1&fltt=2&invt=2"
        "&fid=f3&fs=m:90+t:2+f:!50&fields=f12,f14,f3,f8,f20,f104,f105,f128,f140,f141",
        "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=80&po=1&np=1&fltt=2&invt=2"
        "&fid=f3&fs=m:90+t:2+f:!50&fields=f12,f14,f3,f8,f20,f104,f105,f128,f140,f141",
    ]
    last: Exception | None = None
    for url in urls:
        try:
            data = await fetch_json(client, url, retries=1)
            diff = ((data.get("data") or {}).get("diff")) or []
            if diff:
                return diff
        except Exception as e:  # noqa: BLE001
            last = e
    if last:
        raise last
    return []


async def em_popularity(client: httpx.AsyncClient) -> dict[str, int]:
    data = await fetch_post_json(
        client,
        "https://emappdata.eastmoney.com/stockrank/getAllCurrentList",
        {"appId": "appId01", "pageNo": 1, "pageSize": 100},
    )
    out: dict[str, int] = {}
    for item in data.get("data") or []:
        code = pop_code(str(item.get("sc") or ""))
        rk = item.get("rk")
        if code.isdigit() and rk is not None:
            out[code] = int(rk)
    return out


async def em_indexes(client: httpx.AsyncClient) -> list[dict]:
    hosts = [
        "https://push2.eastmoney.com",
        "https://push2delay.eastmoney.com",
    ]
    secids = "1.000001,0.399001,0.399006"
    for host in hosts:
        url = f"{host}/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f12,f14,f15,f16&secids={secids}"
        try:
            data = await fetch_json(client, url, retries=1)
            out = []
            for item in ((data.get("data") or {}).get("diff")) or []:
                out.append(
                    {
                        "code": str(item.get("f12") or ""),
                        "name": str(item.get("f14") or ""),
                        "pct": to_float(item.get("f3")),
                        "price": to_float(item.get("f2")),
                    }
                )
            if out:
                return out
        except Exception:  # noqa: BLE001
            continue
    return []


async def em_quotes(client: httpx.AsyncClient, codes: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    hosts = [
        "https://push2.eastmoney.com",
        "https://push2delay.eastmoney.com",
        "https://82.push2.eastmoney.com",
    ]
    clean = [c for c in codes if c and c.isdigit()]
    for i in range(0, len(clean), 24):
        batch = clean[i : i + 24]
        secids = ",".join(secid(c) for c in batch)
        ok = False
        for host in hosts:
            url = f"{host}/api/qt/ulist.np/get?fltt=2&fields={QUOTE_FIELDS}&secids={secids}"
            try:
                data = await fetch_json(client, url, retries=1)
                for item in ((data.get("data") or {}).get("diff")) or []:
                    code = str(item.get("f12") or "")
                    if code:
                        out[code] = item
                ok = True
                break
            except Exception:  # noqa: BLE001
                continue
        if not ok:
            continue
    return out


def normalize_zt(item: dict, *, sealed: bool = True) -> dict[str, Any]:
    code = str(item.get("c") or "").zfill(6)
    name = str(item.get("n") or "")
    industry = str(item.get("hybk") or "")
    price = to_float(item.get("p"))
    if price > 1000:
        price = price / 1000.0
    return {
        "code": code,
        "name": name,
        "industry": industry,
        "theme": theme_of(industry),
        "price": price,
        "change_pct": to_float(item.get("zdp")),
        "amount": to_float(item.get("amount")),
        "circ_mv": to_float(item.get("ltsz")),
        "turnover": to_float(item.get("hs")),
        "boards": int(to_float(item.get("lbc") or 1)),
        "first_seal": int(to_float(item.get("fbt") or item.get("yfbt"))),
        "last_seal": int(to_float(item.get("lbt"))),
        "seal_fund": to_float(item.get("fund")),
        "open_count": int(to_float(item.get("zbc"))),
        "sealed": sealed,
        "raw": item,
    }


def merge_quote(row: dict, quote: dict | None) -> dict:
    if not quote:
        return row
    px = to_float(quote.get("f2"))
    if px > 0:
        row["price"] = px
    if quote.get("f3") is not None:
        row["change_pct"] = to_float(quote.get("f3"))
    if quote.get("f6"):
        row["amount"] = to_float(quote.get("f6"))
    if quote.get("f8") is not None:
        row["turnover"] = to_float(quote.get("f8"))
    row["volume_ratio"] = to_float(quote.get("f10")) if quote.get("f10") is not None else None
    row["volume"] = to_float(quote.get("f5"))
    row["high"] = to_float(quote.get("f15")) or None
    row["low"] = to_float(quote.get("f16")) or None
    row["open"] = to_float(quote.get("f17")) or None
    row["pre_close"] = to_float(quote.get("f18")) or None
    row["main_net"] = to_float(quote.get("f62")) if quote.get("f62") is not None else None
    if quote.get("f100"):
        row["industry"] = str(quote.get("f100"))
        row["theme"] = theme_of(row["industry"])
    row["concepts"] = str(quote.get("f103") or "")
    return row


def concept_index(concepts: list[dict]) -> dict[str, dict]:
    """按领涨股代码建索引，同一只票保留涨幅最高的概念。"""
    out: dict[str, dict] = {}
    for c in concepts:
        lead = str(c.get("f140") or "").zfill(6)
        if not lead.isdigit() or lead == "000000":
            continue
        rec = {
            "bk": str(c.get("f12") or ""),
            "name": str(c.get("f14") or ""),
            "pct": to_float(c.get("f3")),
            "up": int(to_float(c.get("f104"))),
            "down": int(to_float(c.get("f105"))),
            "lead_name": str(c.get("f128") or ""),
            "lead_code": lead,
            "amount": to_float(c.get("f20")),
        }
        old = out.get(lead)
        if old is None or rec["pct"] > old["pct"]:
            out[lead] = rec
    return out


async def resolve_trading_date(client: httpx.AsyncClient, override: str | None) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if override and len(override) == 8 and override.isdigit():
        pool = await em_zt_pool(client, override)
        if not pool:
            warnings.append(f"{override} 涨停池为空")
        return override, warnings
    for date in recent_weekdays(8):
        try:
            pool = await em_zt_pool(client, date)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"{date} 涨停池失败：{e}")
            continue
        if pool:
            today = yyyymmdd()
            if date != today:
                warnings.append(f"今日无有效涨停池，已回退到最近交易日 {date}")
            return date, warnings
    return yyyymmdd(), warnings + ["未取到任何交易日涨停池"]


async def load_market(date: str | None = None) -> dict[str, Any]:
    warnings: list[str] = []
    async with httpx.AsyncClient(**client_kwargs()) as client:
        trade_date, date_warns = await resolve_trading_date(client, date)
        warnings.extend(date_warns)
        yesterday: list[dict] = []
        today_zt: list[dict] = []
        zb: list[dict] = []
        concepts: list[dict] = []
        popularity: dict[str, int] = {}
        quotes: dict[str, dict] = {}
        indexes: list[dict] = []

        try:
            today_zt = await em_zt_pool(client, trade_date)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"涨停池失败：{e}")
        try:
            yesterday = await em_yesterday_zt(client, trade_date)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"昨日涨停池失败：{e}")
        try:
            zb = await em_zb_pool(client, trade_date)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"炸板池失败：{e}")
        try:
            concepts = await em_concepts(client)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"概念板块失败：{e}")
        try:
            popularity = await em_popularity(client)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"人气榜失败：{e}（辨识度改用成交额排名）")

        codes = []
        for item in today_zt + zb:
            c = str(item.get("c") or "")
            if c:
                codes.append(c)
        try:
            quotes = await em_quotes(client, codes)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"实时报价失败：{e}（量能用涨停池成交额/换手）")
        try:
            indexes = await em_indexes(client)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"大盘指数失败：{e}")
            indexes = []

    rows = [merge_quote(normalize_zt(x, sealed=True), quotes.get(str(x.get("c")))) for x in today_zt]
    broken = [merge_quote(normalize_zt(x, sealed=False), quotes.get(str(x.get("c")))) for x in zb]
    return {
        "date": trade_date,
        "zt": rows,
        "broken": broken,
        "yesterday": yesterday,
        "concepts": concepts,
        "popularity": popularity,
        "quotes": quotes,
        "indexes": indexes,
        "warnings": warnings,
        "source": {
            "id": "eastmoney",
            "name": "东方财富",
            "desc": "涨停池 + 炸板池 + 概念领涨 + 人气榜 + 实时量价",
        },
    }

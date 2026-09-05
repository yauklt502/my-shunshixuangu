"""东方财富公开行情：涨停池、炸板池、概念、实时报价。人气走同花顺热榜。"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from dragon.kpl import (
    client_kwargs as kpl_client_kwargs,
    fetch_kpl,
    kpl_row_to_zt,
    plates_as_concepts,
    probe_tianti,
)
from dragon.tencent import board_ladder, qq_indexes, qq_quotes, quote_incomplete
from dragon.themes import plate_theme, theme_of
from dragon.ths import client_kwargs as ths_client_kwargs
from dragon.ths import fetch_hot, fuse_popularity
from dragon.timeutil import recent_weekdays, yyyymmdd

LANE_NAMES = {
    "eastmoney": "东财",
    "kaipanla": "开盘啦",
    "tdx": "通达信",
    "tencent": "腾讯",
    "tonghuashun": "同花顺",
}

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


def lane(src: str, n: int | None = None, note: str = "") -> dict[str, Any]:
    rec: dict[str, Any] = {"src": src, "name": LANE_NAMES.get(src, src)}
    if n is not None:
        rec["n"] = n
    if note:
        rec["note"] = note
    return rec


def overlay_kpl(row: dict, tianti: dict | None, detail: dict | None) -> dict:
    """题材/原因走开盘啦；首封、炸次、连板能保住东财的就保住。"""
    if tianti:
        plate = str(tianti.get("plate") or "")
        if plate:
            row["kpl_theme"] = plate
            row["theme"] = tianti.get("theme") or plate_theme(plate)
            row["industry"] = plate
            row["theme_source"] = "kaipanla"
        if not int(row.get("first_seal") or 0) and tianti.get("first_seal"):
            row["first_seal"] = int(tianti["first_seal"])
        if not int(row.get("boards") or 0) and tianti.get("boards"):
            row["boards"] = int(tianti["boards"])
        if not float(row.get("amount") or 0) and tianti.get("amount"):
            row["amount"] = tianti["amount"]
    if detail:
        if detail.get("reason"):
            row["reason"] = detail["reason"]
        if not float(row.get("turnover") or 0) and detail.get("turnover"):
            row["turnover"] = detail["turnover"]
        if not float(row.get("price") or 0) and detail.get("price"):
            row["price"] = detail["price"]
        if not float(row.get("amount") or 0) and detail.get("amount"):
            row["amount"] = detail["amount"]
        if not float(row.get("circ_mv") or 0) and detail.get("circ_mv"):
            row["circ_mv"] = detail["circ_mv"]
        if not float(row.get("seal_fund") or 0) and detail.get("seal_fund"):
            row["seal_fund"] = detail["seal_fund"]
        if not float(row.get("change_pct") or 0) and detail.get("change_pct"):
            row["change_pct"] = detail["change_pct"]
    return row


def fuse_zt(
    em_rows: list[dict],
    kpl: dict[str, Any],
    quotes: dict[str, dict],
) -> tuple[list[dict], str | None]:
    tianti = {x["code"]: x for x in kpl.get("tianti") or []}
    details = kpl.get("details") or {}
    if em_rows:
        out = []
        for row in em_rows:
            overlay_kpl(row, tianti.get(row["code"]), details.get(row["code"]))
            out.append(row)
        seen = {r["code"] for r in out}
        for item in kpl.get("tianti") or []:
            if item["code"] in seen:
                continue
            row = merge_quote(kpl_row_to_zt(item, details.get(item["code"])), quotes.get(item["code"]))
            out.append(row)
        return out, "eastmoney"
    if tianti:
        out = []
        for item in kpl.get("tianti") or []:
            row = merge_quote(kpl_row_to_zt(item, details.get(item["code"])), quotes.get(item["code"]))
            out.append(row)
        return out, "kaipanla"
    return [], None


def fuse_broken(
    em_rows: list[dict],
    kpl: dict[str, Any],
    quotes: dict[str, dict],
) -> tuple[list[dict], str | None]:
    kpl_broken = {x["code"]: x for x in kpl.get("broken") or []}
    if em_rows:
        for row in em_rows:
            hit = kpl_broken.get(row["code"])
            if hit and hit.get("theme") and hit["theme"] not in {"其他", "ST股", "未知"}:
                row["theme"] = hit["theme"]
                row["industry"] = hit.get("themes") or row.get("industry")
                row["theme_source"] = "kaipanla"
        return em_rows, "eastmoney"
    if kpl_broken:
        out = []
        for item in kpl.get("broken") or []:
            row = {
                "code": item["code"],
                "name": item.get("name") or "",
                "industry": item.get("industry") or item.get("themes") or "",
                "theme": item.get("theme") or plate_theme(item.get("themes")),
                "price": item.get("price") or 0,
                "change_pct": item.get("change_pct") or 0,
                "amount": item.get("amount") or 0,
                "circ_mv": item.get("circ_mv") or 0,
                "turnover": item.get("turnover") or 0,
                "boards": 1,
                "first_seal": 0,
                "last_seal": 0,
                "seal_fund": 0,
                "open_count": 1,
                "sealed": False,
                "theme_source": "kaipanla",
            }
            out.append(merge_quote(row, quotes.get(item["code"])))
        return out, "kaipanla"
    return [], None


def fuse_concepts(em_concepts: list[dict], kpl: dict[str, Any]) -> tuple[list[dict], str | None]:
    kpl_concepts = plates_as_concepts(kpl.get("plates") or [], kpl.get("zhu") or [])
    if kpl_concepts and em_concepts:
        return kpl_concepts + em_concepts, "kaipanla"
    if kpl_concepts:
        return kpl_concepts, "kaipanla"
    if em_concepts:
        return em_concepts, "eastmoney"
    return [], None


def fuse_indexes(em_indexes: list[dict], kpl: dict[str, Any]) -> tuple[list[dict], str | None]:
    if em_indexes:
        return em_indexes, "eastmoney"
    kpl_idx = kpl.get("indexes") or []
    if kpl_idx:
        return kpl_idx, "kaipanla"
    return [], None


async def resolve_trading_date(
    em: httpx.AsyncClient,
    kp: httpx.AsyncClient,
    override: str | None,
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if override and len(override) == 8 and override.isdigit():
        try:
            pool = await em_zt_pool(em, override)
            if not pool:
                warnings.append(f"{override} 东财涨停池为空，尝试开盘啦补齐")
        except Exception as e:  # noqa: BLE001
            warnings.append(f"{override} 东财涨停池失败：{e}，尝试开盘啦补齐")
        return override, warnings
    for date in recent_weekdays(8):
        try:
            pool = await em_zt_pool(em, date)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"{date} 涨停池失败：{e}")
            continue
        if pool:
            today = yyyymmdd()
            if date != today:
                warnings.append(f"今日无有效涨停池，已回退到最近交易日 {date}")
            return date, warnings
    for date in recent_weekdays(8):
        try:
            stocks = await probe_tianti(kp, date)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"{date} 开盘啦天梯失败：{e}")
            continue
        if stocks:
            warnings.append(f"东财涨停池为空，已用开盘啦回退到 {date}")
            return date, warnings
    return yyyymmdd(), warnings + ["未取到任何交易日涨停池"]


async def load_market(date: str | None = None) -> dict[str, Any]:
    warnings: list[str] = []
    lanes: dict[str, dict[str, Any]] = {"K线": lane("tdx", note="分时/日K/五档")}
    async with (
        httpx.AsyncClient(**client_kwargs()) as em,
        httpx.AsyncClient(**kpl_client_kwargs()) as kp,
        httpx.AsyncClient(**ths_client_kwargs()) as ths,
    ):
        trade_date, date_warns = await resolve_trading_date(em, kp, date)
        warnings.extend(date_warns)
        latest = trade_date == yyyymmdd()

        async def grab(name: str, coro):
            try:
                return name, await coro
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"{name}失败：{exc}")
                return name, None

        parts = await asyncio.gather(
            grab("涨停池", em_zt_pool(em, trade_date)),
            grab("昨日涨停池", em_yesterday_zt(em, trade_date)),
            grab("炸板池", em_zb_pool(em, trade_date)),
            grab("概念板块", em_concepts(em)),
            grab("同花顺热榜", fetch_hot(ths)),
            grab("东财人气榜", em_popularity(em)),
            grab("大盘指数", em_indexes(em)),
            grab("开盘啦", fetch_kpl(kp, trade_date, latest=latest)),
        )
        got = {name: value for name, value in parts}
        today_zt = got.get("涨停池") or []
        yesterday = got.get("昨日涨停池") or []
        zb = got.get("炸板池") or []
        em_concepts_rows = got.get("概念板块") or []
        ths_pack = got.get("同花顺热榜") or {}
        ths_ranks = ths_pack.get("ranks") if isinstance(ths_pack, dict) else {}
        hot_top = (ths_pack.get("rows") or [])[:10] if isinstance(ths_pack, dict) else []
        em_pop = got.get("东财人气榜") or {}
        popularity, pop_src = fuse_popularity(ths_ranks, em_pop)
        if not ths_ranks and em_pop:
            warnings.append("同花顺热榜空，人气改走东财整榜")
        em_indexes_rows = got.get("大盘指数") or []
        kpl = got.get("开盘啦") or {}
        warnings.extend(kpl.get("warnings") or [])

        em_rows = [normalize_zt(x, sealed=True) for x in today_zt]
        em_broken = [normalize_zt(x, sealed=False) for x in zb]
        codes = [str(r.get("code") or "") for r in em_rows + em_broken]
        codes.extend(str(x.get("code") or "") for x in (kpl.get("tianti") or []))
        codes.extend(str(x.get("code") or "") for x in (kpl.get("broken") or []))
        quotes: dict[str, dict] = {}
        try:
            quotes = await em_quotes(em, codes)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"东财报价失败：{e}，改走腾讯")
        need = [c for c in codes if c and quote_incomplete(quotes.get(c))]
        qq_n = 0
        if need:
            try:
                filled = await qq_quotes(em, need)
                for code, item in filled.items():
                    if quote_incomplete(quotes.get(code)):
                        quotes[code] = item
                        qq_n += 1
            except Exception as e:  # noqa: BLE001
                warnings.append(f"腾讯报价失败：{e}（量能用涨停池成交额/换手）")
        em_rows = [merge_quote(row, quotes.get(row["code"])) for row in em_rows]
        em_broken = [merge_quote(row, quotes.get(row["code"])) for row in em_broken]

        rows, zt_src = fuse_zt(em_rows, kpl, quotes)
        broken, zb_src = fuse_broken(em_broken, kpl, quotes)
        concepts, bk_src = fuse_concepts(em_concepts_rows, kpl)
        indexes, idx_src = fuse_indexes(em_indexes_rows, kpl)
        if not indexes:
            try:
                indexes = await qq_indexes(em)
                if indexes:
                    idx_src = "tencent"
            except Exception as e:  # noqa: BLE001
                warnings.append(f"腾讯指数失败：{e}")

        if zt_src:
            lanes["涨停池"] = lane(zt_src, len(rows))
        if any(r.get("theme_source") == "kaipanla" for r in rows):
            top = (kpl.get("zhu") or [{}])[0]
            lanes["题材主线"] = lane(
                "kaipanla",
                top.get("count"),
                note=f"{top.get('name') or ''}{top.get('count') or ''}家".strip(),
            )
        elif rows:
            lanes["题材主线"] = lane("eastmoney", note="东财行业归并")
        if zb_src:
            lanes["炸板"] = lane(zb_src, len(broken))
        if bk_src:
            lanes["板块强度"] = lane(bk_src, len(kpl.get("plates") or []) or None)
        if popularity and pop_src:
            kind = ths_pack.get("kind") if isinstance(ths_pack, dict) else ""
            note = "1小时热榜" if kind == "hour" else ("日榜" if kind == "day" else "")
            if pop_src == "eastmoney":
                note = "热榜挂了，东财顶上"
            lanes["人气"] = lane(pop_src, len(popularity), note=note)
        em_q = sum(1 for q in quotes.values() if q.get("_src") != "tencent")
        if qq_n and not em_q:
            lanes["报价"] = lane("tencent", qq_n)
        elif quotes:
            lanes["报价"] = lane("eastmoney", em_q or len(quotes), note=f"腾讯补{qq_n}只" if qq_n else "")
        if kpl.get("mood") or kpl.get("expression"):
            mood = kpl.get("mood") or {}
            lanes["情绪"] = lane("kaipanla", note=f"强度{mood.get('strong') or '-'}")
        if idx_src:
            lanes["指数"] = lane(idx_src, len(indexes))

    return {
        "date": trade_date,
        "zt": rows,
        "broken": broken,
        "yesterday": yesterday,
        "concepts": concepts,
        "popularity": popularity,
        "hot_top": hot_top,
        "quotes": quotes,
        "indexes": indexes,
        "mood": kpl.get("mood"),
        "expression": kpl.get("expression"),
        "zhu": kpl.get("zhu") or [],
        "ladder": board_ladder(rows),
        "warnings": warnings,
        "source": {
            "id": "multi",
            "name": "东财 + 开盘啦 + 同花顺 + 通达信 + 腾讯",
            "desc": "人气走同花顺热榜，东财只扛涨停池炸次。题材走开盘啦，K线走通达信，报价东财缺了用腾讯补。",
            "lanes": lanes,
        },
    }

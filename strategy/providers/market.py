"""多数据源适配层：东方财富 / 同花顺 / 通达信(腾讯免费行情)。"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from strategy.providers import num, quote_fields, secid_em, sina_symbol, tencent_symbol

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

SOURCES = {
    "eastmoney": {
        "id": "eastmoney",
        "name": "东方财富",
        "desc": "涨停池 + 竞价最完整（推荐）",
    },
    "tonghuashun": {
        "id": "tonghuashun",
        "name": "同花顺",
        "desc": "同花顺涨停/行情接口（免费）",
    },
    "tongdaxin": {
        "id": "tongdaxin",
        "name": "通达信",
        "desc": "通达信常用免费行情（腾讯/新浪）+ 涨停结构",
    },
}


def client_kwargs() -> dict[str, Any]:
    # trust_env=False：忽略系统代理。Windows 开了代理时东财常被掐断。
    return {
        "headers": {"User-Agent": UA, "Referer": "https://quote.eastmoney.com/"},
        "follow_redirects": True,
        "timeout": httpx.Timeout(20.0, connect=8.0),
        "trust_env": False,
    }


async def fetch_json(client: httpx.AsyncClient, url: str, retries: int = 2) -> dict:
    last: Exception | None = None
    for i in range(retries + 1):
        try:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last = e
            await asyncio.sleep(0.35 * (i + 1))
    assert last is not None
    raise last


async def fetch_text(client: httpx.AsyncClient, url: str, retries: int = 2) -> str:
    last: Exception | None = None
    for i in range(retries + 1):
        try:
            r = await client.get(url)
            r.raise_for_status()
            return r.text
        except Exception as e:  # noqa: BLE001
            last = e
            await asyncio.sleep(0.35 * (i + 1))
    assert last is not None
    raise last


# ---------------- 东方财富 ----------------
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


async def em_quotes(client: httpx.AsyncClient, codes: list[str]) -> dict[str, dict]:
    """小批量 + 多镜像；失败返回已成功部分，不抛穿。"""
    out: dict[str, dict] = {}
    clean = [c for c in codes if secid_em(c)]
    hosts = [
        "https://push2.eastmoney.com",
        "https://push2delay.eastmoney.com",
        "https://82.push2.eastmoney.com",
    ]
    fields = "f2,f3,f8,f12,f14,f17,f18,f62"
    for i in range(0, len(clean), 20):
        batch = clean[i : i + 20]
        secids = ",".join(secid_em(c) for c in batch if secid_em(c))
        if not secids:
            continue
        ok = False
        for host in hosts:
            url = f"{host}/api/qt/ulist.np/get?fltt=2&fields={fields}&secids={secids}"
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
            # 单只兜底，尽量多拿
            for c in batch:
                sid = secid_em(c)
                if not sid:
                    continue
                for host in hosts:
                    url = f"{host}/api/qt/ulist.np/get?fltt=2&fields={fields}&secids={sid}"
                    try:
                        data = await fetch_json(client, url, retries=0)
                        for item in ((data.get("data") or {}).get("diff")) or []:
                            code = str(item.get("f12") or "")
                            if code:
                                out[code] = item
                        break
                    except Exception:  # noqa: BLE001
                        continue
    return out


# ---------------- 腾讯 / 新浪（通达信常用免费源）----------------
async def tencent_quotes(client: httpx.AsyncClient, codes: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    syms = [tencent_symbol(c) for c in codes]
    syms = [s for s in syms if s]
    client.headers["Referer"] = "https://finance.qq.com/"
    for i in range(0, len(syms), 40):
        batch = syms[i : i + 40]
        url = "https://qt.gtimg.cn/q=" + ",".join(batch)
        try:
            text = await fetch_text(client, url, retries=1)
        except Exception:  # noqa: BLE001
            continue
        for line in text.split(";"):
            line = line.strip()
            if not line or "=\"" not in line:
                continue
            # v_sz000001="1~平安银行~000001~11.20~...
            try:
                body = line.split('="', 1)[1].rstrip('"')
                parts = body.split("~")
                if len(parts) < 6:
                    continue
                name = parts[1]
                code = parts[2]
                price = num(parts[3])
                pre = num(parts[4])
                opn = num(parts[5])
                change_pct = ((price / pre) - 1.0) * 100.0 if pre else 0.0
                # 换手约在 38 位附近，不同版本不稳定，缺省 0
                turnover = num(parts[38]) if len(parts) > 38 else 0.0
                out[code] = quote_fields(
                    price=price,
                    change_pct=change_pct,
                    open_price=opn,
                    pre_close=pre,
                    turnover=turnover,
                    name=name,
                    code=code,
                )
            except Exception:  # noqa: BLE001
                continue
    return out


async def sina_quotes(client: httpx.AsyncClient, codes: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    syms = [sina_symbol(c) for c in codes]
    syms = [s for s in syms if s]
    client.headers["Referer"] = "https://finance.sina.com.cn/"
    for i in range(0, len(syms), 40):
        batch = syms[i : i + 40]
        url = "https://hq.sinajs.cn/list=" + ",".join(batch)
        try:
            text = await fetch_text(client, url, retries=1)
        except Exception:  # noqa: BLE001
            continue
        for line in text.splitlines():
            # var hq_str_sh600000="名称,开盘,昨收,现价,..."
            m = re.search(r'hq_str_(\w+)="([^"]*)"', line)
            if not m:
                continue
            sym, body = m.group(1), m.group(2)
            parts = body.split(",")
            if len(parts) < 4:
                continue
            code = sym[-6:]
            name = parts[0]
            opn = num(parts[1])
            pre = num(parts[2])
            price = num(parts[3])
            change_pct = ((price / pre) - 1.0) * 100.0 if pre else 0.0
            out[code] = quote_fields(
                price=price,
                change_pct=change_pct,
                open_price=opn,
                pre_close=pre,
                turnover=0.0,
                name=name,
                code=code,
            )
    return out


# ---------------- 同花顺 ----------------
def _ths_headers() -> dict[str, str]:
    return {
        "User-Agent": UA,
        "Referer": "https://data.10jqka.com.cn/",
        "Accept": "application/json, text/plain, */*",
    }


async def ths_limit_up_pool(client: httpx.AsyncClient, date: str) -> list[dict]:
    """同花顺涨停池；字段映射到东财 pool 近似结构。"""
    client.headers.update(_ths_headers())
    # date: YYYYMMDD -> YYYY-MM-DD
    d = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
    urls = [
        f"https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page=1&limit=200&date={d}",
        f"https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page=1&limit=200",
    ]
    raw_list: list[dict] = []
    for url in urls:
        try:
            data = await fetch_json(client, url, retries=1)
            info = data.get("data") or data
            pool = info.get("info") or info.get("list") or info.get("pool") or []
            if isinstance(pool, list) and pool:
                raw_list = pool
                break
        except Exception:  # noqa: BLE001
            continue
    out: list[dict] = []
    for x in raw_list:
        code = str(x.get("code") or x.get("stock_code") or "").zfill(6)
        name = str(x.get("name") or x.get("stock_name") or "")
        if not code.isdigit():
            continue
        # 连板数
        lbc = int(num(x.get("continue_num") or x.get("limit_times") or x.get("board_count") or 1))
        zdp = num(x.get("change_rate") or x.get("zdf") or x.get("pct_chg") or 10.0)
        price = num(x.get("latest") or x.get("price") or x.get("last_px") or 0)
        # 价格在引擎里按 /1000，这里与东财对齐：东财 p 是厘
        p = int(price * 1000) if price < 10000 else int(price)
        first_limit = str(x.get("first_limit_up_time") or x.get("first_time") or "09:30:00")
        fbt = _time_to_fbt(first_limit)
        last_limit = str(x.get("last_limit_up_time") or x.get("last_time") or first_limit)
        lbt = _time_to_fbt(last_limit)
        open_num = int(num(x.get("open_num") or x.get("break_times") or 0))
        fund = num(x.get("order_amount") or x.get("limit_up_fund") or x.get("seal_amount") or 0)
        # 同花顺封单常为元
        if 0 < fund < 1e7:
            fund = fund  # 可能已是元
        amount = num(x.get("turnover") or x.get("amount") or 0)
        hs = num(x.get("turnover_rate") or x.get("hs") or 0)
        hybk = str(x.get("reason_type") or x.get("plate_name") or x.get("concept") or "")
        out.append(
            {
                "c": code,
                "n": name,
                "p": p,
                "zdp": zdp,
                "lbc": lbc,
                "fbt": fbt,
                "lbt": lbt,
                "zbc": open_num,
                "fund": fund,
                "amount": amount,
                "hs": hs,
                "hybk": hybk,
                "zttj": {"days": lbc, "ct": lbc},
            }
        )
    return out


def _time_to_fbt(t: str) -> int:
    # "09:30:06" / "093006" / "9:30"
    t = t.strip().replace("：", ":")
    if not t:
        return 93000
    if t.isdigit() and len(t) >= 5:
        return int(t[:6].ljust(6, "0"))
    parts = t.split(":")
    try:
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        s = int(float(parts[2])) if len(parts) > 2 else 0
        return h * 10000 + m * 100 + s
    except Exception:  # noqa: BLE001
        return 93000


async def ths_quotes(client: httpx.AsyncClient, codes: list[str]) -> dict[str, dict]:
    """同花顺实时头；失败再回落腾讯。"""
    out: dict[str, dict] = {}
    client.headers.update(_ths_headers())
    for code in codes:
        sym = tencent_symbol(code)
        if not sym:
            continue
        # hs_600000 / sz_000001 style
        market = "hs" if code.startswith("6") else ("sz" if not code.startswith("6") else "hs")
        # 同花顺 realhead: https://d.10jqka.com.cn/v6/realhead/hs_600000/last.js
        key = f"hs_{code}" if code.startswith("6") else f"sz_{code}"
        url = f"https://d.10jqka.com.cn/v6/realhead/{key}/last.js"
        try:
            text = await fetch_text(client, url, retries=0)
            # quotebridge_v6_realhead_hs_600000_last({...})
            m = re.search(r"\((\{.*\})\)\s*;?\s*$", text, re.S)
            if not m:
                continue
            import json

            payload = json.loads(m.group(1))
            items = payload.get("items") or payload.get("data") or payload
            if isinstance(items, dict) and "10" in items:
                # field map: 10=name? 实际字段编号因版本而异；尽量稳健
                price = num(items.get("10") or items.get("price"))
                # 常见：6=昨收 7=开盘 8? 
                pre = num(items.get("6") or items.get("pre") or items.get("13"))
                opn = num(items.get("7") or items.get("open") or items.get("14"))
                name = str(items.get("name") or items.get("5") or "")
                if price and pre:
                    out[code] = quote_fields(
                        price=price,
                        change_pct=((price / pre) - 1.0) * 100.0,
                        open_price=opn or price,
                        pre_close=pre,
                        name=name,
                        code=code,
                    )
        except Exception:  # noqa: BLE001
            continue
    if len(out) < max(1, len(codes) // 3):
        # 同花顺弱时用腾讯补
        more = await tencent_quotes(client, codes)
        for k, v in more.items():
            out.setdefault(k, v)
    return out


# ---------------- 统一入口 ----------------
async def load_market(
    source: str,
    date: str,
) -> dict[str, Any]:
    """返回 yesterday/today_zt/zb/quotes/warnings。"""
    source = (source or "eastmoney").lower().strip()
    if source not in SOURCES:
        source = "eastmoney"

    warnings: list[str] = []
    yesterday: list[dict] = []
    today_zt: list[dict] = []
    zb: list[dict] = []
    quotes: dict[str, dict] = {}

    async with httpx.AsyncClient(**client_kwargs()) as client:
        # 涨停结构：同花顺优先自有池，失败回落东财；通达信用东财结构+腾讯行情
        if source == "tonghuashun":
            try:
                today_zt = await ths_limit_up_pool(client, date)
                if not today_zt:
                    warnings.append("同花顺涨停池为空，已回落东方财富涨停池")
                    today_zt = await em_zt_pool(client, date)
            except Exception as e:  # noqa: BLE001
                warnings.append(f"同花顺涨停池失败，回落东财：{e}")
                today_zt = await em_zt_pool(client, date)
            try:
                yesterday = await em_yesterday_zt(client, date)
            except Exception as e:  # noqa: BLE001
                warnings.append(f"昨日涨停池失败：{e}")
                # 用今日池冒充昨日结构（仅保证不崩）
                yesterday = [
                    {
                        **x,
                        "zttj": {
                            "days": max(1, int(x.get("lbc") or 1)),
                            "ct": max(1, int(x.get("lbc") or 1)),
                        },
                        "zdp": x.get("zdp") or 0,
                    }
                    for x in today_zt
                ]
            try:
                zb = await em_zb_pool(client, date)
            except Exception:  # noqa: BLE001
                zb = []
        else:
            # eastmoney / tongdaxin：结构用东财
            try:
                yesterday, today_zt, zb = await asyncio.gather(
                    em_yesterday_zt(client, date),
                    em_zt_pool(client, date),
                    em_zb_pool(client, date),
                )
            except Exception as e:  # noqa: BLE001
                warnings.append(f"涨停池拉取异常：{e}")
                # 再各试一次
                for label, coro, slot in [
                    ("yesterday", em_yesterday_zt(client, date), "yesterday"),
                    ("today", em_zt_pool(client, date), "today"),
                    ("zb", em_zb_pool(client, date), "zb"),
                ]:
                    try:
                        val = await coro
                        if slot == "yesterday":
                            yesterday = val
                        elif slot == "today":
                            today_zt = val
                        else:
                            zb = val
                    except Exception as ee:  # noqa: BLE001
                        warnings.append(f"{label}失败：{ee}")

        codes: list[str] = []
        for y in yesterday:
            zttj = y.get("zttj") or {}
            if int(zttj.get("ct") or 0) >= 2:
                codes.append(str(y.get("c")))
        for x in today_zt[:50]:
            c = str(x.get("c") or "")
            if c and c not in codes:
                codes.append(c)

        # 行情源
        try:
            if source == "tonghuashun":
                quotes = await ths_quotes(client, codes)
            elif source == "tongdaxin":
                quotes = await tencent_quotes(client, codes)
                if len(quotes) < max(1, len(codes) // 3):
                    more = await sina_quotes(client, codes)
                    for k, v in more.items():
                        quotes.setdefault(k, v)
                    if more:
                        warnings.append("通达信腾讯行情不足，已用新浪补齐")
            else:
                quotes = await em_quotes(client, codes)
                if len(quotes) < max(1, len(codes) // 3):
                    more = await tencent_quotes(client, codes)
                    for k, v in more.items():
                        quotes.setdefault(k, v)
                    if more:
                        warnings.append("东财竞价接口不稳，已用腾讯行情补齐")
        except Exception as e:  # noqa: BLE001
            warnings.append(f"行情获取失败（已用涨停池字段降级）：{e}")
            quotes = {}

    return {
        "source": source,
        "source_meta": SOURCES[source],
        "yesterday": yesterday,
        "today_zt": today_zt,
        "zb": zb,
        "quotes": quotes,
        "warnings": warnings,
    }

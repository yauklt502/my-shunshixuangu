"""东方财富公开数据。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from backend.config import UA

CN = timezone(timedelta(hours=8))


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": UA, "Referer": "https://quote.eastmoney.com/"},
        timeout=httpx.Timeout(30.0, connect=15.0),
        follow_redirects=True,
        trust_env=False,
    )


def today_ymd() -> str:
    return datetime.now(CN).strftime("%Y%m%d")


def plain(code: str) -> str:
    return "".join(ch for ch in str(code) if ch.isdigit())[-6:].zfill(6)


def to_secid(code: str) -> str:
    c = plain(code)
    return f"1.{c}" if c.startswith(("6", "9")) else f"0.{c}"


def fnum(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "-" or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


async def health() -> dict[str, Any]:
    hosts = [
        "https://push2.eastmoney.com/api/qt/ulist.np/get",
        "https://push2delay.eastmoney.com/api/qt/ulist.np/get",
        "https://82.push2.eastmoney.com/api/qt/ulist.np/get",
    ]
    params = {"fltt": "2", "fields": "f12,f14,f2", "secids": "1.000001"}
    last_exc: Exception | None = None
    try:
        async with client() as c:
            for host in hosts:
                try:
                    r = await c.get(host, params=params)
                    r.raise_for_status()
                    ok = bool(((r.json().get("data") or {}).get("diff")) or [])
                    return {"ok": ok, "name": "东方财富", "detail": "可用" if ok else "无数据"}
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    continue
        return {"ok": False, "name": "东方财富", "detail": str(last_exc or "无可用节点")}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "name": "东方财富", "detail": str(exc)}


async def zt_pool(date: str) -> list[dict[str, Any]]:
    url = (
        "https://push2ex.eastmoney.com/getTopicZTPool"
        "?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
        f"&Pageindex=0&pagesize=200&sort=fbt:asc&date={date}"
    )
    async with client() as c:
        r = await c.get(url)
        r.raise_for_status()
        return ((r.json().get("data") or {}).get("pool")) or []


async def zb_pool(date: str) -> list[dict[str, Any]]:
    url = (
        "https://push2ex.eastmoney.com/getTopicZBPool"
        "?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
        f"&Pageindex=0&pagesize=100&sort=fbt:asc&date={date}"
    )
    async with client() as c:
        r = await c.get(url)
        r.raise_for_status()
        return ((r.json().get("data") or {}).get("pool")) or []


async def board_rank(limit: int = 40) -> list[dict[str, Any]]:
    params = (
        f"?pn=1&pz={limit}&po=1&np=1&fltt=2&invt=2&fid=f3"
        "&fs=m:90+t:3+f:!50"
        "&fields=f12,f14,f2,f3,f62,f128,f140,f141,f136"
    )
    hosts = [
        "https://push2.eastmoney.com/api/qt/clist/get",
        "https://push2delay.eastmoney.com/api/qt/clist/get",
        "https://82.push2.eastmoney.com/api/qt/clist/get",
    ]
    diff: list[dict[str, Any]] = []
    async with client() as c:
        last_exc: Exception | None = None
        for host in hosts:
            try:
                r = await c.get(host + params)
                r.raise_for_status()
                diff = ((r.json().get("data") or {}).get("diff")) or []
                if diff:
                    break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                continue
        if not diff and last_exc:
            raise last_exc
        out = []
        for i, it in enumerate(diff):
            out.append(
                {
                    "code": str(it.get("f12") or ""),
                    "name": str(it.get("f14") or ""),
                    "change_pct": fnum(it.get("f3")),
                    "amount": fnum(it.get("f62")),
                    "leader_code": plain(str(it.get("f141") or it.get("f140") or "")),
                    "leader_name": str(it.get("f128") or ""),
                    "leader_pct": fnum(it.get("f136")),
                    "rank": i + 1,
                }
            )
        return out


async def board_members(board_code: str, limit: int = 60) -> list[dict[str, Any]]:
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get"
        f"?pn=1&pz={limit}&po=1&np=1&fltt=2&invt=2&fid=f3"
        f"&fs=b:{board_code}+f:!50"
        "&fields=f12,f14,f2,f3,f8,f15,f16,f17,f18,f100"
    )
    async with client() as c:
        r = await c.get(url)
        r.raise_for_status()
        diff = ((r.json().get("data") or {}).get("diff")) or []
        return [
            {
                "code": str(it.get("f12") or ""),
                "name": str(it.get("f14") or ""),
                "price": fnum(it.get("f2")),
                "change_pct": fnum(it.get("f3")),
                "turnover": fnum(it.get("f8")),
                "open": fnum(it.get("f17")),
                "high": fnum(it.get("f15")),
                "low": fnum(it.get("f16")),
                "pre_close": fnum(it.get("f18")),
                "industry": str(it.get("f100") or ""),
            }
            for it in diff
        ]


async def quotes(codes: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not codes:
        return out
    async with client() as c:
        for i in range(0, len(codes), 40):
            batch = codes[i : i + 40]
            secids = ",".join(to_secid(x) for x in batch)
            url = (
                "https://push2.eastmoney.com/api/qt/ulist.np/get"
                f"?fltt=2&fields=f2,f3,f8,f12,f14,f15,f16,f17,f18&secids={secids}"
            )
            try:
                r = await c.get(url)
                r.raise_for_status()
                for it in ((r.json().get("data") or {}).get("diff")) or []:
                    code = str(it.get("f12") or "")
                    if code:
                        out[code] = {
                            "code": code,
                            "name": str(it.get("f14") or ""),
                            "price": fnum(it.get("f2")),
                            "change_pct": fnum(it.get("f3")),
                            "turnover": fnum(it.get("f8")),
                            "high": fnum(it.get("f15")),
                            "low": fnum(it.get("f16")),
                            "open": fnum(it.get("f17")),
                            "pre_close": fnum(it.get("f18")),
                        }
            except Exception:  # noqa: BLE001
                continue
    return out


async def kline_day(code: str, count: int = 120) -> list[dict[str, Any]]:
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={to_secid(code)}&fields1=f1,f2,f3,f4,f5,f6"
        "&fields2=f51,f52,f53,f54,f55,f56,f57"
        f"&klt=101&fqt=1&end=20500101&lmt={count}"
    )
    async with client() as c:
        r = await c.get(url)
        r.raise_for_status()
        bars = []
        for row in ((r.json().get("data") or {}).get("klines")) or []:
            p = str(row).split(",")
            if len(p) < 6:
                continue
            bars.append(
                {
                    "time": p[0],
                    "open": fnum(p[1]),
                    "close": fnum(p[2]),
                    "high": fnum(p[3]),
                    "low": fnum(p[4]),
                    "volume": fnum(p[5]),
                    "amount": fnum(p[6]) if len(p) > 6 else 0.0,
                }
            )
        return bars


async def minute_today(code: str) -> dict[str, Any]:
    url = (
        "https://push2.eastmoney.com/api/qt/stock/trends2/get"
        f"?secid={to_secid(code)}"
        "&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13"
        "&fields2=f51,f52,f53,f54,f55,f56,f57,f58&iscr=0&ndays=1"
    )
    async with client() as c:
        r = await c.get(url)
        r.raise_for_status()
        data = r.json().get("data") or {}
        points = []
        for row in data.get("trends") or []:
            p = str(row).split(",")
            if len(p) < 5:
                continue
            points.append(
                {
                    "time": p[0][-5:] if " " in p[0] else p[0],
                    "price": fnum(p[1]),
                    "avg": fnum(p[2]),
                    "volume": fnum(p[3]),
                    "amount": fnum(p[4]),
                }
            )
        return {
            "code": plain(code),
            "name": data.get("name") or "",
            "pre_close": fnum(data.get("preClose") or data.get("prePrice")),
            "points": points,
            "source": "eastmoney",
        }


def _norm_zt(x: dict[str, Any]) -> dict[str, Any]:
    price_raw = fnum(x.get("p"))
    fbt = int(fnum(x.get("fbt")))
    zbc = int(fnum(x.get("zbc")))
    return {
        "code": str(x.get("c") or ""),
        "name": str(x.get("n") or ""),
        "price": price_raw / 1000.0 if price_raw > 100 else price_raw,
        "change_pct": fnum(x.get("zdp")),
        "amount": fnum(x.get("amount")),
        "turnover": fnum(x.get("hs")),
        "seal_amount": fnum(x.get("fund")),
        "first_seal": fbt,
        "last_seal": x.get("lbt"),
        "open_count": zbc,
        "boards": int(fnum(x.get("lbc"))),
        "industry": str(x.get("hybk") or x.get("hy") or x.get("bk") or ""),
        "reason": str(x.get("reason") or x.get("tj") or ""),
        # 竞价封死且未开板：9:25:00~9:25:59
        "is_yizi": 92500 <= fbt <= 92559 and zbc == 0,
    }


def _norm_zb(x: dict[str, Any]) -> dict[str, Any]:
    price_raw = fnum(x.get("p"))
    return {
        "code": str(x.get("c") or ""),
        "name": str(x.get("n") or ""),
        "price": price_raw / 1000.0 if price_raw > 100 else price_raw,
        "change_pct": fnum(x.get("zdp")),
        "turnover": fnum(x.get("hs")),
        "open_count": int(fnum(x.get("zbc"))),
        "industry": str(x.get("hybk") or x.get("hy") or ""),
        "first_seal": x.get("fbt"),
    }


async def market_bundle(date: str) -> dict[str, Any]:
    zt = await zt_pool(date)
    try:
        zb = await zb_pool(date)
    except Exception:  # noqa: BLE001
        zb = []
    try:
        boards = await board_rank(40)
    except Exception:  # noqa: BLE001
        boards = []
    return {
        "source": "eastmoney",
        "date": date,
        "limit_up": [_norm_zt(x) for x in zt],
        "broken": [_norm_zb(x) for x in zb],
        "boards": boards,
    }
"""开盘啦（longhuvip）行情。题材主线、情绪、板块强度比东财行业更接近人看盘。"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Awaitable, Callable

import httpx

from dragon.themes import plate_theme
from dragon.timeutil import CN

HIS = "https://apphis.longhuvip.com/w1/api/index.php"
HQ = "https://apphwhq.longhuvip.com/w1/api/index.php"

UA = "Dalvik/2.1.0 (Linux; U; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736)"

_DEVICE = uuid.uuid4().hex

Factory = Callable[[], Awaitable[dict]]


def dash_date(yyyymmdd: str) -> str:
    s = "".join(ch for ch in (yyyymmdd or "") if ch.isdigit())
    if len(s) == 8:
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return yyyymmdd


def common_params() -> dict[str, str]:
    return {
        "DeviceID": _DEVICE,
        "PhoneOSNew": "2",
        "Token": "",
        "UserID": "0",
        "VerSion": "5.23.0.1",
        "apiv": "w44",
    }


def headers() -> dict[str, str]:
    return {
        "User-Agent": UA,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive",
    }


def ts_to_fbt(ts: int | float | str | None) -> int:
    try:
        n = int(float(ts or 0))
    except (TypeError, ValueError):
        return 0
    if n <= 0:
        return 0
    if n < 10_000_000:
        return n
    dt = datetime.fromtimestamp(n, CN)
    return dt.hour * 10000 + dt.minute * 100 + dt.second


def _num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def rows_from_info(info: Any) -> list[list]:
    """涨停/破板 info 经常是 [[rows...], date]。"""
    if not isinstance(info, list) or not info:
        return []
    first = info[0]
    if isinstance(first, list) and first and isinstance(first[0], list):
        return [r for r in first if isinstance(r, list) and r]
    if isinstance(first, list) and first and isinstance(first[0], str):
        return [r for r in info if isinstance(r, list) and r and isinstance(r[0], str)]
    return []


def client_kwargs() -> dict[str, Any]:
    return {
        "headers": headers(),
        "follow_redirects": True,
        "timeout": httpx.Timeout(14.0, connect=6.0),
        "trust_env": False,
    }


def _ok_payload(data: dict) -> bool:
    if not isinstance(data, dict):
        return False
    if str(data.get("errcode", "0")) in {"0", "0.0"}:
        return True
    return any(data.get(k) for k in ("info", "StockList", "list", "tip"))


async def kpl_get(client: httpx.AsyncClient, url: str, extra: dict[str, Any]) -> dict:
    r = await client.get(url, params={**common_params(), **{k: str(v) for k, v in extra.items()}})
    r.raise_for_status()
    data = r.json()
    if not _ok_payload(data):
        raise RuntimeError(f"kpl {extra.get('a')} err={data.get('errcode')}")
    return data


async def kpl_post(client: httpx.AsyncClient, url: str, extra: dict[str, Any]) -> dict:
    r = await client.post(url, data={**common_params(), **{k: str(v) for k, v in extra.items()}})
    r.raise_for_status()
    data = r.json()
    if not _ok_payload(data):
        raise RuntimeError(f"kpl {extra.get('a')} err={data.get('errcode')}")
    return data


async def first_ok(factories: list[Factory]) -> tuple[dict | None, str | None]:
    last_err = None
    for fac in factories:
        try:
            data = await fac()
            if data:
                return data, None
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
    return None, last_err


def parse_tianti(data: dict) -> tuple[list[dict], list[dict]]:
    stocks = []
    for row in data.get("StockList") or []:
        if not isinstance(row, list) or len(row) < 6:
            continue
        plate = str(row[5] or "")
        stocks.append(
            {
                "code": str(row[0] or "").zfill(6),
                "name": str(row[1] or ""),
                "boards": int(_num(row[2], 1)),
                "first_seal": ts_to_fbt(row[3]),
                "plate_id": str(row[4] or ""),
                "plate": plate,
                "theme": plate_theme(plate),
                "peer_hint": int(_num(row[8] if len(row) > 8 else 0)),
                "amount": _num(row[9] if len(row) > 9 else 0),
                "plate_amount": _num(row[10] if len(row) > 10 else 0),
                "sealed": True,
            }
        )
    zhu = []
    for row in data.get("ZhuShuList") or []:
        if not isinstance(row, list) or len(row) < 3:
            continue
        zhu.append(
            {
                "id": str(row[0] or ""),
                "name": str(row[1] or ""),
                "count": int(_num(row[2])),
                "amount": _num(row[3] if len(row) > 3 else 0),
                "codes": [c.strip() for c in str(row[4] if len(row) > 4 else "").split(",") if c.strip()],
                "theme": plate_theme(str(row[1] or "")),
            }
        )
    return stocks, zhu


def parse_limit_row(row: list) -> dict:
    reason = str(row[5] if len(row) > 5 else "")
    return {
        "code": str(row[0] or "").zfill(6),
        "name": str(row[1] or ""),
        "first_seal": ts_to_fbt(row[4] if len(row) > 4 else 0),
        "reason": reason,
        "seal_fund": _num(row[6] if len(row) > 6 else 0),
        "main_net": _num(row[8] if len(row) > 8 else 0),
        "amount": _num(row[11] if len(row) > 11 else 0),
        "themes": str(row[12] if len(row) > 12 else ""),
        "circ_mv": _num(row[13] if len(row) > 13 else 0),
        "turnover": _num(row[14] if len(row) > 14 else 0),
        "rebound": int(_num(row[16] if len(row) > 16 else 0)),
        "price": _num(row[21] if len(row) > 21 else 0),
        "change_pct": _num(row[22] if len(row) > 22 else 0),
        "theme": plate_theme(reason),
        "sealed": True,
    }


def parse_broken_row(row: list) -> dict:
    themes = str(row[6] if len(row) > 6 else "")
    return {
        "code": str(row[0] or "").zfill(6),
        "name": str(row[1] or ""),
        "price": _num(row[4] if len(row) > 4 else 0),
        "change_pct": _num(row[5] if len(row) > 5 else 0),
        "themes": themes,
        "theme": plate_theme(themes),
        "main_net": _num(row[7] if len(row) > 7 else 0),
        "amount": _num(row[10] if len(row) > 10 else 0),
        "circ_mv": _num(row[11] if len(row) > 11 else 0),
        "turnover": _num(row[12] if len(row) > 12 else 0),
        "sealed": False,
        "open_count": 1,
        "boards": 1,
        "first_seal": 0,
        "industry": themes,
    }


def parse_plates(data: dict) -> list[dict]:
    out = []
    for row in data.get("list") or []:
        if not isinstance(row, list) or len(row) < 4:
            continue
        out.append(
            {
                "id": str(row[0] or ""),
                "name": str(row[1] or ""),
                "strength": _num(row[2]),
                "pct": _num(row[3]),
                "amount": _num(row[5] if len(row) > 5 else 0),
                "main_net": _num(row[6] if len(row) > 6 else 0),
                "theme": plate_theme(str(row[1] or "")),
            }
        )
    return out


def parse_mood(data: dict, day: str | None = None) -> dict | None:
    info = data.get("info")
    rows: list[dict] = []
    if isinstance(info, list):
        rows = [x for x in info if isinstance(x, dict)]
    elif isinstance(info, dict):
        rows = [info]
    if not rows:
        return None
    want = "".join(ch for ch in (day or "") if ch.isdigit())
    row = rows[0]
    if want:
        for item in rows:
            got = "".join(ch for ch in str(item.get("Day") or "") if ch.isdigit())
            if got == want:
                row = item
                break
    return {
        "strong": _num(row.get("strong")),
        "zt": int(_num(row.get("ztjs"))),
        "height": int(_num(row.get("lbgd"))),
        "drawdown": int(_num(row.get("df_num"))),
        "day": str(row.get("Day") or ""),
        "tip": str(data.get("tip") or ""),
    }


def parse_expression(data: dict) -> dict | None:
    info = data.get("info")
    if not isinstance(info, list) or len(info) < 8:
        return None
    return {
        "zt": int(_num(info[0])),
        "two": int(_num(info[1])),
        "three": int(_num(info[2])),
        "max_boards": int(_num(info[3])),
        "promote2": _num(info[4]),
        "promote3": _num(info[5]),
        "broken_rate": _num(info[7]),
        "yest_zt": _num(info[8]) if len(info) > 8 else None,
        "summary": str(info[11]) if len(info) > 11 else "",
    }


def parse_indexes(data: dict) -> list[dict]:
    out = []
    for item in data.get("StockList") or []:
        if not isinstance(item, dict):
            continue
        rate = str(item.get("increase_rate") or "0").replace("%", "")
        out.append(
            {
                "code": str(item.get("StockID") or "").replace("SH", "").replace("SZ", ""),
                "name": str(item.get("prod_name") or ""),
                "pct": _num(rate),
                "price": _num(item.get("last_px")),
            }
        )
    return out


def kpl_row_to_zt(base: dict, extra: dict | None = None) -> dict:
    extra = extra or {}
    plate = base.get("plate") or extra.get("reason") or extra.get("themes") or ""
    return {
        "code": base["code"],
        "name": base.get("name") or extra.get("name") or "",
        "industry": plate,
        "theme": plate_theme(plate) if plate else extra.get("theme") or "未知",
        "price": extra.get("price") or 0,
        "change_pct": extra.get("change_pct") or 0,
        "amount": extra.get("amount") or base.get("amount") or 0,
        "circ_mv": extra.get("circ_mv") or 0,
        "turnover": extra.get("turnover") or 0,
        "boards": int(base.get("boards") or 1),
        "first_seal": int(base.get("first_seal") or extra.get("first_seal") or 0),
        "last_seal": 0,
        "seal_fund": extra.get("seal_fund") or 0,
        # 开盘啦只有「是否回封」，没有炸板次数。缺东财时按未开处理，不拿回封冒充炸次。
        "open_count": 0,
        "sealed": True,
        "reason": extra.get("reason") or plate,
        "kpl_theme": plate,
        "theme_source": "kaipanla",
    }


def plates_as_concepts(plates: list[dict], zhu: list[dict]) -> list[dict]:
    """只把带涨幅的板块强度喂给「板块红不红」。主线家数走天梯，不拿空涨幅的主线列表冒充指数。"""
    zhu_by_name = {z["name"]: z for z in zhu}
    out = []
    for p in plates:
        if p.get("pct") is None:
            continue
        hit = zhu_by_name.get(p["name"]) or {}
        codes = hit.get("codes") or []
        lead = str(codes[0]).zfill(6) if codes else ""
        out.append(
            {
                "f12": p["id"],
                "f14": p["name"],
                "f3": p["pct"],
                "f8": 0,
                "f20": p["amount"],
                "f104": hit.get("count") or 0,
                "f105": 0,
                "f128": "",
                "f140": lead,
                "f141": "",
            }
        )
    return out


def _date_params(day: str) -> dict[str, str]:
    return {"Date": day, "date": day, "Day": day}


async def probe_tianti(client: httpx.AsyncClient, ymd: str) -> list[dict]:
    day = dash_date(ymd)
    extra = {"a": "GetZhangTingTianTi", "c": "FuPanLa", **_date_params(day)}
    data, _err = await first_ok(
        [
            lambda: kpl_post(client, HIS, extra),
            lambda: kpl_post(client, HQ, extra),
        ]
    )
    stocks, _zhu = parse_tianti(data or {})
    return stocks


async def fetch_kpl(client: httpx.AsyncClient, ymd: str, *, latest: bool) -> dict[str, Any]:
    day = dash_date(ymd)
    warnings: list[str] = []
    dates = _date_params(day)

    async def tianti():
        extra = {"a": "GetZhangTingTianTi", "c": "FuPanLa", **dates}
        primary, secondary = (HQ, HIS) if latest else (HIS, HQ)
        data, err = await first_ok(
            [
                lambda: kpl_post(client, primary, extra),
                lambda: kpl_post(client, secondary, extra),
            ]
        )
        if err and not data:
            raise RuntimeError(err)
        return data or {}

    async def mood():
        extra = {"a": "ChangeStatistics", "c": "HisHomeDingPan", "st": "20", "Index": "0", **dates}
        data, err = await first_ok(
            [
                lambda: kpl_get(client, HIS, extra),
                lambda: kpl_get(client, HQ, extra),
            ]
        )
        if err and not data:
            raise RuntimeError(err)
        return data or {}

    async def expr():
        extra = {"a": "ZhangTingExpression", "c": "HisHomeDingPan", **dates}
        data, err = await first_ok(
            [
                lambda: kpl_get(client, HIS, extra),
                lambda: kpl_get(client, HQ, extra),
            ]
        )
        if err and not data:
            raise RuntimeError(err)
        return data or {}

    async def plates():
        extra = {
            "a": "RealRankingInfo",
            "c": "ZhiShuRanking",
            "Type": "1",
            "Order": "1",
            "ZSType": "7",
            "Index": "0",
            "st": "30",
            **dates,
        }
        primary, secondary = (HQ, HIS) if latest else (HIS, HQ)
        data, err = await first_ok(
            [
                lambda: kpl_post(client, primary, extra),
                lambda: kpl_post(client, secondary, extra),
            ]
        )
        if err and not data:
            raise RuntimeError(err)
        return data or {}

    async def indexes():
        extra = {
            "a": "RefreshStockList",
            "c": "UserSelectStock",
            "StockIDList": "SH000001,SZ399001,SZ399006,SH000688",
        }
        data, err = await first_ok(
            [
                lambda: kpl_post(client, HQ, extra),
                lambda: kpl_post(client, HIS, extra),
            ]
        )
        if err and not data:
            raise RuntimeError(err)
        return data or {}

    async def one_limit(pid: int) -> list[dict]:
        extra = {
            "a": "DailyLimitPerformance",
            "c": "HomeDingPan" if latest else "HisHomeDingPan",
            "PidType": str(pid),
            "Type": "4",
            "Index": "0",
            "Order": "0",
            "st": "200",
            **dates,
        }
        primary, secondary = (HQ, HIS) if latest else (HIS, HQ)
        data, err = await first_ok(
            [
                lambda e=extra, u=primary: kpl_get(client, u, e),
                lambda: kpl_get(
                    client,
                    secondary,
                    {**extra, "c": "HisHomeDingPan"},
                ),
            ]
        )
        if err and not data:
            raise RuntimeError(err)
        return [parse_limit_row(r) for r in rows_from_info((data or {}).get("info"))]

    async def limits():
        chunks = await asyncio.gather(*[one_limit(pid) for pid in range(1, 6)], return_exceptions=True)
        rows = []
        for i, chunk in enumerate(chunks, 1):
            if isinstance(chunk, Exception):
                warnings.append(f"开盘啦涨停明细{i}板失败：{chunk}")
                continue
            rows.extend(chunk)
        return rows

    async def broken():
        extra = {
            "a": "DailyLimitPerformance2",
            "c": "HisHomeDingPan",
            "PidType": "1",
            "Type": "5",
            "Index": "0",
            "Order": "1",
            "st": "200",
            **dates,
        }
        data, err = await first_ok(
            [
                lambda: kpl_get(client, HIS, extra),
                lambda: kpl_get(client, HQ, {**extra, "c": "HomeDingPan"}),
            ]
        )
        if err and not data:
            raise RuntimeError(err)
        return [parse_broken_row(r) for r in rows_from_info((data or {}).get("info"))]

    out: dict[str, Any] = {
        "tianti": [],
        "zhu": [],
        "details": {},
        "broken": [],
        "plates": [],
        "mood": None,
        "expression": None,
        "indexes": [],
        "warnings": warnings,
    }

    async def grab(name: str, coro):
        try:
            return name, await coro
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"开盘啦{name}失败：{exc}")
            return name, None

    parts = await asyncio.gather(
        grab("天梯", tianti()),
        grab("情绪", mood()),
        grab("涨停表现", expr()),
        grab("板块强度", plates()),
        grab("指数", indexes()),
        grab("涨停明细", limits()),
        grab("破板", broken()),
    )
    got = {k: v for k, v in parts}
    if got.get("天梯"):
        out["tianti"], out["zhu"] = parse_tianti(got["天梯"])
    if got.get("情绪"):
        out["mood"] = parse_mood(got["情绪"], day)
    if got.get("涨停表现"):
        out["expression"] = parse_expression(got["涨停表现"])
    if got.get("板块强度"):
        out["plates"] = parse_plates(got["板块强度"])
    if got.get("指数"):
        out["indexes"] = parse_indexes(got["指数"])
    if got.get("涨停明细"):
        out["details"] = {r["code"]: r for r in got["涨停明细"] or []}
    if got.get("破板"):
        out["broken"] = got["破板"]
    return out

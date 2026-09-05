"""三条纪律看板 — 本地 FastAPI 服务（venv 一键启动）。"""
from __future__ import annotations

import json
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any

import httpx
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
CN_TZ = timezone(timedelta(hours=8))
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
DEFAULT_WATCH = ["600519", "000001", "300750", "002594", "600900"]
INDEXES = {"sh": "sh000001", "cyb": "sz399006"}

app = FastAPI(title="三条纪律看板")


# ---------- helpers ----------
def now_iso() -> str:
    return datetime.now(CN_TZ).isoformat()


def today_ymd() -> str:
    return datetime.now(CN_TZ).strftime("%Y%m%d")


def to_market(code: str) -> tuple[str, str, str]:
    raw = str(code).strip()
    lower = raw.lower()
    digits = re.sub(r"\D", "", raw).zfill(6)[-6:]
    if lower.startswith("sh") or lower.endswith(".sh") or lower.startswith("1."):
        return digits, "sh", "sh"
    if lower.startswith("sz") or lower.endswith(".sz") or lower.startswith("0."):
        return digits, "sz", "sz"
    if digits.startswith(("6", "9")):
        return digits, "sh", "sh"
    return digits, "sz", "sz"


def to_tencent(code: str) -> str:
    s = str(code).lower()
    if s in {"sh000001", "000001.sh", "1.000001"}:
        return "sh000001"
    if s in {"sz399006", "399006.sz", "0.399006"}:
        return "sz399006"
    if s.startswith(("sh", "sz")):
        return re.sub(r"\W", "", s)
    c, _, p = to_market(code)
    return f"{p}{c}"


def pct(a, b):
    if a is None or b in (None, 0):
        return None
    return (float(a) - float(b)) / float(b) * 100


def r2(n, d=2):
    if n is None or (isinstance(n, float) and math.isnan(n)):
        return None
    return round(float(n), d)


def sma(vals, n):
    if not vals or len(vals) < n:
        return None
    chunk = vals[-n:]
    return sum(chunk) / n


def parse_boards(text) -> int:
    if not text:
        return 1
    s = str(text)
    if "首板" in s or s == "1":
        return 1
    m = re.search(r"(\d+)\s*板", s)
    if m:
        return int(m.group(1))
    try:
        return int(float(s))
    except ValueError:
        return 1


def num(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def make_quote(**kw) -> dict:
    code = kw.get("code")
    name = kw.get("name") or code
    price = kw.get("price")
    open_ = kw.get("open_")
    prev = kw.get("prev_close") or open_ or price
    high = kw.get("high")
    low = kw.get("low")
    chg = kw.get("change_pct")
    if chg is None:
        chg = pct(price, prev)
    from_high = pct(price, high) if high else None
    from_low = pct(price, low) if low else None
    day_pos = None
    if high is not None and low is not None and high != low and price is not None:
        day_pos = (price - low) / (high - low)
    ma5 = kw.get("ma5")
    ma5_dist = pct(price, ma5) if ma5 is not None else None

    status, reason = "neutral", "价格处于日内中位，观望"
    if from_high is not None and from_low is not None:
        if from_high >= -0.8 and (chg or 0) > 5:
            status, reason = "chase", f"距日内高点仅 {abs(from_high):.2f}%，追高区，禁止低吸"
        elif ma5 is not None and ma5_dist is not None and -3 <= ma5_dist <= 0.6:
            status, reason = "ok", f"贴近/回踩 MA5（距均线 {ma5_dist:.2f}%），符合低吸纪律"
        elif from_low <= 1.2 or (day_pos is not None and day_pos <= 0.28):
            status, reason = "ok", f"贴近日内低点（距低 {abs(from_low):.2f}%），符合低吸纪律"
        elif ma5_dist is not None and ma5_dist > 3 and day_pos is not None and day_pos > 0.7:
            status, reason = "chase", f"远离 MA5 上方 {ma5_dist:.2f}% 且贴近高点，勿追"
        elif (chg or 0) < -3 and from_high <= -2:
            status, reason = "ok", f"回调 {abs(chg):.2f}% 且离高点较远，可评估低吸"
        elif ma5_dist is not None:
            reason = f"距 MA5 {ma5_dist:.2f}%，未到低吸位，继续等待"

    return {
        "code": code,
        "name": name,
        "price": r2(price),
        "open": r2(open_),
        "prevClose": r2(prev),
        "high": r2(high),
        "low": r2(low),
        "changePct": r2(chg),
        "volume": kw.get("volume"),
        "amount": kw.get("amount"),
        "time": kw.get("time"),
        "ma5": r2(ma5),
        "ma5DistPct": r2(ma5_dist),
        "fromHighPct": r2(from_high),
        "fromLowPct": r2(from_low),
        "dayRangePos": r2(day_pos, 3),
        "lowBuyStatus": status,
        "lowBuyReason": reason,
    }


def drawdown_from_high(klines: list[dict]) -> dict | None:
    if not klines:
        return None
    peak, peak_date = -1e18, None
    for k in klines:
        h = k.get("high", k.get("close"))
        if h is not None and h > peak:
            peak, peak_date = h, k.get("date")
    last = klines[-1]
    price = last.get("close")
    return {
        "peak": r2(peak),
        "peakDate": peak_date,
        "price": r2(price),
        "date": last.get("date"),
        "drawdownPct": r2(pct(price, peak)),
    }


def freeze_by_dd(dd, soft=-3.0, hard=-5.0) -> dict:
    if dd is None:
        return {"level": "unknown", "label": "无数据", "action": "等待行情", "reason": "暂无回撤数据"}
    if dd <= hard:
        return {
            "level": "hard",
            "label": "硬冻结",
            "action": "禁止新开仓 / 不加仓",
            "reason": f"相对近期高点回撤 {dd:.2f}% ≤ {hard}%：只准守，不准动",
        }
    if dd <= soft:
        return {
            "level": "soft",
            "label": "软冻结",
            "action": "暂停新开仓，仅允许减仓",
            "reason": f"相对近期高点回撤 {dd:.2f}% ≤ {soft}%：回撤区，别乱动",
        }
    return {
        "level": "ok",
        "label": "可操作",
        "action": "可按低吸纪律交易",
        "reason": f"回撤 {dd:.2f}%，未触发冻结线（软 {soft}% / 硬 {hard}%）",
    }


def http_json(url: str, headers: dict | None = None) -> Any:
    with httpx.Client(timeout=12, headers={"User-Agent": UA}, follow_redirects=True) as c:
        r = c.get(url, headers=headers or {})
        r.raise_for_status()
        return r.json()


def http_text(url: str, headers: dict | None = None, encoding: str | None = None) -> str:
    with httpx.Client(timeout=12, headers={"User-Agent": UA}, follow_redirects=True) as c:
        r = c.get(url, headers=headers or {})
        r.raise_for_status()
        if encoding:
            return r.content.decode(encoding, errors="ignore")
        return r.text


# ---------- 东方财富 ----------
def em_quotes(codes: list[str]) -> list[dict]:
    secids = []
    for raw in codes:
        c, m, _ = to_market(raw)
        secids.append(f"{1 if m == 'sh' else 0}.{c}")
    url = (
        "https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&invt=2"
        f"&secids={','.join(secids)}&fields=f12,f14,f2,f3,f15,f16,f17,f18,f5,f6"
        f"&ut=fa5fd1943c7b386f172d6893dbfba10b&_={int(time.time()*1000)}"
    )
    data = http_json(url, {"Referer": "https://quote.eastmoney.com/"})
    rows = (data.get("data") or {}).get("diff") or []
    if not rows:
        raise RuntimeError("东方财富行情为空")
    return [
        make_quote(
            code=r.get("f12"),
            name=r.get("f14"),
            price=num(r.get("f2")),
            change_pct=num(r.get("f3")),
            high=num(r.get("f15")),
            low=num(r.get("f16")),
            open_=num(r.get("f17")),
            prev_close=num(r.get("f18")),
            volume=num(r.get("f5")),
            amount=num(r.get("f6")),
        )
        for r in rows
    ]


def em_kline(code: str, lmt: int = 60) -> list[dict]:
    c, m, _ = to_market(code)
    secid = f"{1 if m == 'sh' else 0}.{c}"
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6"
        "&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&end=20500101"
        f"&lmt={lmt}&ut=fa5fd1943c7b386f172d6893dbfba10b"
    )
    data = http_json(url, {"Referer": "https://quote.eastmoney.com/"})
    kl = (data.get("data") or {}).get("klines") or []
    if not kl:
        raise RuntimeError("东方财富K线为空")
    out = []
    for line in kl:
        p = line.split(",")
        out.append(
            {
                "date": p[0],
                "open": float(p[1]),
                "close": float(p[2]),
                "high": float(p[3]),
                "low": float(p[4]),
                "volume": float(p[5]) if len(p) > 5 else 0,
            }
        )
    return out


def em_limit_up(trade_date: str | None = None) -> list[dict]:
    day = trade_date or today_ymd()
    url = (
        "https://push2ex.eastmoney.com/getTopicZTPool"
        "?ut=7eea3edcaed734bea9cbfc24410557a5&dpt=wz.ztzt"
        f"&Pageindex=0&pagesize=200&sort=fbt:asc&date={day}&_={int(time.time()*1000)}"
    )
    data = http_json(url, {"Referer": "https://quote.eastmoney.com/ztb/detail"})
    pool = (data.get("data") or {}).get("pool") or []
    if not pool:
        raise RuntimeError("东方财富涨停池为空")
    out = []
    for r in pool:
        b = int(r.get("lbc") or 1)
        out.append(
            {
                "code": r.get("c"),
                "name": r.get("n"),
                "price": r.get("p"),
                "changePct": r.get("zdp"),
                "boards": b,
                "highDays": "首板" if b == 1 else f"{b}板",
                "reason": r.get("hybk") or r.get("n"),
                "source": "eastmoney",
            }
        )
    return out


# ---------- 同花顺 ----------
def ths_sym(code: str) -> str:
    c, m, _ = to_market(code)
    if c == "000001" and m == "sh":
        return "hs_1A0001"
    if c == "399006":
        return "hs_399006"
    return f"hs_{c}" if m == "sh" else f"sz_{c}"


def ths_quotes(codes: list[str]) -> list[dict]:
    out = []
    for raw in codes:
        c, _, _ = to_market(raw)
        url = f"https://d.10jqka.com.cn/v2/realhead/{ths_sym(raw)}/last.js?_={int(time.time()*1000)}"
        text = http_text(url, {"Referer": "https://q.10jqka.com.cn/"})
        m = re.search(r"last\((\{[\s\S]*\})\)\s*;?\s*$", text)
        if not m:
            raise RuntimeError(f"同花顺解析失败 {c}")
        items = json.loads(m.group(1)).get("items") or {}
        price = num(items.get("10")) or 0
        open_ = num(items.get("7")) or 0
        prev = num(items.get("6")) or open_
        out.append(
            make_quote(
                code=c,
                name=str(items.get("name") or items.get("55") or c),
                price=price,
                high=num(items.get("8")),
                low=num(items.get("9")),
                open_=open_,
                prev_close=prev,
                change_pct=pct(price, prev),
                volume=num(items.get("13")),
                amount=num(items.get("19")),
            )
        )
    return out


def ths_kline(code: str, lmt: int = 60) -> list[dict]:
    url = f"https://d.10jqka.com.cn/v6/line/{ths_sym(code)}/01/last.js?_={int(time.time()*1000)}"
    text = http_text(url, {"Referer": "https://q.10jqka.com.cn/"})
    m = re.search(r"last\((\{[\s\S]*\})\)\s*;?\s*$", text)
    if not m:
        raise RuntimeError("同花顺K线解析失败")
    raw = json.loads(m.group(1)).get("data") or ""
    out = []
    for row in [x for x in raw.split(";") if x][-lmt:]:
        p = row.split(",")
        if len(p) < 6:
            continue
        d, o, h, l, c, v = p[:6]
        out.append(
            {
                "date": f"{d[:4]}-{d[4:6]}-{d[6:8]}",
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
                "volume": float(v or 0),
            }
        )
    if not out:
        raise RuntimeError("同花顺K线为空")
    return out


def ths_limit_up() -> list[dict]:
    url = (
        "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page=1&limit=200"
        "&field=199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003"
        "&filter=HS,GEM2STAR&order_field=330324&order_type=0"
    )
    data = http_json(url, {"Referer": "https://data.10jqka.com.cn/"})
    info = (data.get("data") or {}).get("info") or []
    if not info:
        raise RuntimeError("同花顺涨停池为空")
    return [
        {
            "code": r.get("code"),
            "name": r.get("name"),
            "price": r.get("latest"),
            "changePct": r.get("change_rate"),
            "boards": parse_boards(r.get("high_days")),
            "highDays": r.get("high_days"),
            "reason": r.get("reason_type") or r.get("limit_up_type"),
            "source": "tonghuashun",
        }
        for r in info
    ]


# ---------- 通达信兼容：腾讯 ----------
def tdx_quotes(codes: list[str]) -> list[dict]:
    url = f"https://qt.gtimg.cn/q={','.join(to_tencent(c) for c in codes)}&_={int(time.time()*1000)}"
    text = http_text(url, {"Referer": "https://finance.qq.com/"}, encoding="gbk")
    out = []
    for line in text.splitlines():
        if "=" not in line:
            continue
        body = line.split("=", 1)[1].strip().strip(";").strip('"')
        if not body:
            continue
        p = body.split("~")
        if len(p) < 40:
            continue
        out.append(
            make_quote(
                code=p[2],
                name=p[1],
                price=num(p[3]),
                prev_close=num(p[4]),
                open_=num(p[5]),
                high=num(p[33]),
                low=num(p[34]),
                change_pct=num(p[32]),
                volume=num(p[36]) or num(p[6]),
                amount=num(p[37]),
                time=p[30],
            )
        )
    if not out:
        raise RuntimeError("通达信兼容源（腾讯）行情为空")
    return out


def tdx_kline(code: str, lmt: int = 60) -> list[dict]:
    symbol = to_tencent(code)
    url = (
        "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        f"CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={lmt}"
    )
    text = http_text(url, {"Referer": "https://finance.sina.com.cn/"})
    arr = json.loads(text)
    if not isinstance(arr, list) or not arr:
        raise RuntimeError("通达信兼容K线为空")
    return [
        {
            "date": k["day"],
            "open": float(k["open"]),
            "high": float(k["high"]),
            "low": float(k["low"]),
            "close": float(k["close"]),
            "volume": float(k.get("volume") or 0),
        }
        for k in arr
    ]


def tdx_limit_up() -> list[dict]:
    pool = ths_limit_up()
    for x in pool:
        x["source"] = "tongdaxin+ths_pool"
    return pool


SOURCES = {
    "eastmoney": {
        "id": "eastmoney",
        "label": "东方财富",
        "quotes": em_quotes,
        "kline": em_kline,
        "limit_up": em_limit_up,
    },
    "tonghuashun": {
        "id": "tonghuashun",
        "label": "同花顺",
        "quotes": ths_quotes,
        "kline": ths_kline,
        "limit_up": ths_limit_up,
    },
    "tongdaxin": {
        "id": "tongdaxin",
        "label": "通达信兼容（腾讯）",
        "quotes": tdx_quotes,
        "kline": tdx_kline,
        "limit_up": tdx_limit_up,
    },
}


def with_fallback(primary: str, method: str, *args):
    order = [primary, "tongdaxin", "tonghuashun", "eastmoney"]
    seen, errors = set(), []
    for sid in order:
        if sid in seen:
            continue
        seen.add(sid)
        src = SOURCES.get(sid)
        if not src or method not in src:
            continue
        try:
            return src[method](*args), sid, src["label"], errors
        except Exception as e:  # noqa: BLE001
            errors.append({"source": sid, "message": str(e)})
    raise RuntimeError(" | ".join(f"{e['source']}: {e['message']}" for e in errors) or "全部数据源失败")


def attach_ma5(quotes: list[dict], used: str) -> list[dict]:
    """逐票补 MA5；并发拉取，避免串行卡顿。"""

    def one(q: dict) -> dict:
        try:
            kl, _, _, _ = with_fallback(used, "kline", q["code"], 30)
            ma5v = sma([float(k["close"]) for k in kl], 5)
            return make_quote(
                code=q["code"],
                name=q.get("name"),
                price=q.get("price"),
                open_=q.get("open"),
                prev_close=q.get("prevClose"),
                high=q.get("high"),
                low=q.get("low"),
                change_pct=q.get("changePct"),
                volume=q.get("volume"),
                amount=q.get("amount"),
                time=q.get("time"),
                ma5=ma5v,
            )
        except Exception:  # noqa: BLE001
            return q

    if not quotes:
        return []
    out: list[dict | None] = [None] * len(quotes)
    with ThreadPoolExecutor(max_workers=min(8, len(quotes))) as pool:
        futs = {pool.submit(one, q): i for i, q in enumerate(quotes)}
        for fut in as_completed(futs):
            out[futs[fut]] = fut.result()
    return [x for x in out if x is not None]


def parse_codes(raw: str | None) -> list[str]:
    if not raw or not str(raw).strip():
        return list(DEFAULT_WATCH)
    codes = []
    seen = set()
    for x in re.split(r"[,，\s]+", str(raw)):
        d = re.sub(r"\D", "", x.strip())
        if not d:
            continue
        c = d.zfill(6)[-6:]
        if c not in seen:
            seen.add(c)
            codes.append(c)
    return codes or list(DEFAULT_WATCH)


def collect_focus_codes(primary: str, extra: list[str] | None = None, limit: int = 24) -> list[dict]:
    """二三板 + 观察票，供回撤个股列表。"""
    rows: list[dict] = []
    seen: set[str] = set()
    try:
        pool, _, _, _ = with_fallback(primary, "limit_up")
        for x in pool:
            b = int(x.get("boards") or parse_boards(x.get("highDays")))
            if b not in (2, 3):
                continue
            code = re.sub(r"\D", "", str(x.get("code") or "")).zfill(6)[-6:]
            if not code or code in seen:
                continue
            seen.add(code)
            rows.append(
                {
                    "code": code,
                    "name": x.get("name") or code,
                    "boards": b,
                    "highDays": x.get("highDays"),
                    "changePct": x.get("changePct"),
                    "from": "boards",
                }
            )
            if len(rows) >= limit:
                break
    except Exception:  # noqa: BLE001
        pass
    for raw in extra or []:
        code = re.sub(r"\D", "", str(raw)).zfill(6)[-6:]
        if not code or code in seen:
            continue
        seen.add(code)
        rows.append({"code": code, "name": code, "boards": None, "from": "watch"})
        if len(rows) >= limit + 10:
            break
    return rows


def stock_drawdown_rows(
    items: list[dict],
    primary: str,
    soft: float,
    hard: float,
    days: int,
) -> list[dict]:
    """个股相对近 N 日高点回撤 + 冻结建议。"""

    def one(item: dict) -> dict | None:
        code = item["code"]
        try:
            kl, used, label, _ = with_fallback(primary, "kline", code, days)
            dd = drawdown_from_high(kl)
            fr = freeze_by_dd(dd.get("drawdownPct") if dd else None, soft, hard)
            name = item.get("name") or code
            # 用最新行情补名称/涨跌（可选，失败忽略）
            return {
                "code": code,
                "name": name,
                "boards": item.get("boards"),
                "highDays": item.get("highDays"),
                "from": item.get("from") or "boards",
                "source": used,
                "sourceLabel": label,
                "drawdown": dd,
                "freeze": fr,
                "changePct": item.get("changePct"),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "code": code,
                "name": item.get("name") or code,
                "boards": item.get("boards"),
                "from": item.get("from") or "boards",
                "drawdown": None,
                "freeze": {"level": "unknown", "label": "无数据", "action": "等待", "reason": str(exc)},
                "changePct": item.get("changePct"),
            }

    if not items:
        return []
    out: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(8, len(items))) as pool:
        futs = [pool.submit(one, it) for it in items]
        for fut in as_completed(futs):
            row = fut.result()
            if row:
                out.append(row)
    rank = {"hard": 3, "soft": 2, "ok": 1, "unknown": 0}
    out.sort(
        key=lambda x: (
            -rank.get((x.get("freeze") or {}).get("level"), 0),
            (x.get("drawdown") or {}).get("drawdownPct") or 0,
        )
    )
    # 补行情名称/涨跌
    try:
        codes = [x["code"] for x in out]
        quotes, _, _, _ = with_fallback(primary, "quotes", codes)
        qmap = {str(q["code"]): q for q in quotes}
        for x in out:
            q = qmap.get(str(x["code"]))
            if not q:
                continue
            if q.get("name"):
                x["name"] = q["name"]
            if q.get("changePct") is not None:
                x["changePct"] = q["changePct"]
            if q.get("price") is not None:
                x["price"] = q["price"]
    except Exception:  # noqa: BLE001
        pass
    return out


# ---------- API ----------
@app.get("/api/health")
def health():
    return {"ok": True, "sources": list(SOURCES)}


@app.get("/api/sources")
def sources():
    return {
        "sources": [{"id": s["id"], "label": s["label"]} for s in SOURCES.values()],
        "note": "通达信项用腾讯财经免费行情；涨停池在东方财富不可用时自动回退同花顺。失败自动切换。",
    }


@app.get("/api/discipline/low-buy")
def low_buy(
    source: Annotated[str, Query()] = "tongdaxin",
    codes: Annotated[str, Query()] = "",
):
    primary = source if source in SOURCES else "tongdaxin"
    code_list = parse_codes(codes)
    data, used, label, errors = with_fallback(primary, "quotes", code_list)
    with_ma = attach_ma5(data, used)
    summary = {
        "ok": sum(1 for x in with_ma if x["lowBuyStatus"] == "ok"),
        "chase": sum(1 for x in with_ma if x["lowBuyStatus"] == "chase"),
        "neutral": sum(1 for x in with_ma if x["lowBuyStatus"] == "neutral"),
    }
    return {
        "source": used,
        "sourceLabel": label,
        "rule": {
            "title": "低吸纪律",
            "bullets": [
                "优先回踩 / 贴近 MA5，而不是追着涨停买",
                "只买贴近日内低点或均线支撑的位置，不买贴近日内高点的票",
                "涨幅已大且价格在日内高位区间 → 追高区，禁止低吸",
                "一句话：低吸是买「便宜的相对位置」，不是买「便宜的名字」",
            ],
        },
        "summary": summary,
        "quotes": with_ma,
        "fallbackErrors": errors,
        "updatedAt": now_iso(),
    }


@app.get("/api/discipline/boards")
def boards(
    source: Annotated[str, Query()] = "tongdaxin",
    date: Annotated[str, Query()] = "",
):
    primary = source if source in SOURCES else "tongdaxin"
    trade_date = date.strip() if date and len(date.strip()) == 8 else None
    try:
        if primary == "eastmoney" and trade_date:
            data, used, label, errors = em_limit_up(trade_date), "eastmoney", SOURCES["eastmoney"]["label"], []
        else:
            data, used, label, errors = with_fallback(primary, "limit_up")
            if trade_date and used == "eastmoney":
                data = em_limit_up(trade_date)
    except Exception:
        data, used, label, errors = with_fallback(primary, "limit_up")
    enriched = []
    for x in data:
        b = int(x.get("boards") or parse_boards(x.get("highDays")))
        enriched.append({**x, "boards": b})
    b1 = [x for x in enriched if x["boards"] == 1]
    b2 = [x for x in enriched if x["boards"] == 2]
    b3 = [x for x in enriched if x["boards"] == 3]
    b4 = [x for x in enriched if x["boards"] >= 4]
    total = len(enriched) or 1
    focus = len(b2) + len(b3)
    code, lab, reason = "mixed", "结构一般", f"二板 {len(b2)} / 三板 {len(b3)} / 首板 {len(b1)}，按个股质量选"
    if len(b2) >= 3 and len(b3) >= 1:
        code, lab, reason = "healthy", "二三板活跃", f"二板 {len(b2)} / 三板 {len(b3)}，梯队成形，短线情绪健康"
    elif len(b2) >= 2 and len(b3) == 0:
        code, lab, reason = "early", "二板试错期", f"二板 {len(b2)}、三板 0，情绪偏早"
    elif len(b1) / total > 0.75 and focus <= 1:
        code, lab, reason = "weak", "高度不足", "首板占比过高、二三板稀缺，节奏偏弱"
    elif len(b4) >= 2 and len(b2) <= 1:
        code, lab, reason = "fragile", "高位独苗", "高位板多但二三板断层，龙头容易核"
    # 轻量标签：仅用日内行情，不逐票拉 K 线（避免看板卡顿）
    focus_codes = [x["code"] for x in (b2[:20] + b3[:20]) if x.get("code")]
    action_map: dict[str, dict] = {}
    if focus_codes:
        try:
            qdata, _, _, _ = with_fallback(primary, "quotes", focus_codes)
            for q in qdata:
                st = q.get("lowBuyStatus") or "neutral"
                if st == "ok":
                    tag, tag_label = "ok", "可买入"
                elif st == "chase":
                    tag, tag_label = "chase", "勿追高"
                else:
                    tag, tag_label = "watch", "观察"
                action_map[str(q["code"])] = {
                    "action": tag,
                    "actionLabel": tag_label,
                    "actionReason": q.get("lowBuyReason") or "",
                    "ma5": q.get("ma5"),
                    "ma5DistPct": q.get("ma5DistPct"),
                    "dayRangePos": q.get("dayRangePos"),
                    "changePct": q.get("changePct"),
                    "price": q.get("price"),
                    "reason": q.get("lowBuyReason") or "",
                }
        except Exception as exc:  # noqa: BLE001
            errors.append({"stage": "action_tag", "message": str(exc)})

    def _tag(rows: list[dict]) -> list[dict]:
        out = []
        for x in rows:
            info = action_map.get(str(x.get("code")), {})
            out.append(
                {
                    **x,
                    **info,
                    "action": info.get("action") or "watch",
                    "actionLabel": info.get("actionLabel") or "观察",
                    "reason": info.get("reason") or x.get("reason") or "",
                }
            )
        return out

    b2, b3 = _tag(b2), _tag(b3)

    return {
        "source": used,
        "sourceLabel": label,
        "date": trade_date or today_ymd(),
        "rule": {
            "title": "二三板节奏",
            "bullets": [
                "连板关键观察点在二板、三板，不是一板盲冲",
                "二板≥3 且三板≥1 → 梯队健康，可做情绪接力",
                "只有首板、高度上不去 → 节奏弱，降低仓位与频率",
                "高位独苗（4板以上多、二三板断层）→ 脆弱，防核按钮",
            ],
        },
        "rhythm": {"code": code, "label": lab, "reason": reason},
        "stats": {
            "total": len(enriched),
            "board1": len(b1),
            "board2": len(b2),
            "board3": len(b3),
            "board4p": len(b4),
        },
        "focus": {"board2": b2[:20], "board3": b3[:20]},
        "all": enriched,
        "fallbackErrors": errors,
        "updatedAt": now_iso(),
    }


@app.get("/api/discipline/drawdown")
def drawdown(
    source: Annotated[str, Query()] = "tongdaxin",
    soft: Annotated[float, Query()] = -3,
    hard: Annotated[float, Query()] = -5,
    days: Annotated[int, Query()] = 20,
    codes: Annotated[str, Query()] = "",
):
    primary = source if source in SOURCES else "tongdaxin"
    results, errors = [], []
    for tid, name, code in (("sh", "上证指数", INDEXES["sh"]), ("cyb", "创业板指", INDEXES["cyb"])):
        try:
            kl, used, label, _ = with_fallback(primary, "kline", code, days)
            dd = drawdown_from_high(kl)
            fr = freeze_by_dd(dd.get("drawdownPct") if dd else None, soft, hard)
            results.append(
                {
                    "id": tid,
                    "name": name,
                    "code": code,
                    "source": used,
                    "sourceLabel": label,
                    "drawdown": dd,
                    "freeze": fr,
                    "recent": kl[-8:],
                }
            )
        except Exception as e:  # noqa: BLE001
            errors.append({"target": tid, "message": str(e)})
    rank = {"hard": 3, "soft": 2, "ok": 1, "unknown": 0}
    worst = (
        max(results, key=lambda x: rank.get(x["freeze"]["level"], 0))
        if results
        else {"freeze": {"level": "unknown", "label": "无数据", "action": "等待", "reason": ""}}
    )

    watch = parse_codes(codes) if codes.strip() else []
    # 默认展示二三板个股回撤；观察栏代码一并并入
    focus_items = collect_focus_codes(primary, extra=watch, limit=24)
    stocks = stock_drawdown_rows(focus_items, primary, soft, hard, days)
    stock_summary = {
        "hard": sum(1 for x in stocks if (x.get("freeze") or {}).get("level") == "hard"),
        "soft": sum(1 for x in stocks if (x.get("freeze") or {}).get("level") == "soft"),
        "ok": sum(1 for x in stocks if (x.get("freeze") or {}).get("level") == "ok"),
        "total": len(stocks),
    }

    return {
        "source": primary,
        "sourceLabel": SOURCES[primary]["label"],
        "rule": {
            "title": "回撤时别乱动",
            "bullets": [
                f"相对近 {days} 日高点回撤 ≤ {soft}%：软冻结——暂停新开仓",
                f"回撤 ≤ {hard}%：硬冻结——禁止新开仓/加仓，只准防守",
                "回撤区最常见亏法：忍不住「补仓摊薄」和「换股乱动」",
                "个股与指数分开看：指数可操作 ≠ 个股可乱动；个股硬冻结优先守",
            ],
        },
        "thresholds": {"soft": soft, "hard": hard, "days": days},
        "overall": worst["freeze"],
        "indices": results,
        "stocks": stocks,
        "stockSummary": stock_summary,
        "fallbackErrors": errors,
        "updatedAt": now_iso(),
    }


@app.get("/api/dates")
def api_dates(limit: Annotated[int, Query(ge=1, le=120)] = 40):
    from backend import panel_data as pd

    items = pd.recent_trade_dates(limit)
    return {
        "dates": items,
        "today": today_ymd(),
        "default": items[0]["date"] if items else today_ymd(),
    }


@app.get("/api/panel/{code}")
def api_panel(
    code: str,
    source: Annotated[str, Query()] = "tdx",
):
    """Tick Stock Panel：强制通达信 TCP（eltdx），不回退东财冒充。"""
    from backend import panel_data as pd

    data = pd.build_panel(code, source="tdx")
    data["tdxHost"] = data.get("tdx_host") or pd.TDX_HOST
    data["tdxConnected"] = bool(data.get("tdxConnected"))
    data["daySource"] = "tdx"
    data["errors"] = data.get("errors") or []
    if not data.get("ok"):
        return JSONResponse(data, status_code=502)
    return data


@app.get("/")
def index_page():
    return FileResponse(WEB / "index.html")


# static last so /api keeps priority
app.mount("/assets-static", StaticFiles(directory=str(WEB)), name="assets_static")


@app.get("/{path:path}")
def static_fallback(path: str):
    # serve web files for /app.js /styles.css /vendor/...
    target = (WEB / path).resolve()
    if str(target).startswith(str(WEB.resolve())) and target.is_file():
        return FileResponse(target)
    return JSONResponse({"error": "not found"}, status_code=404)

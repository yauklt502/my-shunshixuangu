"""极速精简选股·趋势王 — pytdx 直连多线程版（与桌面脚本同逻辑）."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from src.data_source.tdx_source import (
    TDX_PORT,
    _market_of,
    get_api,
    get_server_info,
    pick_server,
)

logger = logging.getLogger(__name__)

STRATEGY_ID = "trend_king"
STRATEGY_NAME = "趋势王·稳健精选"
MAX_WORKERS = 10
TOP_N = 5

VALID_PREFIX = ("600", "601", "603", "605", "000", "001", "002")


def _get_all_mainboard() -> dict[str, str]:
    from pytdx.hq import TdxHq_API

    ip = pick_server()
    if not ip:
        return {}
    api = TdxHq_API(heartbeat=True)
    if not api.connect(ip, TDX_PORT, time_out=5):
        return {}
    result: dict[str, str] = {}
    try:
        for market in (1, 0):
            cnt = api.get_security_count(market)
            start = 0
            while start < cnt:
                lst = api.get_security_list(market, start)
                start += 1000
                if not lst:
                    continue
                for item in lst:
                    code = str(item["code"]).zfill(6)
                    name = item.get("name") or code
                    if not code.startswith(VALID_PREFIX):
                        continue
                    if "ST" in name or "退" in name:
                        continue
                    result[code] = name
    finally:
        api.disconnect()
    return result


def _batch_quotes(pairs: list[tuple[int, str]]) -> list[dict]:
    api = get_api()
    out: list[dict] = []
    for i in range(0, len(pairs), 80):
        chunk = pairs[i : i + 80]
        try:
            q = api.get_security_quotes(chunk)
            if q:
                out.extend(q)
        except Exception:
            pass
    return out


def _get_ma_data(code: str) -> tuple[float, float, float, float, float]:
    try:
        api = get_api()
        market = _market_of(code)
        bars = api.get_security_bars(9, market, code, 0, 130)
        if not bars or len(bars) < 120:
            return 0.0, 0.0, 0.0, 0.0, 1.0
        closes = [float(b["close"]) for b in bars]
        vols = [float(b["vol"]) for b in bars]

        def ma(seq: list[float], n: int, shift: int = 0) -> float:
            seg = seq[-(n + shift) : len(seq) - shift] if shift else seq[-n:]
            return sum(seg) / n

        ma20 = ma(closes, 20)
        ma60 = ma(closes, 60)
        ma120 = ma(closes, 120)
        ma60_last = ma(closes, 60, shift=1)
        vol_ratio = 1.0
        if len(vols) >= 6:
            prev5 = sum(vols[-6:-1]) / 5
            if prev5 > 0:
                vol_ratio = vols[-1] / prev5
        return ma20, ma60, ma120, ma60_last, vol_ratio
    except Exception:
        return 0.0, 0.0, 0.0, 0.0, 1.0


def screen_trend_king(top_n: int = TOP_N) -> dict:
    """
    初筛：涨幅 2%~5.5%、成交额≥1亿、振幅≤10%
    核验：现价>MA20>MA60>MA120、MA60向上、(MA20-MA60)/MA60>1%
    评分：量比40% + 涨幅20% + 趋势强度40%，取前 top_n
    """
    ip = pick_server(force=False)
    if not ip:
        return {
            "ok": False,
            "message": "未找到可用通达信服务器",
            "strategy_id": STRATEGY_ID,
            "strategy_name": STRATEGY_NAME,
            "results": [],
            "server": get_server_info(),
        }

    board = _get_all_mainboard()
    if not board:
        return {
            "ok": False,
            "message": "获取主板列表失败",
            "strategy_id": STRATEGY_ID,
            "strategy_name": STRATEGY_NAME,
            "results": [],
            "server": get_server_info(),
        }

    codes = list(board.keys())
    pairs = [(_market_of(c), c) for c in codes]
    snapshot: dict[str, dict] = {}

    chunks = [pairs[i : i + 400] for i in range(0, len(pairs), 400)]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(_batch_quotes, ck) for ck in chunks]
        for f in as_completed(futs):
            for q in f.result():
                code = str(q["code"]).zfill(6)
                snapshot[code] = q

    spot: list[dict] = []
    for code, q in snapshot.items():
        try:
            price = float(q["price"])
            last_close = float(q["last_close"])
            if price <= 0 or last_close <= 0:
                continue
            pct_chg = (price - last_close) / last_close * 100
            amount = float(q["amount"])
            high = float(q["high"])
            low = float(q["low"])
            amplitude = (high - low) / low * 100 if low > 0 else 0
            if 2 < pct_chg < 5.5 and amount >= 100_000_000 and amplitude <= 10:
                spot.append(
                    {
                        "code": code,
                        "name": board.get(code, code),
                        "price": price,
                        "pct_chg": pct_chg,
                        "amount": amount,
                        "amplitude": amplitude,
                    }
                )
        except Exception:
            continue

    if not spot:
        return {
            "ok": True,
            "strategy_id": STRATEGY_ID,
            "strategy_name": STRATEGY_NAME,
            "scanned": len(codes),
            "prefilter": 0,
            "count": 0,
            "message": "初筛无命中（非交易时段或条件过严）",
            "results": [],
            "server": get_server_info(),
        }

    spot_map = {s["code"]: s for s in spot}
    code_list = [s["code"] for s in spot]
    res_list: list[dict] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_get_ma_data, code): code for code in code_list}
        for future in as_completed(futures):
            code = futures[future]
            ma20, ma60, ma120, ma60_last, vol_ratio = future.result()
            if ma20 == 0:
                continue
            row = spot_map[code]
            price = row["price"]
            if (
                price > ma20 > ma60 > ma120
                and ma60 > ma60_last
                and (ma20 - ma60) / ma60 > 0.01
            ):
                vol_sc = min(vol_ratio, 5) / 5 * 40
                pct_sc = row["pct_chg"] / 5.5 * 20
                trend_sc = price / ma20 * 0.5 + ma20 / ma60 * 0.3 + ma60 / ma120 * 0.2
                trend_sc = min(trend_sc, 1.2) / 1.2 * 40
                total = round(vol_sc + pct_sc + trend_sc, 2)
                res_list.append(
                    {
                        "symbol": code,
                        "code": code,
                        "name": row["name"],
                        "price": round(price, 2),
                        "change_pct": round(row["pct_chg"], 2),
                        "vol_ratio": round(vol_ratio, 2),
                        "ma20": round(ma20, 2),
                        "score": total,
                        "reason": f"趋势王评分{total} 量比{vol_ratio:.2f} MA20={ma20:.2f}",
                        "strategy_id": STRATEGY_ID,
                        "strategy_name": STRATEGY_NAME,
                    }
                )

    res_list.sort(key=lambda x: x["score"], reverse=True)
    top = res_list[:top_n]

    return {
        "ok": True,
        "strategy_id": STRATEGY_ID,
        "strategy_name": STRATEGY_NAME,
        "scanned": len(codes),
        "prefilter": len(spot),
        "count": len(top),
        "results": top,
        "server": get_server_info(),
    }

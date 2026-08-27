"""纯规则：主板 / 非ST / 竞价涨停取反 / 量价过滤 / 量占自由流通前后排序。"""

from __future__ import annotations

from typing import Any, Iterable

# 大于 100 万股、小于 1000 万股
VOL_SHARES_MIN = 1_000_000
VOL_SHARES_MAX = 10_000_000
OPEN_PCT_MIN = 1.0
VOL_RATIO_MIN = 8.0
VOL_RATIO_MAX = 100.0
AMT_RATIO_MIN = 0.8
AMT_RATIO_MAX = 100.0
TURNOVER_MAX = 2.0
RANK_FIRST = 8
RANK_FINAL = 5


def is_st(name: str) -> bool:
    n = (name or "").upper().replace(" ", "")
    return "ST" in n or "退" in n


def is_main_board(code: str, name: str = "") -> bool:
    """沪深主板（含原中小板 002）。排除创业/科创/北交/B股。"""
    code = (code or "").split(".")[0]
    if is_st(name):
        return False
    if code.startswith(("300", "301", "688", "689", "8", "4", "200", "900")):
        return False
    return code.startswith(("60", "000", "001", "002", "003"))


def limit_pct(code: str, name: str) -> float:
    if is_st(name):
        return 5.0
    if code.startswith(("300", "301", "688", "689")):
        return 20.0
    if code.startswith(("8", "4")):
        return 30.0
    return 10.0


def limit_price(prev_close: float, code: str, name: str) -> float:
    if prev_close <= 0:
        return 0.0
    return round(prev_close * (1 + limit_pct(code, name) / 100.0) + 1e-8, 2)


def is_auction_limit_up(open_px: float, prev_close: float, code: str, name: str) -> bool:
    zt = limit_price(prev_close, code, name)
    if zt <= 0 or open_px <= 0:
        return False
    return open_px >= zt - 0.011


def vol_ratio(auction_lots: float, avg_daily_lots: float, minutes: float = 240.0) -> float:
    """竞价量比 ≈ 竞价量 / (日均量 / 240)。"""
    per_min = avg_daily_lots / minutes if avg_daily_lots > 0 else 0.0
    return auction_lots / per_min if per_min > 0 else 0.0


def turnover_pct(auction_shares: float, free_float_shares: float) -> float:
    if free_float_shares <= 0:
        return 0.0
    return auction_shares / free_float_shares * 100.0


def vol_over_free(auction_shares: float, free_float_shares: float) -> float:
    if free_float_shares <= 0:
        return 0.0
    return auction_shares / free_float_shares


def numeric_ok(row: dict[str, Any]) -> bool:
    vol = float(row.get("auction_shares") or 0)
    if not (VOL_SHARES_MIN < vol < VOL_SHARES_MAX):
        return False
    if float(row.get("open_pct") or 0) <= OPEN_PCT_MIN:
        return False
    ratio = float(row.get("vol_ratio") or 0)
    if not (VOL_RATIO_MIN < ratio < VOL_RATIO_MAX):
        return False
    amt_ratio = float(row.get("amt_ratio") or 0)
    if not (AMT_RATIO_MIN < amt_ratio < AMT_RATIO_MAX):
        return False
    if float(row.get("turnover") or 0) >= TURNOVER_MAX:
        return False
    return True


def _rank_key(row: dict[str, Any]) -> float:
    return float(row.get("vol_over_free") or 0)


def sequential_select(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """按用户条件顺序过滤。

    主板 → 非ST → 竞价涨停取反 → 昨日涨停（调用方已限定）
    → 竞价量/自由流通股 前8
    → 量/涨幅/量比/金额比/换手
    → 竞价量/自由流通股 前5
    """
    universe: list[dict[str, Any]] = []
    for row in rows:
        code = str(row.get("code") or "")
        name = str(row.get("name") or "")
        if not is_main_board(code, name):
            continue
        if is_st(name):
            continue
        if row.get("is_auction_zt"):
            continue
        universe.append(row)

    ranked = sorted(universe, key=_rank_key, reverse=True)
    top8 = ranked[:RANK_FIRST]
    filtered = [r for r in top8 if numeric_ok(r)]
    filtered_sorted = sorted(filtered, key=_rank_key, reverse=True)
    top5 = filtered_sorted[:RANK_FINAL]
    return {
        "universe": ranked,
        "top8": top8,
        "after_numeric": filtered_sorted,
        "top5": top5,
    }

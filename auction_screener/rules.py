"""纯规则：基准版 + 连板优化版过滤 / 评分 / 排序。"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

# ---------- 原版（基准）----------
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

# ---------- 优化 v2（连板）----------
OPT_VOL_MIN = 1_000_000
OPT_VOL_MAX = 8_000_000
OPT_OPEN_PCT_MIN = 1.5
OPT_OPEN_PCT_MAX = 7.0
OPT_VOL_RATIO_MIN = 8.0
OPT_VOL_RATIO_MAX = 35.0
OPT_AMT_RATIO_MIN = 0.9
OPT_AMT_RATIO_MAX = 6.0
OPT_TURNOVER_MIN = 0.2
OPT_TURNOVER_MAX = 1.5
OPT_LBC_MIN = 1
OPT_LBC_MAX = 4
OPT_ZBC_MAX = 1
OPT_MV_YI_MIN = 20.0
OPT_MV_YI_MAX = 150.0
OPT_TOP_N = 5
# 2026-09-04 复盘：金帝股份昨换手12.8%+二板偏高开 → 冲板回落；海量数据一进二低换手更健康
OPT_YEST_HS_MAX = 10.0
WR100_OPEN_LO = 3.0
WR100_OPEN_HI = 4.5
WR100_OPEN_HI_LBC2 = 3.7
WR100_YEST_HS_MAX = 10.0
WR100_LBC_MAX = 2
WR100_TOP_N = 3


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
    """原版硬过滤。"""
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


def optimized_numeric_ok(row: dict[str, Any]) -> bool:
    """连板优化硬过滤：收紧无效上限，补高度/炸板/市值/昨换手。"""
    vol = float(row.get("auction_shares") or 0)
    if not (OPT_VOL_MIN < vol < OPT_VOL_MAX):
        return False
    open_pct = float(row.get("open_pct") or 0)
    if not (OPT_OPEN_PCT_MIN < open_pct < OPT_OPEN_PCT_MAX):
        return False
    ratio = float(row.get("vol_ratio") or 0)
    if not (OPT_VOL_RATIO_MIN < ratio < OPT_VOL_RATIO_MAX):
        return False
    amt_ratio = float(row.get("amt_ratio") or 0)
    if not (OPT_AMT_RATIO_MIN < amt_ratio < OPT_AMT_RATIO_MAX):
        return False
    turnover = float(row.get("turnover") or 0)
    if not (OPT_TURNOVER_MIN < turnover < OPT_TURNOVER_MAX):
        return False
    lbc = int(row.get("lbc") or 1)
    if not (OPT_LBC_MIN <= lbc <= OPT_LBC_MAX):
        return False
    zbc = int(row.get("zbc") or 0)
    if zbc > OPT_ZBC_MAX:
        return False
    mv = float(row.get("mv_yi") or 0)
    if mv > 0 and not (OPT_MV_YI_MIN < mv < OPT_MV_YI_MAX):
        return False
    hs = float(row.get("hs") or 0)
    if hs > OPT_YEST_HS_MAX:
        return False
    # 二板及以上：避免偏高开诱多（金帝 2板+3.95% 冲板回落）
    if lbc >= 2 and open_pct >= 3.8:
        return False
    return True


def wr100_ok(row: dict[str, Any]) -> bool:
    """胜率方案 v2（2026-09-04 复盘后）。"""
    if row.get("is_auction_zt"):
        return False
    open_pct = float(row.get("open_pct") or 0)
    lbc = int(row.get("lbc") or 1)
    if not (1 <= lbc <= WR100_LBC_MAX):
        return False
    hi = WR100_OPEN_HI_LBC2 if lbc >= 2 else WR100_OPEN_HI
    if not (WR100_OPEN_LO < open_pct < hi):
        return False
    if int(row.get("zbc") or 0) > 1:
        return False
    mv = float(row.get("mv_yi") or 0)
    if mv > 0 and not (20 < mv < 150):
        return False
    if int(row.get("fbt") or 150000) > 100000:
        return False
    hs = float(row.get("hs") or 0)
    if hs > WR100_YEST_HS_MAX:
        return False
    return True


def _rank_key(row: dict[str, Any]) -> float:
    return float(row.get("vol_over_free") or 0)


def score_lianban(row: dict[str, Any], plate_counts: dict[str, int] | None = None) -> tuple[float, list[str]]:
    """连板综合分。越高越优先。"""
    score = 0.0
    reasons: list[str] = []
    open_pct = float(row.get("open_pct") or 0)
    amt_ratio = float(row.get("amt_ratio") or 0)
    vol_ratio_v = float(row.get("vol_ratio") or 0)
    turnover = float(row.get("turnover") or 0)
    lbc = int(row.get("lbc") or 1)
    zbc = int(row.get("zbc") or 0)
    fbt = int(row.get("fbt") or 150000)
    hy = str(row.get("hy") or "")
    traj = float(row.get("traj_score") or 0)
    traj_label = str(row.get("traj_label") or "")

    if 2.5 <= open_pct <= 5.5:
        score += 28
        reasons.append(f"涨幅甜蜜区{open_pct:.2f}%")
    elif 1.5 < open_pct < 2.5:
        score += 16
        reasons.append(f"小高开{open_pct:.2f}%")
    elif 5.5 < open_pct < 7.0:
        score += 14
        reasons.append(f"偏高开{open_pct:.2f}%")
    else:
        score += 4
        reasons.append(f"涨幅边缘{open_pct:.2f}%")

    if 1.0 <= amt_ratio <= 3.0:
        score += 16
        reasons.append(f"金额比健康{amt_ratio:.2f}")
    elif 0.9 < amt_ratio < 1.0:
        score += 8
        reasons.append(f"金额比略缩{amt_ratio:.2f}")
    elif 3.0 < amt_ratio <= 6.0:
        score += 6
        reasons.append(f"金额比偏大{amt_ratio:.2f}")
    else:
        score -= 4
        reasons.append(f"金额比异常{amt_ratio:.2f}")

    if 10 <= vol_ratio_v <= 25:
        score += 12
        reasons.append(f"量比适中{vol_ratio_v:.1f}")
    elif 8 < vol_ratio_v < 10:
        score += 7
        reasons.append(f"量比刚过线{vol_ratio_v:.1f}")
    elif 25 < vol_ratio_v < 35:
        score += 4
        reasons.append(f"量比偏高{vol_ratio_v:.1f}")

    if 0.4 <= turnover <= 1.0:
        score += 10
        reasons.append(f"换手适中{turnover:.3f}%")
    elif 0.2 < turnover < 0.4:
        score += 5
        reasons.append(f"换手偏低{turnover:.3f}%")
    elif 1.0 < turnover < 1.5:
        score += 4
        reasons.append(f"换手偏高{turnover:.3f}%")

    if lbc == 1:
        score += 14
        reasons.append("一进二优先")
    elif lbc == 2:
        score += 4
        reasons.append("二进三谨慎")
        if open_pct >= 3.8:
            score -= 16
            reasons.append("二板偏高开易冲回落")
    elif lbc == 3:
        score += 1
        reasons.append("三进四高风险")
    elif lbc == 4:
        score -= 4
        reasons.append("四进五降权")

    hs = float(row.get("hs") or 0)
    if 2.5 <= hs <= 8:
        score += 10
        reasons.append(f"昨换手健康{hs:.1f}%")
    elif 8 < hs <= 10:
        score += 2
        reasons.append(f"昨换手偏高{hs:.1f}%")
    elif hs > 10:
        score -= 14
        reasons.append(f"昨换手过大{hs:.1f}%")
    elif 0 < hs < 2.5:
        score += 3
        reasons.append(f"昨换手偏低{hs:.1f}%")

    # 断板再连：近N日涨停次数 < 天数（如 4日3板）
    zt_days = int(row.get("zt_days") or 0)
    zt_ct = int(row.get("zt_ct") or 0)
    if zt_days >= 3 and zt_ct > 0 and zt_ct < zt_days:
        score -= 8
        reasons.append(f"断板再连{zt_days}日{zt_ct}板")

    if zbc == 0:
        score += 10
        reasons.append("昨未开板")
    elif zbc == 1:
        score += 2
        reasons.append("昨开板1次")
    else:
        score -= 8
        reasons.append(f"昨开板{zbc}次")

    if fbt <= 93030:
        score += 12
        reasons.append("昨秒板")
    elif fbt <= 100000:
        score += 9
        reasons.append("昨早盘封")
    elif fbt <= 103000:
        score += 5
        reasons.append("昨午前封")
    elif fbt <= 130000:
        score += 1
        reasons.append("昨午盘封")
    else:
        score -= 4
        reasons.append("昨尾盘偷袭")

    plate_n = (plate_counts or {}).get(hy, 0) if hy else 0
    if plate_n >= 5:
        score += 10
        reasons.append(f"板块强共振{hy}×{plate_n}")
    elif plate_n >= 3:
        score += 6
        reasons.append(f"板块共振{hy}×{plate_n}")
    elif plate_n == 1:
        score -= 2
        reasons.append("题材偏孤岛")

    # 量占自由：相对加分，但巨量金额比时降权
    vof = float(row.get("vol_over_free") or 0)
    if vof > 0:
        score += min(vof * 800, 12)
        if amt_ratio > 4 and vof > 0.01:
            score -= 6
            reasons.append("量占自由高但金额比过大")

    if traj_label:
        score += traj
        reasons.append(f"走势:{traj_label}({traj:+.0f})")
    elif traj:
        score += traj

    return score, reasons


def sequential_select(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """原版顺序：主板→非ST→竞价涨停取反→量占自由前8→硬过滤→前5。"""
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


def optimized_select(
    rows: Iterable[dict[str, Any]],
    *,
    top_n: int = OPT_TOP_N,
) -> dict[str, list[dict[str, Any]]]:
    """优化版：硬过滤后按连板综合分排序取 TopN。"""
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

    plate_counts = Counter(str(r.get("hy") or "") for r in universe if r.get("hy"))
    passed: list[dict[str, Any]] = []
    for row in universe:
        if not optimized_numeric_ok(row):
            continue
        sc, reasons = score_lianban(row, plate_counts)
        item = dict(row)
        item["score"] = round(sc, 2)
        item["reasons"] = reasons
        passed.append(item)

    ranked = sorted(
        passed,
        key=lambda r: (float(r.get("score") or 0), float(r.get("vol_over_free") or 0)),
        reverse=True,
    )
    return {
        "universe": sorted(universe, key=_rank_key, reverse=True),
        "after_numeric": ranked,
        "top5": ranked[:top_n],
        "top8": ranked[: max(8, top_n)],
    }

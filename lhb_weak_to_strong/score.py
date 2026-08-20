"""弱转强评分规则 — 锚定 2026-08-03 案例族。

形态定义（弱转强 · 龙虎榜版）
----------------------------
当日因大跌上榜（跌幅偏离等），但龙虎榜净买入为正，显示有资金在恐慌盘中承接。
次日常见修复/主升启动；若同日多只共振，胜率显著抬升。

硬门槛
------
1. 非 ST / 退市整理 / 可转债 / B 股
2. 当日涨跌幅 ≤ -7%
3. 龙虎榜净买额 > 0

加分维度（满分约 100）
----------------------
- 净买绝对额
- 净买额 / 当日成交额
- 买入席位质量（机构 / 北向）
- 跌幅甜区 [-11%, -7%]
- 同日弱转强候选数量（板块/情绪共振）
"""

from __future__ import annotations

import math
import re
from typing import Any

SCORE_VERSION = "wts-lhb-v1"

# Anchored case study — 2026-08-03
ANCHOR_CASES = [
    {
        "code": "002409",
        "name": "雅克科技",
        "note": "机构四席+深股通净买，净买占比10.3%，次日+7.1%、五日+28.4%",
    },
    {
        "code": "002156",
        "name": "通富微电",
        "note": "机构+深股通承接，净买2.23亿，次日+8.3%、五日+23.1%",
    },
    {
        "code": "301520",
        "name": "万邦医药",
        "note": "高换手弱转强（游资主导），净买比6.1%，次日+9.8%、五日+40.2%",
    },
    {
        "code": "603118",
        "name": "共进股份",
        "note": "连续下跌偏离上榜+沪股通，次日仅微涨+3.4%，属于弱转强偏弱档",
    },
]


def is_excluded(code: str, name: str) -> bool:
    code = str(code)
    name = str(name)
    if re.search(r"ST|退", name):
        return True
    if "转债" in name or "债" in name:
        return True
    if code.startswith(("11", "12")):  # convertibles
        return True
    if code.startswith("2"):  # B shares
        return True
    return False


def passes_hard_filters(row: dict[str, Any]) -> tuple[bool, str]:
    code = str(row.get("代码") or row.get("code") or "")
    name = str(row.get("名称") or row.get("name") or "")
    if is_excluded(code, name):
        return False, "排除ST/退市/债/B股"
    chg = float(row.get("涨跌幅") or row.get("chg") or 0)
    net = float(row.get("龙虎榜净买额") or row.get("net") or 0)
    if chg > -7:
        return False, "跌幅未达弱转强门槛(需≤-7%)"
    if net <= 0:
        return False, "龙虎榜净买额≤0（弱势出货）"
    return True, "ok"


def _tier(score: float) -> str:
    if score >= 75:
        return "S"
    if score >= 60:
        return "A"
    if score >= 45:
        return "B"
    return "C"


def score_candidate(
    row: dict[str, Any],
    seat: dict[str, Any] | None = None,
    cluster_count: int = 1,
) -> dict[str, Any]:
    """Score one LHB row. Returns score breakdown + actionable tag."""
    ok, reason = passes_hard_filters(row)
    code = str(row.get("代码") or row.get("code") or "")
    name = str(row.get("名称") or row.get("name") or "")
    chg = float(row.get("涨跌幅") or row.get("chg") or 0)
    net = float(row.get("龙虎榜净买额") or row.get("net") or 0)
    ratio = float(row.get("净买额占总成交比") or row.get("ratio") or 0)
    turnover = float(row.get("换手率") or row.get("turnover") or 0)
    list_reason = str(row.get("上榜原因") or row.get("reason") or "")
    close = float(row.get("收盘价") or row.get("close") or 0)
    mcap = float(row.get("流通市值") or row.get("mcap") or 0)

    seat = seat or {}
    n_inst = int(seat.get("n_inst") or 0)
    n_north = int(seat.get("n_north") or 0)
    inst_net = float(seat.get("inst_net") or 0)
    north_net = float(seat.get("north_net") or 0)
    hot_net = float(seat.get("hot_net") or 0)

    breakdown: dict[str, float] = {}
    notes: list[str] = []

    if not ok:
        return {
            "eligible": False,
            "filter_reason": reason,
            "code": code,
            "name": name,
            "score": 0.0,
            "tier": "F",
            "breakdown": {},
            "notes": [reason],
            "action": "忽略",
        }

    # --- 净买绝对额 (0~45) ---
    # 3e7→~22, 1e8→~32, 5e8→~42
    if net > 0:
        net_score = min(45.0, 8.0 * math.log10(net) - 36.0)
        net_score = max(0.0, net_score)
    else:
        net_score = 0.0
    breakdown["net_amount"] = round(net_score, 2)

    # --- 净买占比 (0~25) ---
    if ratio >= 10:
        ratio_score = 25.0
    elif ratio >= 5:
        ratio_score = 20.0
    elif ratio >= 2.5:
        ratio_score = 15.0
    elif ratio >= 1.5:
        ratio_score = 10.0
    elif ratio >= 0.8:
        ratio_score = 5.0
    else:
        ratio_score = 2.0
    breakdown["net_ratio"] = ratio_score

    # --- 席位质量 (0~35) ---
    seat_score = 0.0
    seat_score += min(20.0, n_inst * 5.0)
    if n_north >= 1:
        seat_score += 12.0
    if n_inst >= 2 and n_north >= 1:
        seat_score += 8.0
        notes.append("机构+北向双料买入")
    elif n_inst >= 2:
        notes.append("多机构席位承接")
    elif n_north >= 1:
        notes.append("北向席位现身买入")
    elif hot_net > 0 and n_inst == 0 and n_north == 0:
        seat_score += 6.0  # pure hot-money weak-to-strong still valid (301520)
        notes.append("游资主导弱转强（需更高换手/净买比验证）")
    breakdown["seat_quality"] = round(min(35.0, seat_score), 2)

    # --- 跌幅甜区 (可正可负) ---
    if -11 <= chg <= -7:
        chg_score = 10.0
        notes.append("跌幅甜区[-11,-7]")
    elif -15 <= chg < -11:
        chg_score = 4.0
        notes.append("深跌但未失控")
    elif chg < -15:
        chg_score = -6.0
        notes.append("超跌风险偏高（连续杀跌/20cm深砸）")
    else:
        chg_score = 0.0
    breakdown["chg_zone"] = chg_score

    # --- 上榜原因 ---
    reason_score = 0.0
    if "跌幅偏离值达到7%" in list_reason or "日跌幅偏离" in list_reason:
        reason_score = 6.0
        notes.append("单日跌幅偏离上榜")
    elif "连续三个交易日内" in list_reason and "跌幅" in list_reason:
        reason_score = 2.0
        notes.append("连续下跌偏离上榜（修复弹性弱于单日恐慌）")
    elif "换手率" in list_reason:
        reason_score = 4.0
        notes.append("高换手换筹上榜")
    breakdown["list_reason"] = reason_score

    # --- 换手辅助（高换手弱转强加分，过低减分）---
    turn_score = 0.0
    if turnover >= 25:
        turn_score = 5.0
    elif turnover >= 10:
        turn_score = 3.0
    elif 0 < turnover < 3:
        turn_score = -3.0
        notes.append("换手偏低，承接真实性存疑")
    breakdown["turnover"] = turn_score

    # --- 同日共振 ---
    cluster_score = 0.0
    if cluster_count >= 5:
        cluster_score = 12.0
        notes.append(f"强共振：同日{cluster_count}只弱转强候选")
    elif cluster_count >= 3:
        cluster_score = 8.0
        notes.append(f"板块/情绪共振：同日{cluster_count}只候选")
    elif cluster_count == 2:
        cluster_score = 3.0
    breakdown["cluster"] = cluster_score

    total = sum(breakdown.values())
    total = max(0.0, min(100.0, total))
    tier = _tier(total)

    if tier == "S":
        action = "优先：次日竞价/开盘回踩低吸，设好止损"
    elif tier == "A":
        action = "可跟踪：看竞价强度与板块回流，半仓试错"
    elif tier == "B":
        action = "观察：需额外验证（板块、分时、大盘），不急着上车"
    else:
        action = "过滤：仅作样本，不作为买入信号"

    # Pattern tag
    if n_inst >= 2 and n_north >= 1:
        pattern = "机构北向双杀接"
    elif n_inst >= 2:
        pattern = "机构承接"
    elif n_north >= 1:
        pattern = "北向承接"
    elif turnover >= 25:
        pattern = "高换手游资弱转强"
    else:
        pattern = "普通净买弱转强"

    return {
        "eligible": True,
        "filter_reason": "ok",
        "code": code,
        "name": name,
        "close": close,
        "chg": chg,
        "net": net,
        "ratio": ratio,
        "turnover": turnover,
        "mcap": mcap,
        "list_reason": list_reason,
        "n_inst": n_inst,
        "n_north": n_north,
        "inst_net": inst_net,
        "north_net": north_net,
        "hot_net": hot_net,
        "buy_seats": seat.get("buy_seats") or [],
        "cluster_count": cluster_count,
        "score": round(total, 1),
        "tier": tier,
        "pattern": pattern,
        "breakdown": breakdown,
        "notes": notes,
        "action": action,
        "t1": row.get("上榜后1日") if row.get("上榜后1日") is not None else row.get("t1"),
        "t2": row.get("上榜后2日") if row.get("上榜后2日") is not None else row.get("t2"),
        "t5": row.get("上榜后5日") if row.get("上榜后5日") is not None else row.get("t5"),
        "score_version": SCORE_VERSION,
    }

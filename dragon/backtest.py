"""近3个月回测：只用当日涨停池能看到的字段，次日收益来自选股宝昨日涨停表现。"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from dragon.engine import analyze
from dragon.score import is_yizi
from dragon.timeutil import CN
from dragon.xuangubao import fetch_pool, next_day_map, normalize_xgb

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "data" / "backtest_3m.json"


def trading_dates(start: str, end: str) -> list[str]:
    cur = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=CN)
    last = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=CN)
    out: list[str] = []
    while cur <= last:
        if cur.weekday() < 5:
            out.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return out


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(trust_env=False, follow_redirects=True, timeout=20.0)


def _tag_mainline_membership(rows: list[dict]) -> list[dict]:
    """按选股宝相关板块归并主线，一只票只进一个最强主题。「其他」不能当主线。"""
    counts: dict[str, set[str]] = defaultdict(set)
    amounts: dict[str, float] = defaultdict(float)
    for r in rows:
        for th in r.get("themes") or [r["theme"]]:
            if th in {"其他", "ST股", "未知"}:
                continue
            counts[th].add(r["code"])
            amounts[th] += float(r.get("amount") or 0)
    if not counts:
        return rows
    main = sorted(counts.items(), key=lambda kv: (-len(kv[1]), -amounts[kv[0]]))[0][0]
    out = []
    for r in rows:
        copy = dict(r)
        if main in (r.get("themes") or []):
            copy["theme"] = main
            copy["industry"] = main
        out.append(copy)
    return out


def pick_controls(zt_rows: list[dict]) -> dict[str, dict | None]:
    sealed = [r for r in zt_rows if r.get("sealed")]
    if not sealed:
        return {}
    first = sorted(sealed, key=lambda r: int(r.get("first_seal") or 999999))[0]
    high = sorted(sealed, key=lambda r: (-int(r.get("boards") or 0), int(r.get("first_seal") or 999999)))[0]
    bulky = sorted(sealed, key=lambda r: -float(r.get("amount") or 0))[0]
    tradable = [
        r
        for r in sealed
        if not is_yizi(int(r.get("first_seal") or 0), int(r.get("open_count") or 0), float(r.get("turnover") or 0))
    ]
    first_t = sorted(tradable, key=lambda r: int(r.get("first_seal") or 999999))[0] if tradable else None
    high_t = (
        sorted(tradable, key=lambda r: (-int(r.get("boards") or 0), int(r.get("first_seal") or 999999)))[0]
        if tradable
        else None
    )
    return {
        "first_market": first,
        "height_market": high,
        "amount_market": bulky,
        "first_tradable": first_t,
        "height_tradable": high_t,
    }


def summarize(samples: list[dict], label: str) -> dict[str, Any]:
    xs = [s for s in samples if s.get("next_pct") is not None]
    if not xs:
        return {"label": label, "n": 0}
    rets = [float(s["next_pct"]) for s in xs]
    wins = sum(1 for r in rets if r > 0)
    flats = sum(1 for r in rets if r == 0)
    zt = sum(1 for s in xs if s.get("next_zt"))
    lose = sum(1 for r in rets if r <= -5)
    rets_sorted = sorted(rets)
    mid = rets_sorted[len(rets_sorted) // 2]
    return {
        "label": label,
        "n": len(xs),
        "avg": round(sum(rets) / len(rets), 3),
        "median": round(mid, 3),
        "win_rate": round(wins / len(xs) * 100.0, 1),
        "zt_rate": round(zt / len(xs) * 100.0, 1),
        "big_loss_rate": round(lose / len(xs) * 100.0, 1),
        "best": round(max(rets), 2),
        "worst": round(min(rets), 2),
        "sum": round(sum(rets), 2),
    }


async def run_backtest(start: str = "2026-06-05", end: str = "2026-09-04") -> dict[str, Any]:
    dates = trading_dates(start, end)
    days: list[dict[str, Any]] = []
    buckets: dict[str, list[dict]] = defaultdict(list)

    async with _client() as client:
        pools: dict[str, list] = {}
        ypools: dict[str, list] = {}
        for i, date in enumerate(dates):
            try:
                pools[date] = await fetch_pool(client, "limit_up", date)
            except Exception:
                pools[date] = []
            try:
                ypools[date] = await fetch_pool(client, "yesterday_limit_up", date)
            except Exception:
                ypools[date] = []
            await asyncio.sleep(0.05)

    valid = [d for d in dates if pools.get(d)]
    for i, date in enumerate(valid):
        nxt = valid[i + 1] if i + 1 < len(valid) else None
        if not nxt:
            continue
        rows = [r for r in (normalize_xgb(x) for x in pools[date]) if r]
        if len(rows) < 8:
            continue
        rows_used = _tag_mainline_membership(rows)
        result = analyze(rows_used, popularity={}, concepts=[], broken=[], indexes=[], mode="盘后")

        watch = result.get("watch")
        controls = pick_controls(rows)
        nxt_map = next_day_map(ypools.get(nxt) or [])
        baseline = [nxt_map[r["code"]]["next_pct"] for r in rows if r["code"] in nxt_map]
        day = {
            "date": date,
            "next": nxt,
            "zt": len(rows),
            "mainline": (result.get("mainline") or {}).get("theme"),
            "mainline_count": (result.get("mainline") or {}).get("count"),
            "watch": None,
            "controls": {},
            "baseline_avg": round(sum(baseline) / len(baseline), 3) if baseline else None,
        }

        def pack(row: dict | None, scored=None) -> dict | None:
            src = scored
            code = src.code if src is not None else (row or {}).get("code")
            if not code:
                return None
            nd = nxt_map.get(code)
            return {
                "code": code,
                "name": src.name if src is not None else row.get("name"),
                "theme": src.theme if src is not None else row.get("theme"),
                "boards": src.boards if src is not None else row.get("boards"),
                "first_seal": src.first_seal if src is not None else None,
                "turnover": src.turnover if src is not None else row.get("turnover"),
                "open_count": src.open_count if src is not None else row.get("open_count"),
                "next_pct": nd["next_pct"] if nd else None,
                "next_zt": nd["next_zt"] if nd else None,
            }

        if watch:
            day["watch"] = pack(None, watch)
            if day["watch"]["next_pct"] is not None:
                buckets["method"].append(day["watch"])
        for key, row in controls.items():
            day["controls"][key] = pack(row)
            if day["controls"][key] and day["controls"][key]["next_pct"] is not None:
                buckets[key].append(day["controls"][key])
        if day["baseline_avg"] is not None:
            buckets["all_zt"].append({"next_pct": day["baseline_avg"], "next_zt": False})

        # 支线最高板：检验「支线再猛也不进池」
        main = day["mainline"]
        side = [r for r in rows_used if main and r.get("theme") != main]
        if side:
            side_high = sorted(side, key=lambda r: (-int(r.get("boards") or 0), -float(r.get("amount") or 0)))[0]
            day["controls"]["side_height"] = pack(side_high)
            if day["controls"]["side_height"]["next_pct"] is not None:
                buckets["side_height"].append(day["controls"]["side_height"])
        days.append(day)

    monthly: dict[str, list] = defaultdict(list)
    for s, day in zip(buckets["method"], [d for d in days if d.get("watch") and d["watch"].get("next_pct") is not None]):
        monthly[day["date"][:7]].append(s)
    # zip may misalign if some days have no next_pct on watch; build from days instead
    monthly = defaultdict(list)
    for day in days:
        w = day.get("watch") or {}
        if w.get("next_pct") is not None:
            monthly[day["date"][:7]].append(w)

    summary = {
        "method": summarize(buckets["method"], "主线火车头（他说的方法）"),
        "first_market": summarize(buckets["first_market"], "全市场最先封（含一字）"),
        "first_tradable": summarize(buckets["first_tradable"], "全市场最先封（非一字）"),
        "height_market": summarize(buckets["height_market"], "全市场最高板（含一字）"),
        "height_tradable": summarize(buckets["height_tradable"], "全市场最高板（非一字）"),
        "amount_market": summarize(buckets["amount_market"], "全市场成交额最大"),
        "side_height": summarize(buckets["side_height"], "支线最高板"),
        "all_zt": summarize(buckets["all_zt"], "当天全部涨停等权（基准）"),
    }
    report = {
        "ok": True,
        "start": start,
        "end": end,
        "days": len(days),
        "source": "选股宝涨停池 + 次日昨日涨停表现",
        "note": [
            "只用当日涨停池字段（首封、炸板、换手、板块），不用后人气榜。",
            "收益是次日收盘相对当日收盘。涨停封死当天买不到，这是「盘后盯、次日表现」不是可成交收益。",
            "创业板/科创板按是否再次封板统计晋级，涨跌幅仍用真实幅度。",
        ],
        "summary": summary,
        "monthly": {k: summarize(v, k) for k, v in monthly.items()},
        "verdict": _verdict(summary),
        "samples": days,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    return report


def _verdict(summary: dict[str, dict]) -> dict[str, Any]:
    m = summary.get("method") or {}
    base = summary.get("all_zt") or {}
    height = summary.get("height_tradable") or summary.get("height_market") or {}
    side = summary.get("side_height") or {}
    first = summary.get("first_tradable") or summary.get("first_market") or {}
    lines = []
    if not m.get("n"):
        return {"ok": False, "lines": ["回测没有有效样本。"]}
    beat_base = m.get("avg", -99) > base.get("avg", -99)
    beat_height = m.get("avg", -99) > height.get("avg", -99)
    beat_side = m.get("avg", -99) > side.get("avg", -99)
    beat_first = m.get("avg", -99) > first.get("avg", -99)
    lines.append(
        f"主线火车头次日均涨 {m.get('avg')}%，胜率 {m.get('win_rate')}%，"
        f"再封 {m.get('zt_rate')}%，样本 {m.get('n')} 天。"
    )
    lines.append(
        f"对照：全部涨停等权 {base.get('avg')}%，全市场最高板 {height.get('avg')}%，"
        f"全市场最先封 {first.get('avg')}%，支线最高板 {side.get('avg')}%。"
    )
    if beat_base and beat_side:
        lines.append("「先定板块、支线不进池」在这3个月里，比乱打涨停和追支线高标更强。")
    elif beat_base and not beat_side:
        lines.append("比全部涨停强，但支线高标次日均涨并不差，支线一律不看这句话过猛。")
    else:
        lines.append("这3个月主线火车头没有稳定打赢「随便打一只涨停」的基准，口诀不能当真理。")
    if not beat_height:
        lines.append("最高板的次日均涨不低于火车头，高度龙仍有独立价值，不能只看先封。")
    if not beat_first:
        lines.append("全市场最先封并不更差，说明「一定要先定板块」不是每天都成立。")
    if m.get("big_loss_rate", 0) >= 15:
        lines.append(f"大亏天（次日≤-5%）占 {m.get('big_loss_rate')}%，盯1只也会遇到核按钮。")
    return {
        "ok": True,
        "beat_baseline": beat_base,
        "beat_side": beat_side,
        "beat_height": beat_height,
        "beat_first_market": beat_first,
        "lines": lines,
    }


def print_report(report: dict) -> None:
    print(f"回测 {report['start']} → {report['end']}  有效日 {report['days']}")
    print("策略".ljust(22), "天数", "均涨%", "中位%", "胜率%", "再封%", "大亏%", "最好", "最差")
    for key in (
        "method",
        "first_tradable",
        "height_tradable",
        "first_market",
        "height_market",
        "amount_market",
        "side_height",
        "all_zt",
    ):
        s = report["summary"][key]
        if not s.get("n"):
            continue
        print(
            f"{s['label']:<22} {s['n']:>3} {s['avg']:>7} {s['median']:>7} "
            f"{s['win_rate']:>6} {s['zt_rate']:>6} {s['big_loss_rate']:>6} {s['best']:>6} {s['worst']:>6}"
        )
    print()
    for line in report["verdict"]["lines"]:
        print("-", line)
    print("\n最近10个交易日：")
    for d in report["samples"][-10:]:
        w = d.get("watch") or {}
        print(
            f"  {d['date']} 主线={d.get('mainline')} 盯={w.get('name')} "
            f"次日={w.get('next_pct')} 再封={w.get('next_zt')}"
        )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2026-06-05")
    parser.add_argument("--end", default="2026-09-04")
    args = parser.parse_args()
    report = await run_backtest(args.start, args.end)
    print_report(report)
    print(f"\n报告已写 {REPORT}")


if __name__ == "__main__":
    asyncio.run(main())

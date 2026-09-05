from __future__ import annotations

import asyncio
import json
import sys

from dragon.engine import build_snapshot
from dragon.shot import save_png


def _line(stock: dict | None, title: str) -> str:
    if not stock:
        return f"{title}：无"
    pop = stock.get("pop_rank")
    return (
        f"{title}：{stock['name']} {stock['code']} {stock['boards']}板 "
        f"{stock['theme']} 换手{stock['turnover']}% 人气{pop if pop else '-'}"
    )


async def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = set(sys.argv[1:])
    date = args[0] if args else None
    mode = "盘中" if "--intraday" in flags else ("盘后" if "--review" in flags else None)
    snap = await build_snapshot(date, mode)
    watch = snap.get("watch")
    picks = snap.get("picks") or {}
    print(f"交易日 {snap['date']}  {snap['session']['phase']}  模式={snap['mode']}  涨停{snap['stats']['zt']}只")
    ml = snap.get("mainline")
    sec = snap.get("secondary")
    if ml:
        print(f"主线 {ml['theme']}  涨停{ml['count']}只  成交{ml['amount_yi']}亿")
    else:
        print("主线：无")
    if sec:
        print(f"次主线 {sec['theme']}  涨停{sec['count']}只  最高{sec['max_boards']}板")
    print()
    print(_line(picks.get("locomotive"), "火车头"))
    print(_line(picks.get("sentiment"), "情绪龙头"))
    print(_line(picks.get("height"), "空间高标"))
    print()
    for step in snap.get("steps") or []:
        mark = "过" if step["pass"] else "否"
        print(f"{step['step']}. [{mark}] {step['title']}")
        print(f"   {step['detail']}")
    print()
    if watch:
        print(f"盯1只：{watch['name']} {watch['code']} {watch['boards']}板  {snap.get('watch_hat') or ''}")
        print(f"理由：{snap.get('reason')}")
        print(f"动作：{snap.get('action')}")
        for n in snap.get("notes") or []:
            print(f"  · {n}")
    else:
        print("盯1只：无")
        print(f"理由：{snap.get('reason')}")
    if "--shot" in flags:
        path = save_png(snap)
        print(f"截屏：{path}")
    if "--json" in flags:
        print(json.dumps({
            "watch": snap.get("watch"),
            "picks": {k: picks.get(k) for k in ("locomotive", "sentiment", "height")},
            "reason": snap.get("reason"),
            "steps": snap.get("steps"),
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

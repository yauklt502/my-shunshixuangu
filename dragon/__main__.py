from __future__ import annotations

import asyncio
import json
import sys

from dragon.engine import build_snapshot


async def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = set(sys.argv[1:])
    date = args[0] if args else None
    mode = "盘中" if "--intraday" in flags else ("盘后" if "--review" in flags else None)
    snap = await build_snapshot(date, mode)
    watch = snap.get("watch")
    print(f"交易日 {snap['date']}  {snap['session']['phase']}  模式={snap['mode']}  涨停{snap['stats']['zt']}只")
    ml = snap.get("mainline")
    if ml:
        print(f"主线 {ml['theme']}  涨停{ml['count']}只  成交{ml['amount_yi']}亿")
    else:
        print("主线：无")
    print()
    for step in snap.get("steps") or []:
        mark = "过" if step["pass"] else "否"
        print(f"{step['step']}. [{mark}] {step['title']}")
        print(f"   {step['detail']}")
    print()
    if watch:
        print(f"盯1只：{watch['name']} {watch['code']} {watch['boards']}板 换手{watch['turnover']}% 成交{watch['amount_yi']}亿")
        print(f"动作：{snap.get('action')}")
    else:
        print("盯1只：无")
    print("\n主线定龙池:")
    for s in snap["leaders"][:8]:
        print(f"  {s['first_seal']} 炸{s['open_count']} {s['name']} {s['boards']}板 换手{s['turnover']}% {s['status']}")
    if "--json" in flags:
        print(json.dumps({"watch": snap.get("watch"), "steps": snap.get("steps")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

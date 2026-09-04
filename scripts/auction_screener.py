#!/usr/bin/env python3
"""主板 · 非ST · 昨日涨停 · 竞价涨停取反。

默认跑优化版（连板综合分）；--mode baseline 还原原公式。
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from auction_screener.fetch import (  # noqa: E402
    CST,
    auction_from_trends,
    fetch_trends,
    latest_zt_date,
)
from auction_screener.rules import (  # noqa: E402
    is_auction_limit_up,
    is_main_board,
    optimized_select,
    sequential_select,
    turnover_pct,
    vol_over_free,
    vol_ratio,
)


def zt_prev_close(zt: dict[str, Any]) -> float:
    p = float(zt.get("p") or 0)
    if p > 1000:
        return p / 1000.0
    return p


def enrich(zt: dict[str, Any]) -> dict[str, Any] | None:
    code, name = zt["c"], zt["n"]
    payload = fetch_trends(code, ndays=5)
    auction = auction_from_trends(payload)
    if not auction:
        return None
    prev = auction["prev_close"] or zt_prev_close(zt)
    ltsz = float(zt.get("ltsz") or 0)
    free = (ltsz / prev) if prev else 0.0
    today = auction["today_auction"]
    yest = auction["yest_auction"]
    open_px = today["px"]
    shares = today["vol_lots"] * 100.0
    open_pct = (open_px / prev - 1) * 100 if prev else 0.0
    amt_ratio = (today["amt"] / yest["amt"]) if yest["amt"] else 0.0
    mv_yi = ltsz / 1e8 if ltsz else 0.0
    return {
        "code": code,
        "name": name,
        "hy": zt.get("hybk") or "",
        "lbc": int(zt.get("lbc") or 0) or 1,
        "zbc": int(zt.get("zbc") or 0),
        "fbt": int(zt.get("fbt") or 150000),
        "hs": float(zt.get("hs") or 0),
        "mv_yi": round(mv_yi, 2),
        "prev": round(prev, 3),
        "open": round(open_px, 3),
        "open_pct": round(open_pct, 2),
        "is_auction_zt": is_auction_limit_up(open_px, prev, code, name),
        "auction_shares": shares,
        "auction_lots": today["vol_lots"],
        "auction_amt": today["amt"],
        "yest_auction_amt": yest["amt"],
        "amt_ratio": round(amt_ratio, 3),
        "vol_ratio": round(vol_ratio(today["vol_lots"], auction["avg5_lots"]), 2),
        "turnover": round(turnover_pct(shares, free), 4),
        "vol_over_free": vol_over_free(shares, free),
        "free_float": free,
        "trade_date": auction["today"],
        "zt_date": auction["yesterday"],
    }


def render_text(picked: dict[str, list[dict[str, Any]]], meta: dict[str, Any], mode: str) -> str:
    title = "连板优化 v2" if mode == "optimized" else "竞价涨停取反·原版"
    lines = [
        f"{title}  {meta['generated_at']}",
        f"昨涨停 {meta['zt_date']}  {meta['zt_total']}只  主板非ST {meta['main_n']}只  有竞价数据 {meta['fetched']}",
        "",
        "最终标的：",
    ]
    top5 = picked["top5"]
    if not top5:
        lines.append("  （无）过滤后为空")
    for i, r in enumerate(top5, 1):
        score = r.get("score")
        score_s = f"  分{score:.1f}" if score is not None else ""
        lines.append(
            f"  {i}. {r['name']} {r['code']}  高开{r['open_pct']:.2f}%  "
            f"竞价{r['auction_shares']/1e4:.0f}万股  量比{r['vol_ratio']:.1f}  "
            f"换手{r['turnover']:.3f}%  金额比{r['amt_ratio']:.2f}  "
            f"高{r.get('lbc', '?')}{score_s}"
        )
        if r.get("reasons"):
            lines.append("     " + "；".join(r["reasons"][:6]))
    if picked.get("top8") and mode == "baseline":
        lines += ["", "前8（量占自由，未做量价硬过滤）："]
        for i, r in enumerate(picked["top8"], 1):
            flag = "涨停" if r["is_auction_zt"] else ""
            lines.append(
                f"{i:2d} {r['code']} {r['name']:8s} {r['open_pct']:+6.2f}%{flag}  "
                f"量{r['auction_shares']/1e4:7.1f}万  量比{r['vol_ratio']:6.1f}  "
                f"换手{r['turnover']:6.3f}%  额比{r['amt_ratio']:6.2f}"
            )
    return "\n".join(lines) + "\n"


def render_html(picked: dict[str, list[dict[str, Any]]], meta: dict[str, Any], mode: str) -> str:
    def rows_html(items: list[dict[str, Any]]) -> str:
        out = []
        for i, r in enumerate(items, 1):
            cls = "top" if i <= 5 and items is picked["top5"] else ""
            score = r.get("score")
            score_s = f"{score:.1f}" if score is not None else "-"
            out.append(
                "<tr class='{cls}'><td>{i}</td><td>{code}</td><td>{name}</td>"
                "<td>{pct:+.2f}%</td><td>{vol:.0f}</td><td>{vr:.1f}</td>"
                "<td>{hs:.3f}%</td><td>{ar:.2f}</td><td>{lbc}</td><td>{score}</td>"
                "<td>{hy}</td></tr>".format(
                    cls=cls,
                    i=i,
                    code=r["code"],
                    name=r["name"],
                    pct=r["open_pct"],
                    vol=r["auction_shares"] / 1e4,
                    vr=r["vol_ratio"],
                    hs=r["turnover"],
                    ar=r["amt_ratio"],
                    lbc=r.get("lbc", ""),
                    score=score_s,
                    hy=r.get("hy") or "",
                )
            )
        return "\n".join(out)

    cards = []
    medals = ("①", "②", "③", "④", "⑤")
    for i, r in enumerate(picked["top5"][:5]):
        why = "；".join((r.get("reasons") or [])[:4])
        cards.append(
            f"""<article class="card"><div class="medal">{medals[i]}</div>
            <h2>{r['name']} <span>{r['code']}</span></h2>
            <p class="score">高开 {r['open_pct']:.2f}% · 分 {r.get('score', '-')} · {r.get('lbc', '?')}板</p>
            <p class="why">{why}</p>
            <dl>
              <div><dt>竞价量</dt><dd>{r['auction_shares']/1e4:.0f} 万股</dd></div>
              <div><dt>量比</dt><dd>{r['vol_ratio']:.1f}</dd></div>
              <div><dt>换手</dt><dd>{r['turnover']:.3f}%</dd></div>
              <div><dt>金额比</dt><dd>{r['amt_ratio']:.2f}</dd></div>
            </dl></article>"""
        )
    if not cards:
        cards.append("<p class='empty'>过滤后无标的</p>")
    title = "连板优化 v2" if mode == "optimized" else "竞价涨停取反（原版）"
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title} {meta.get('trade_date') or ''}</title>
<style>
:root {{ --bg:#f3efe6; --ink:#1c1914; --muted:#6b6358; --card:#fffdf8; --line:#ddd4c4; --accent:#0f5c4c; --gold:#9a6b16; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:"Segoe UI","PingFang SC","Noto Sans SC",sans-serif; background:
  radial-gradient(1200px 500px at 10% -10%, #d9ebe4 0%, transparent 55%),
  radial-gradient(900px 400px at 100% 0%, #f0e0c8 0%, transparent 50%),
  var(--bg); color:var(--ink); }}
main {{ max-width:1100px; margin:0 auto; padding:28px 20px 48px; }}
h1 {{ font-size:28px; letter-spacing:.02em; margin:0 0 6px; }}
.sub {{ color:var(--muted); margin:0 0 20px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:4px; padding:14px; }}
.medal {{ color:var(--gold); font-size:18px; }}
h2 {{ font-size:18px; margin:4px 0; }} h2 span {{ color:var(--muted); font-weight:500; font-size:14px; }}
.score {{ color:var(--accent); font-weight:600; margin:0 0 6px; }}
.why {{ color:var(--muted); font-size:12px; min-height:2.4em; }}
dl {{ display:grid; grid-template-columns:1fr 1fr; gap:6px; margin:0; }}
dt {{ color:var(--muted); font-size:11px; }} dd {{ margin:0; font-weight:600; }}
table {{ width:100%; border-collapse:collapse; margin-top:18px; font-size:14px; background:var(--card); }}
th,td {{ border-bottom:1px solid var(--line); padding:8px 6px; text-align:left; }}
tr.top td {{ color:var(--accent); font-weight:600; }}
.empty {{ color:var(--muted); }}
</style></head>
<body><main>
<h1>{title}</h1>
<p class="sub">{meta['generated_at']} · 昨涨停日 {meta['zt_date']} · 主板非ST {meta['main_n']} 只 · mode={mode}</p>
<div class="grid">{''.join(cards)}</div>
<h2>最终标的</h2>
<table><thead><tr><th>#</th><th>代码</th><th>名称</th><th>竞价涨幅</th><th>竞价量(万)</th><th>量比</th><th>换手</th><th>金额比</th><th>高度</th><th>分数</th><th>板块</th></tr></thead>
<tbody>{rows_html(picked['top5']) or '<tr><td colspan="11">无</td></tr>'}</tbody></table>
<p class="sub">自由流通用东方财富流通A股近似。研究用，不构成投资建议。</p>
</main></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument(
        "--mode",
        choices=("optimized", "baseline"),
        default="optimized",
        help="optimized=连板优化v2；baseline=原问财条件",
    )
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()
    now = datetime.now(CST)
    zt_date, pool = latest_zt_date(now)
    cands = [x for x in pool if is_main_board(x["c"], x["n"])]
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    done = 0
    with ThreadPoolExecutor(max_workers=8) as pool_ex:
        futs = {pool_ex.submit(enrich, zt): zt for zt in cands}
        for fut in as_completed(futs):
            zt = futs[fut]
            done += 1
            try:
                row = fut.result()
                if row:
                    rows.append(row)
                else:
                    errors.append(f"{zt['c']} {zt['n']} no auction bar")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{zt['c']} {zt['n']} {exc}")
            print(f"\rfetch {done}/{len(cands)} ok={len(rows)} err={len(errors)}", end="", file=sys.stderr)
    print(file=sys.stderr)

    if args.mode == "baseline":
        picked = sequential_select(rows)
    else:
        picked = optimized_select(rows, top_n=args.top)

    trade_date = rows[0]["trade_date"] if rows else now.strftime("%Y-%m-%d")
    meta = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "zt_date": zt_date,
        "trade_date": trade_date,
        "zt_total": len(pool),
        "main_n": len(cands),
        "fetched": len(rows),
        "mode": args.mode,
        "errors": errors,
    }
    text = render_text(picked, meta, args.mode)
    print(text)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = trade_date.replace("-", "")
    payload = {
        **meta,
        "top5": picked["top5"],
        "top8": picked.get("top8", []),
        "after_numeric": picked.get("after_numeric", []),
    }
    prefix = "auction-lianban-opt" if args.mode == "optimized" else "auction-zt-reversal"
    (out_dir / f"{prefix}-{stamp}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / f"{prefix}-{stamp}.html").write_text(render_html(picked, meta, args.mode), encoding="utf-8")
    (out_dir / f"{prefix}-latest.html").write_text(render_html(picked, meta, args.mode), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

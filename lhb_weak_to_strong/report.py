"""Offline single-file HTML report for weak-to-strong LHB analysis."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _esc(v: Any) -> str:
    return html.escape("" if v is None else str(v))


def _fmt_yi(v: float | int | None) -> str:
    if v is None:
        return "—"
    return f"{float(v) / 1e8:.2f}亿"


def _fmt_pct(v: float | int | None, signed: bool = True) -> str:
    if v is None:
        return "—"
    x = float(v)
    if signed:
        return f"{x:+.2f}%"
    return f"{x:.2f}%"


def _tier_class(tier: str) -> str:
    return {
        "S": "tier-s",
        "A": "tier-a",
        "B": "tier-b",
        "C": "tier-c",
        "F": "tier-f",
    }.get(tier, "tier-c")


def render_html(result: dict[str, Any], backtest: dict[str, Any] | None = None) -> str:
    date = result["trade_date"]
    cands = result.get("candidates") or []
    dumps = result.get("weak_dump") or []
    summary = result.get("summary") or {}
    anchors = result.get("anchor_cases") or []

    cards = []
    for c in cands:
        seats_html = "".join(
            f"<li><span class='seat-kind'>{_esc(s['kind'])}</span> {_esc(s['name'])} "
            f"<b>{_fmt_yi(s['net'])}</b></li>"
            for s in (c.get("buy_seats") or [])[:5]
        )
        notes = " · ".join(_esc(n) for n in (c.get("notes") or []))
        t1 = c.get("t1")
        t5 = c.get("t5")
        cards.append(
            f"""
            <article class="card {_tier_class(c.get('tier'))}">
              <header>
                <div class="code-line">
                  <span class="tier">{_esc(c.get('tier'))}</span>
                  <strong>{_esc(c.get('name'))}</strong>
                  <span class="code">{_esc(c.get('code'))}</span>
                  <span class="score">{c.get('score', 0):.1f}</span>
                </div>
                <div class="pattern">{_esc(c.get('pattern'))}</div>
              </header>
              <div class="metrics">
                <div><label>当日涨跌</label><b class="neg">{_fmt_pct(c.get('chg'))}</b></div>
                <div><label>龙虎净买</label><b class="pos">{_fmt_yi(c.get('net'))}</b></div>
                <div><label>净买占比</label><b>{_fmt_pct(c.get('ratio'), signed=False)}</b></div>
                <div><label>换手</label><b>{_fmt_pct(c.get('turnover'), signed=False)}</b></div>
                <div><label>机构席</label><b>{c.get('n_inst', 0)}</b></div>
                <div><label>北向席</label><b>{c.get('n_north', 0)}</b></div>
                <div><label>上榜后1日</label><b class="{'pos' if (t1 or 0) > 0 else 'neg'}">{_fmt_pct(t1)}</b></div>
                <div><label>上榜后5日</label><b class="{'pos' if (t5 or 0) > 0 else 'neg'}">{_fmt_pct(t5)}</b></div>
              </div>
              <p class="action">{_esc(c.get('action'))}</p>
              <p class="notes">{notes}</p>
              <p class="reason">上榜原因：{_esc(c.get('list_reason'))}</p>
              <ul class="seats">{seats_html or '<li>席位未取到</li>'}</ul>
            </article>
            """
        )

    dump_rows = "".join(
        f"<tr><td>{_esc(x['code'])}</td><td>{_esc(x['name'])}</td>"
        f"<td class='neg'>{_fmt_pct(x['chg'])}</td>"
        f"<td class='neg'>{_fmt_yi(x['net'])}</td>"
        f"<td>{_fmt_pct(x.get('t1'))}</td>"
        f"<td>{_fmt_pct(x.get('t5'))}</td></tr>"
        for x in dumps
    )

    anchor_lis = "".join(
        f"<li><b>{_esc(a['name'])}（{a['code']}）</b> — {_esc(a['note'])}</li>" for a in anchors
    )

    playbook = "".join(f"<li>{_esc(s)}</li>" for s in (summary.get("playbook") or []))

    bt_html = ""
    if backtest:
        f = backtest.get("weak_to_strong_filtered") or {}
        c = backtest.get("cluster_days_filtered") or {}
        d = backtest.get("weak_dump") or {}
        r = backtest.get("weak_to_strong_raw") or {}
        bt_html = f"""
        <section class="panel">
          <h2>回测快照（{ _esc(backtest.get('start')) } ~ { _esc(backtest.get('end')) }）</h2>
          <div class="bt-grid">
            <div><h3>弱势出货（跌≤-7% 且净买≤0）</h3>
              <p>n={d.get('n')} · T+1均 {_esc(d.get('t1_mean'))}% · 胜率 {_esc(d.get('t1_win'))}%</p></div>
            <div><h3>弱转强粗筛（仅跌+净买>0）</h3>
              <p>n={r.get('n')} · T+1均 {_esc(r.get('t1_mean'))}% · 胜率 {_esc(r.get('t1_win'))}%</p></div>
            <div><h3>加门槛（净买≥3000万 & 占比≥1.5%）</h3>
              <p>n={f.get('n')} · T+1均 {_esc(f.get('t1_mean'))}% · 胜率 {_esc(f.get('t1_win'))}%</p></div>
            <div><h3>共振日子集（同日候选≥3）</h3>
              <p>n={c.get('n')} · T+1均 {_esc(c.get('t1_mean'))}% · 胜率 {_esc(c.get('t1_win'))}%</p></div>
          </div>
          <p class="fine">{_esc(backtest.get('note'))}</p>
        </section>
        """

    # Methods from literature
    methods = result.get("methods") or []
    methods_html = "".join(
        f"""<div class="method">
          <h3>{_esc(m.get('name'))}</h3>
          <p class="fine">来源：{_esc(m.get('source'))}</p>
          <ul>{''.join(f'<li>{_esc(r)}</li>' for r in (m.get('rules') or []))}</ul>
        </div>"""
        for m in methods
    )

    # Research analogs + cluster insight
    research = result.get("research") or {}
    insight = research.get("cluster_insight") or {}
    analogs = research.get("similar_analogs") or []
    cluster_days = research.get("cluster_days") or []
    analog_rows = "".join(
        f"<tr><td>{_esc(a.get('date'))}</td><td>{_esc(a.get('code'))}</td><td>{_esc(a.get('name'))}</td>"
        f"<td class='neg'>{_fmt_pct(a.get('chg'))}</td><td class='pos'>{_esc(a.get('net_yi'))}亿</td>"
        f"<td>{_esc(a.get('ratio'))}%</td><td class='{'pos' if (a.get('t1') or 0)>0 else 'neg'}'>{_fmt_pct(a.get('t1'))}</td>"
        f"<td>{_fmt_pct(a.get('t5'))}</td></tr>"
        for a in analogs[:18]
    )
    cluster_rows = "".join(
        f"<tr class='q-{_esc(x.get('quality'))}'><td>{_esc(x.get('date'))}</td><td>{_esc(x.get('n'))}</td>"
        f"<td>{_esc(x.get('t1_mean'))}%</td><td>{_esc(x.get('t1_win'))}%</td>"
        f"<td>{_esc(x.get('idx_day'))}%</td><td>{_esc(x.get('idx_next'))}%</td>"
        f"<td>{_esc(x.get('quality'))}</td></tr>"
        for x in sorted(cluster_days, key=lambda z: z.get("t1_mean") or -999, reverse=True)
    )
    idx_info = (summary.get("index") or {})
    research_html = ""
    if research:
        research_html = f"""
        <section class="panel">
          <h2>相似样本与共振质量（{ _esc(research.get('window')) }）</h2>
          <p class="fine">{_esc(insight.get('finding'))}</p>
          <p class="fine">T+1 与次日指数相关性：{_esc(insight.get('corr_t1_vs_idx_next'))}；
            优质日次日指数均值 {_esc(insight.get('good_avg_idx_next'))}% /
            劣质日 {_esc(insight.get('bad_avg_idx_next'))}%</p>
          <h3>共振日对照</h3>
          <table>
            <thead><tr><th>日期</th><th>候选数</th><th>T+1均</th><th>胜率</th><th>当日指数</th><th>次日指数</th><th>质量</th></tr></thead>
            <tbody>{cluster_rows or '<tr><td colspan="7">无</td></tr>'}</tbody>
          </table>
          <h3>最像 8.3 甜区的历史样本</h3>
          <table>
            <thead><tr><th>日期</th><th>代码</th><th>名称</th><th>涨跌</th><th>净买</th><th>占比</th><th>T+1</th><th>T+5</th></tr></thead>
            <tbody>{analog_rows or '<tr><td colspan="8">无</td></tr>'}</tbody>
          </table>
        </section>
        """

    payload = json.dumps(
        {k: v for k, v in result.items() if k != "methods"},
        ensure_ascii=False,
        default=str,
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>龙虎榜弱转强 · {_esc(date)}</title>
<style>
:root {{
  --bg0: #0f1419;
  --bg1: #172029;
  --bg2: #1e2a36;
  --line: #2c3b4a;
  --text: #e7eef5;
  --muted: #8fa3b5;
  --pos: #e85d4c;
  --neg: #3cb89a;
  --accent: #d4a017;
  --s: #ff6b4a;
  --a: #f0a202;
  --b: #5b8def;
  --c: #7a8a99;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: "Source Han Sans SC", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--text);
  background:
    radial-gradient(1200px 600px at 10% -10%, #243447 0%, transparent 55%),
    radial-gradient(900px 500px at 100% 0%, #3a2a14 0%, transparent 50%),
    var(--bg0);
  line-height: 1.55;
}}
.wrap {{ max-width: 1120px; margin: 0 auto; padding: 28px 18px 60px; }}
.hero {{
  border: 1px solid var(--line);
  background: linear-gradient(135deg, rgba(212,160,23,.12), rgba(23,32,41,.9));
  padding: 28px 24px;
  border-radius: 4px;
  margin-bottom: 22px;
}}
.brand {{
  font-size: clamp(28px, 5vw, 42px);
  font-weight: 800;
  letter-spacing: .04em;
  margin: 0 0 8px;
}}
.hero h1 {{ font-size: clamp(18px, 2.4vw, 24px); font-weight: 600; margin: 0 0 10px; color: #f3d27a; }}
.hero p {{ margin: 0; color: var(--muted); max-width: 46rem; }}
.meta {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }}
.pill {{
  border: 1px solid var(--line);
  background: var(--bg2);
  padding: 6px 12px;
  font-size: 13px;
  color: var(--muted);
}}
.pill b {{ color: var(--text); }}
.panel {{
  border: 1px solid var(--line);
  background: rgba(23,32,41,.88);
  padding: 20px;
  margin-bottom: 18px;
  border-radius: 4px;
}}
.panel h2 {{ margin: 0 0 12px; font-size: 18px; }}
.panel h3 {{ margin: 16px 0 8px; font-size: 15px; color: #d7e3ee; }}
.panel ol, .panel ul {{ margin: 0; padding-left: 1.2rem; color: var(--muted); }}
.panel li {{ margin: 6px 0; }}
.grid {{ display: grid; gap: 14px; }}
@media (min-width: 860px) {{ .grid {{ grid-template-columns: 1fr 1fr; }} }}
.card {{
  border: 1px solid var(--line);
  background: var(--bg1);
  padding: 16px;
  border-left-width: 4px;
}}
.tier-s {{ border-left-color: var(--s); }}
.tier-a {{ border-left-color: var(--a); }}
.tier-b {{ border-left-color: var(--b); }}
.tier-c {{ border-left-color: var(--c); }}
.code-line {{ display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }}
.tier {{
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 28px; height: 28px; border-radius: 2px;
  background: #0006; font-weight: 800; font-size: 14px;
}}
.tier-s .tier {{ color: var(--s); }}
.tier-a .tier {{ color: var(--a); }}
.tier-b .tier {{ color: var(--b); }}
.code {{ color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
.score {{ margin-left: auto; font-size: 22px; font-weight: 800; color: var(--accent); }}
.pattern {{ color: #c9b27a; font-size: 13px; margin-top: 4px; }}
.metrics {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 12px 0;
}}
.metrics div {{ background: var(--bg2); padding: 8px; border: 1px solid var(--line); }}
.metrics label {{ display: block; color: var(--muted); font-size: 11px; }}
.metrics b {{ font-size: 14px; }}
.pos {{ color: var(--pos); }}
.neg {{ color: var(--neg); }}
.action {{ margin: 8px 0; color: #f0e6c8; }}
.notes, .reason, .fine {{ color: var(--muted); font-size: 13px; }}
.seats {{ margin: 8px 0 0; padding-left: 1.1rem; color: var(--muted); font-size: 12px; }}
.seat-kind {{
  display: inline-block; min-width: 4.5em; color: #9fc0df;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ border-bottom: 1px solid var(--line); padding: 8px 6px; text-align: left; }}
th {{ color: var(--muted); font-weight: 600; }}
.bt-grid, .method-grid {{ display: grid; gap: 10px; }}
@media (min-width: 800px) {{
  .bt-grid {{ grid-template-columns: 1fr 1fr; }}
  .method-grid {{ grid-template-columns: 1fr 1fr; }}
}}
.bt-grid > div, .method {{ background: var(--bg2); border: 1px solid var(--line); padding: 12px; }}
.bt-grid h3, .method h3 {{ margin: 0 0 6px; font-size: 14px; }}
.bt-grid p {{ margin: 0; color: var(--muted); font-size: 13px; }}
tr.q-good td:last-child {{ color: var(--pos); }}
tr.q-bad td:last-child {{ color: var(--neg); }}
footer {{ margin-top: 24px; color: var(--muted); font-size: 12px; }}
@media print {{
  body {{ background: #fff; color: #111; }}
  .hero, .panel, .card, .metrics div, .bt-grid > div, .method {{ background: #fff; color: #111; }}
  .pos {{ color: #b42318; }} .neg {{ color: #0f7b5c; }}
}}
</style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <p class="brand">顺势选股 · 龙虎榜弱转强</p>
      <h1>{_esc(date)} 净买入承接扫描</h1>
      <p>{_esc(summary.get('message'))}。核心逻辑：大跌日有真金白银承接（尤其机构/北向），比单纯追涨停更接近「弱转强」启动点。榜面只做概率增强，次日竞价才是验证。</p>
      <div class="meta">
        <div class="pill">评分版本 <b>{_esc(result.get('score_version'))}</b></div>
        <div class="pill">原始上榜 <b>{result.get('raw_count', 0)}</b></div>
        <div class="pill">弱转强候选 <b>{result.get('cluster_count', 0)}</b></div>
        <div class="pill">共振标记 <b>{"是" if summary.get("cluster_flag") else "否"}</b></div>
        <div class="pill">上证当日 <b>{_esc(idx_info.get('idx_day_pct'))}%</b></div>
        <div class="pill">上证次日 <b>{_esc(idx_info.get('idx_next_pct'))}%</b></div>
        <div class="pill">环境 <b>{_esc(idx_info.get('cluster_regime'))}</b></div>
      </div>
    </section>

    <section class="panel">
      <h2>锚定案例（2026-08-03）</h2>
      <ul>{anchor_lis}</ul>
    </section>

    <section class="panel">
      <h2>公开买入法 → 本工具映射</h2>
      <div class="method-grid">{methods_html or '<p class="fine">无</p>'}</div>
    </section>

    <section class="panel">
      <h2>操作手册</h2>
      <ol>{playbook}</ol>
    </section>

    <section class="panel">
      <h2>今日候选（按评分）</h2>
      <div class="grid">
        {''.join(cards) if cards else '<p class="fine">无候选。可能是非交易日，或当日没有「大跌+净买入」标的。</p>'}
      </div>
    </section>

    <section class="panel">
      <h2>对照：弱势出货（大跌且净卖）</h2>
      <table>
        <thead><tr><th>代码</th><th>名称</th><th>涨跌</th><th>净买</th><th>T+1</th><th>T+5</th></tr></thead>
        <tbody>{dump_rows or '<tr><td colspan="6">无</td></tr>'}</tbody>
      </table>
    </section>

    {research_html}
    {bt_html}

    <footer>
      数据来源：东方财富/交易所公开龙虎榜（经 akshare）。买入法要点综合公开复盘框架与样本回测。仅供研究复盘，不构成投资建议。市场有风险，交易需谨慎。
    </footer>
  </div>
  <script type="application/json" id="wts-data">{html.escape(payload)}</script>
</body>
</html>
"""


def write_report(
    result: dict[str, Any],
    out_path: str | Path,
    backtest: dict[str, Any] | None = None,
) -> Path:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(result, backtest=backtest), encoding="utf-8")
    return path

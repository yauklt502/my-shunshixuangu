#!/usr/bin/env python3
"""昨日首板 → 今日竞价一进二评分。

数据：东方财富涨停池（昨收）+ 新浪行情（竞价/实时盘口）。
默认交易日取最近一个已收盘日的涨停池，再对当日 09:25 竞价打分。
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any

CST = timezone(timedelta(hours=8))
CTX = ssl.create_default_context()
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

ZT_URL = (
    "https://push2ex.eastmoney.com/getTopicZTPool"
    "?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
    "&Pageindex=0&pagesize=200&sort=lbc:desc&date={date}"
)
SINA_URL = "https://hq.sinajs.cn/list={codes}"
TREND_URL = (
    "https://push2.eastmoney.com/api/qt/stock/trends2/get"
    "?fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13"
    "&fields2=f51,f52,f53,f54,f55,f56,f57,f58"
    "&ut=fa5fd1943c7b386f172d6893dbfba10b&ndays=1&iscr=0&iscca=0&secid={secid}"
)


def http_json(url: str) -> Any:
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Referer": "https://quote.eastmoney.com/"}
    )
    with urllib.request.urlopen(req, timeout=25, context=CTX) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def http_text(url: str, encoding: str = "gbk") -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Referer": "https://finance.sina.com.cn/"}
    )
    with urllib.request.urlopen(req, timeout=25, context=CTX) as resp:
        return resp.read().decode(encoding, "replace")


def yyyymmdd(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")


def parse_fbt(t: int) -> str:
    s = f"{int(t):06d}"
    return f"{s[0:2]}:{s[2:4]}:{s[4:6]}"


def sina_prefix(code: str) -> str:
    if code.startswith(("6", "9")):
        return "sh" + code
    if code.startswith(("8", "4")):
        return "bj" + code
    return "sz" + code


def limit_pct(code: str, name: str) -> float:
    if "ST" in name or "退" in name:
        return 5.0
    if code.startswith("3") or code.startswith("68"):
        return 20.0
    if code.startswith(("8", "4")):
        return 30.0
    return 10.0


def fetch_zt_pool(date: str) -> list[dict[str, Any]]:
    data = http_json(ZT_URL.format(date=date))
    pool = (data.get("data") or {}).get("pool") or []
    return pool


def fetch_sina_quotes(codes: list[str]) -> dict[str, dict[str, Any]]:
    if not codes:
        return {}
    text = http_text(SINA_URL.format(codes=",".join(sina_prefix(c) for c in codes)))
    out: dict[str, dict[str, Any]] = {}
    for line in text.splitlines():
        if "hq_str_" not in line or "=" not in line:
            continue
        left, right = line.split("=", 1)
        code = left.split("hq_str_")[-1][2:]
        right = right.strip().strip(";").strip('"')
        parts = right.split(",")
        if len(parts) < 32 or not parts[2]:
            continue
        bids = [
            (float(parts[10 + i * 2] or 0), float(parts[11 + i * 2] or 0))
            for i in range(5)
        ]
        asks = [
            (float(parts[20 + i * 2] or 0), float(parts[21 + i * 2] or 0))
            for i in range(5)
        ]
        out[code] = {
            "name": parts[0],
            "open": float(parts[1] or 0),
            "prev": float(parts[2] or 0),
            "last": float(parts[3] or 0),
            "high": float(parts[4] or 0),
            "low": float(parts[5] or 0),
            "vol": float(parts[8] or 0),
            "amt": float(parts[9] or 0),
            "bids": bids,
            "asks": asks,
            "date": parts[30],
            "time": parts[31],
        }
    return out


def em_secid(code: str) -> str:
    return ("1." if code.startswith(("6", "9")) else "0.") + code


def fetch_first_bar(code: str) -> dict[str, Any] | None:
    """A 股 09:30 第一根 K 的成交额近似集合竞价成交。"""
    url = TREND_URL.format(secid=em_secid(code))
    for _ in range(3):
        try:
            data = http_json(url)
            trends = (data.get("data") or {}).get("trends") or []
            if not trends:
                return None
            parts = trends[0].split(",")
            return {
                "time": parts[0],
                "open": float(parts[1]),
                "close": float(parts[2]),
                "high": float(parts[3]),
                "low": float(parts[4]),
                "vol": float(parts[5]),
                "amt": float(parts[6]),
            }
        except Exception:
            time.sleep(0.25)
    return None


def fetch_first_bars(codes: list[str]) -> dict[str, dict[str, Any] | None]:
    out: dict[str, dict[str, Any] | None] = {}
    with ThreadPoolExecutor(16) as pool:
        futs = {pool.submit(fetch_first_bar, c): c for c in codes}
        for fut in as_completed(futs):
            out[futs[fut]] = fut.result()
    return out


def score_row(
    zt: dict[str, Any],
    quote: dict[str, Any],
    plate_n: int,
    first_bar: dict[str, Any] | None = None,
) -> dict[str, Any]:
    code = zt["c"]
    name = zt["n"]
    lp = limit_pct(code, name)
    prev = quote["prev"]
    openp = quote["open"] or quote["last"]
    zt_price = round(prev * (1 + lp / 100.0) + 1e-8, 2)
    open_pct = (openp / prev - 1) * 100 if prev else 0.0
    is_auction_zt = openp >= zt_price - 0.011
    yamt = float(zt["amount"] or 0)
    if first_bar and first_bar.get("amt"):
        auction_amt = float(first_bar["amt"])
    elif first_bar is None:
        auction_amt = float(quote["amt"] or 0)
    else:
        auction_amt = 0.0
    ratio = (auction_amt / yamt * 100) if yamt else 0.0
    bid1_vol, bid1_px = quote["bids"][0]
    ask1_vol, ask1_px = quote["asks"][0]
    bid_amt = bid1_vol * bid1_px
    ask_amt = ask1_vol * ask1_px
    imbalance = (bid_amt - ask_amt) / (bid_amt + ask_amt + 1)
    ltsz_yi = float(zt["ltsz"]) / 1e8
    fbt = int(zt["fbt"])
    zbc = int(zt["zbc"])
    hs = float(zt["hs"])
    hy = zt.get("hybk") or ""
    days = (zt.get("zttj") or {}).get("days", 1)
    ct = (zt.get("zttj") or {}).get("ct", 1)

    score = 0.0
    reasons: list[str] = []

    if is_auction_zt:
        score += 38
        reasons.append("竞价涨停")
        one_word = bool(
            first_bar and float(first_bar.get("low") or 0) >= zt_price - 0.011
        )
        live_sealed = ask1_vol <= 0 or ask1_px == 0
        if one_word or (first_bar is None and live_sealed):
            # 已封死是一进二晋级概率的最强信号，权重大于“高开未封”。
            score += 28
            reasons.append("竞价一字/封死")
        elif live_sealed:
            score += 10
            reasons.append("盘中封死(非竞价)")
        elif ask_amt < bid_amt * 0.2:
            score += 10
            reasons.append("竞价封单占优")
        # 开盘后的实时封单是事后信息，竞价评分只用首分钟是否一字。
        if first_bar is None:
            seal_ratio = (bid_amt / float(zt["ltsz"])) * 100 if zt.get("ltsz") else 0.0
            if seal_ratio >= 5:
                score += 10
                reasons.append(f"封成比{seal_ratio:.1f}%厚")
            elif seal_ratio >= 2:
                score += 6
                reasons.append(f"封成比{seal_ratio:.1f}%尚可")
            elif seal_ratio >= 1:
                score += 3
                reasons.append(f"封成比{seal_ratio:.1f}%偏薄")
            else:
                score -= 2
                reasons.append(f"封成比{seal_ratio:.1f}%过薄")
        if 3 <= hs <= 15 and 2.5 <= ratio <= 8:
            score += 6
            reasons.append("换手板缩量一字")
    elif 6.0 <= open_pct < lp - 0.3:
        score += 32
        reasons.append(f"高开{open_pct:.2f}%偏强")
    elif 3.5 <= open_pct < 6.0:
        score += 26
        reasons.append(f"高开{open_pct:.2f}%适中")
    elif 1.5 <= open_pct < 3.5:
        score += 16
        reasons.append(f"小高开{open_pct:.2f}%")
    elif 0 <= open_pct < 1.5:
        score += 8
        reasons.append(f"平附近开{open_pct:.2f}%")
    elif -2 <= open_pct < 0:
        score += 3
        reasons.append(f"小低开{open_pct:.2f}%")
    else:
        score -= 8
        reasons.append(f"明显低开{open_pct:.2f}%")

    if 4 <= ratio <= 12:
        score += 16
        reasons.append(f"竞价量比健康{ratio:.1f}%")
    elif 2.5 <= ratio < 4:
        score += 10
        reasons.append(f"竞价量比略弱{ratio:.1f}%")
    elif 12 < ratio <= 18:
        score += 8
        reasons.append(f"竞价量比较大{ratio:.1f}%")
    elif 18 < ratio <= 28:
        # 一字板上放量=抛压被吃掉；未封死放量才是真分歧。
        if is_auction_zt:
            score += 6
            reasons.append(f"竞价放量换手{ratio:.1f}%")
        else:
            score += 2
            reasons.append(f"竞价放量过猛{ratio:.1f}%")
    elif ratio > 28:
        score -= 6
        reasons.append(f"竞价巨量分歧{ratio:.1f}%")
    else:
        score -= 2
        reasons.append(f"竞价缩量{ratio:.1f}%")

    if is_auction_zt and first_bar is None:
        if bid_amt >= 3e7:
            score += 8
            reasons.append(f"封单约{bid_amt / 1e8:.2f}亿")
        elif bid_amt >= 8e6:
            score += 4
            reasons.append(f"封单约{bid_amt / 1e8:.2f}亿")
    elif not is_auction_zt:
        if imbalance > 0.4 and open_pct > 1:
            score += 6
            reasons.append("买盘占优")
        elif imbalance < -0.4 and open_pct < 3:
            score -= 4
            reasons.append("卖盘占优")

    if fbt <= 93030:
        score += 10
        reasons.append("昨日秒板/早封")
    elif fbt <= 100000:
        score += 7
        reasons.append("昨日早盘封")
    elif fbt <= 103000:
        score += 4
        reasons.append("昨日午前封")
    elif fbt <= 130000:
        score += 1
        reasons.append("昨日午盘封")
    else:
        score -= 3
        reasons.append("昨日尾盘偷袭")

    if zbc == 0:
        score += 6
        reasons.append("昨日未开板")
    elif zbc == 1:
        score += 1
        reasons.append("昨日开板1次")
    else:
        score -= 4
        reasons.append(f"昨日烂板开{zbc}次")

    if 3 <= hs <= 12:
        score += 8
        reasons.append(f"昨换手适中{hs:.1f}%")
    elif 12 < hs <= 20:
        score += 3
        reasons.append(f"昨换手偏高{hs:.1f}%")
    elif hs > 20:
        score -= 5
        reasons.append(f"昨换手过大{hs:.1f}%")
    elif 1 <= hs < 3:
        score += 4
        reasons.append(f"昨换手偏低{hs:.1f}%")
    else:
        score += 1
        reasons.append(f"昨换手极低{hs:.1f}%偏一字")

    if 15 <= ltsz_yi <= 80:
        score += 8
        reasons.append(f"流通{ltsz_yi:.0f}亿适中")
    elif 80 < ltsz_yi <= 150:
        score += 4
        reasons.append(f"流通{ltsz_yi:.0f}亿偏大")
    elif 8 <= ltsz_yi < 15:
        score += 3
        reasons.append(f"流通{ltsz_yi:.0f}亿偏小")
    elif ltsz_yi > 300:
        score -= 8
        reasons.append(f"流通{ltsz_yi:.0f}亿过大")
    elif ltsz_yi > 150:
        score -= 2
        reasons.append(f"流通{ltsz_yi:.0f}亿偏大")

    if plate_n >= 3:
        score += 10
        reasons.append(f"板块效应{hy}{plate_n}家首板")
    elif plate_n == 2:
        score += 5
        reasons.append(f"板块跟风{hy}2家")
    else:
        reasons.append(f"独苗{hy}")

    if lp >= 20:
        if is_auction_zt:
            score += 2
        else:
            score -= 6
            reasons.append("创业/科创20cm一进二更难")

    if yamt > 2e9 and not is_auction_zt:
        score -= 4
        reasons.append("昨成交过大承接难")

    if ct >= 3 and days <= 10:
        score += 3
        reasons.append(f"近期{days}天{ct}板股性活")

    seal_ratio = (bid_amt / float(zt["ltsz"])) * 100 if zt.get("ltsz") else 0.0
    return {
        "code": code,
        "name": name,
        "hy": hy,
        "plate_n": plate_n,
        "open_pct": round(open_pct, 2),
        "is_auction_zt": is_auction_zt,
        "ratio": round(ratio, 1),
        "amt": auction_amt,
        "yamt": yamt,
        "hs": round(hs, 1),
        "zbc": zbc,
        "fbt": parse_fbt(fbt),
        "lbt": parse_fbt(int(zt["lbt"])),
        "ltsz": round(ltsz_yi, 1),
        "fund": round(float(zt["fund"]) / 1e8, 2),
        "bid_amt": bid_amt,
        "ask_amt": ask_amt,
        "seal_ratio": round(seal_ratio, 2),
        "open": openp,
        "prev": prev,
        "last": quote["last"],
        "zt_price": zt_price,
        "time": quote["time"],
        "lp": lp,
        "score": round(score, 1),
        "reasons": reasons,
        "days": days,
        "ct": ct,
    }


def rank_first_boards(zt_date: str) -> dict[str, Any]:
    pool = fetch_zt_pool(zt_date)
    first = [x for x in pool if int(x.get("lbc") or 0) == 1]
    plate = Counter(x.get("hybk") or "" for x in first)
    quotes = fetch_sina_quotes([x["c"] for x in first])
    now = datetime.now(CST)
    first_bars: dict[str, dict[str, Any] | None] = {}
    if now.hour > 9 or (now.hour == 9 and now.minute >= 30):
        first_bars = fetch_first_bars([x["c"] for x in first])
    rows = []
    missing = []
    for zt in first:
        q = quotes.get(zt["c"])
        if not q or not q.get("prev"):
            missing.append(f"{zt['c']} {zt['n']}")
            continue
        rows.append(
            score_row(
                zt,
                q,
                plate[zt.get("hybk") or ""],
                first_bars.get(zt["c"]) if not first_bars else (first_bars.get(zt["c"]) or {"amt": 0}),
            )
        )
    rows.sort(key=lambda r: r["score"], reverse=True)
    return {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "zt_date": zt_date,
        "trade_date": now.strftime("%Y-%m-%d"),
        "zt_total": len(pool),
        "first_total": len(first),
        "max_lbc": max((int(x.get("lbc") or 0) for x in pool), default=0),
        "max_name": next(
            (x["n"] for x in pool if int(x.get("lbc") or 0) == max((int(y.get("lbc") or 0) for y in pool), default=0)),
            "",
        ),
        "plate": plate.most_common(),
        "missing": missing,
        "rows": rows,
        "top3": rows[:3],
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"一进二竞价评分  {result['generated_at']}",
        f"昨涨停池 {result['zt_date']}  涨停{result['zt_total']}只  首板{result['first_total']}只  高度{result['max_lbc']}板{result['max_name']}",
        "",
        "今日一进二概率最高 3 只：",
    ]
    for i, r in enumerate(result["top3"], 1):
        tag = "竞价封死" if r["is_auction_zt"] and r["ask_amt"] <= 0 else (
            "竞价涨停" if r["is_auction_zt"] else f"高开{r['open_pct']:.2f}%"
        )
        lines.append(
            f"  {i}. {r['name']} {r['code']}  {tag}  "
            f"量比{r['ratio']:.1f}%  封单{r['bid_amt']/1e8:.2f}亿  "
            f"昨封{r['fbt']} 炸{r['zbc']}  分{r['score']:.0f}"
        )
        lines.append(f"     {' | '.join(r['reasons'][:6])}")
    lines += ["", "完整排序（前15）："]
    for i, r in enumerate(result["rows"][:15], 1):
        lines.append(
            f"{i:2d} {r['code']} {r['name']:8s} {r['open_pct']:+6.2f}% "
            f"量比{r['ratio']:5.1f}% 流通{r['ltsz']:6.1f}亿 {r['hy']} 分{r['score']:5.1f}"
        )
    return "\n".join(lines) + "\n"


def render_html(result: dict[str, Any]) -> str:
    top_cards = []
    medals = ("①", "②", "③")
    for i, r in enumerate(result["top3"]):
        reasons = "".join(f"<li>{x}</li>" for x in r["reasons"])
        seal = f"{r['bid_amt']/1e8:.2f}亿" if r["is_auction_zt"] else "—"
        top_cards.append(
            f"""
            <article class="card">
              <div class="medal">{medals[i]}</div>
              <h2>{r['name']} <span>{r['code']}</span></h2>
              <p class="score">评分 {r['score']:.0f}</p>
              <dl>
                <div><dt>竞价</dt><dd>{r['open_pct']:+.2f}% {'（涨停）' if r['is_auction_zt'] else ''}</dd></div>
                <div><dt>量比</dt><dd>{r['ratio']:.1f}%</dd></div>
                <div><dt>买一/封单</dt><dd>{seal}</dd></div>
                <div><dt>昨封</dt><dd>{r['fbt']} 炸{r['zbc']}</dd></div>
                <div><dt>昨换手</dt><dd>{r['hs']:.1f}%</dd></div>
                <div><dt>流通</dt><dd>{r['ltsz']:.1f}亿 · {r['hy']}</dd></div>
              </dl>
              <ul>{reasons}</ul>
            </article>
            """
        )
    rows_html = []
    for i, r in enumerate(result["rows"], 1):
        cls = "top" if i <= 3 else ""
        rows_html.append(
            f"<tr class='{cls}'><td>{i}</td><td>{r['code']}</td><td>{r['name']}</td>"
            f"<td>{r['open_pct']:+.2f}%</td><td>{r['ratio']:.1f}%</td>"
            f"<td>{r['bid_amt']/1e8:.2f}</td><td>{r['hs']:.1f}%</td>"
            f"<td>{r['fbt']}</td><td>{r['zbc']}</td><td>{r['ltsz']:.1f}</td>"
            f"<td>{r['hy']}</td><td>{r['score']:.0f}</td></tr>"
        )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>一进二竞价 {result['trade_date']}</title>
<style>
  :root {{ color-scheme: dark; --bg:#0f1419; --card:#1a2332; --line:#2a3545; --text:#e8eef5; --muted:#8b9bb0; --red:#ff5c5c; --gold:#f5c542; }}
  body {{ margin:0; font-family: "Segoe UI", "PingFang SC", sans-serif; background:var(--bg); color:var(--text); }}
  header {{ padding:28px 24px 8px; }}
  h1 {{ margin:0 0 8px; font-size:22px; }}
  .meta {{ color:var(--muted); font-size:13px; }}
  .grid {{ display:grid; gap:16px; padding:16px 24px 8px; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; }}
  .medal {{ font-size:22px; }}
  .card h2 {{ margin:6px 0 0; font-size:20px; }}
  .card h2 span {{ color:var(--muted); font-size:14px; font-weight:500; }}
  .score {{ color:var(--gold); font-weight:700; margin:6px 0 12px; }}
  dl {{ display:grid; grid-template-columns:1fr 1fr; gap:8px 12px; margin:0 0 10px; }}
  dt {{ color:var(--muted); font-size:12px; }} dd {{ margin:0; font-size:14px; }}
  ul {{ margin:0; padding-left:18px; color:var(--muted); font-size:13px; }}
  table {{ width:calc(100% - 48px); margin:12px 24px 40px; border-collapse:collapse; font-size:13px; }}
  th,td {{ border-bottom:1px solid var(--line); padding:8px 6px; text-align:left; }}
  tr.top td {{ color:var(--gold); font-weight:600; }}
  footer {{ color:var(--muted); font-size:12px; padding:0 24px 32px; }}
</style>
</head>
<body>
<header>
  <h1>今日一进二 · 竞价概率最高 3 只</h1>
  <p class="meta">{result['generated_at']}　昨涨停池 {result['zt_date']}　涨停 {result['zt_total']} / 首板 {result['first_total']}　高度 {result['max_lbc']}板{result['max_name']}</p>
</header>
<section class="grid">{''.join(top_cards)}</section>
<table>
  <thead><tr><th>#</th><th>代码</th><th>名称</th><th>开幅</th><th>量比%</th><th>买一亿</th><th>昨换手</th><th>昨封</th><th>炸</th><th>流通亿</th><th>行业</th><th>分</th></tr></thead>
  <tbody>{''.join(rows_html)}</tbody>
</table>
<footer>评分只反映竞价强弱，不构成投资建议。一进二仍取决于开盘后封单与板块情绪。</footer>
</body>
</html>
"""


def default_zt_date(now: datetime | None = None) -> str:
    now = now or datetime.now(CST)
    # 周一到周五 16:00 前，涨停池仍用上一交易日。
    d = now.date()
    if now.hour < 16:
        d = d - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


def score_fixture() -> None:
    """最小回归：竞价封死应排在高开未封之前。"""
    zt_seal = {
        "c": "000001",
        "n": "封死测",
        "amount": 2e8,
        "ltsz": 3e9,
        "fbt": 94300,
        "lbt": 94300,
        "zbc": 0,
        "hs": 8.0,
        "hybk": "测试",
        "fund": 3e7,
        "zttj": {"days": 1, "ct": 1},
    }
    q_seal = {
        "open": 11.0,
        "prev": 10.0,
        "last": 11.0,
        "amt": 1.6e7,
        "bids": [(20_000_000, 11.0)],
        "asks": [(0.0, 0.0)],
        "time": "09:25:00",
    }
    zt_open = dict(zt_seal)
    zt_open["n"] = "高开测"
    q_open = {
        "open": 10.7,
        "prev": 10.0,
        "last": 10.7,
        "amt": 1.4e7,
        "bids": [(50000, 10.7)],
        "asks": [(300, 10.71)],
        "time": "09:25:00",
    }
    s_seal = score_row(zt_seal, q_seal, 1)
    s_open = score_row(zt_open, q_open, 3)
    assert s_seal["is_auction_zt"]
    assert not s_open["is_auction_zt"]
    assert s_seal["score"] > s_open["score"], (s_seal["score"], s_open["score"])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="昨日首板今日竞价一进二评分")
    p.add_argument("--zt-date", help="昨涨停池日期 YYYYMMDD，默认上一交易日")
    p.add_argument("--json-out", help="写入 JSON 快照路径")
    p.add_argument("--html-out", help="写入 HTML 报告路径")
    p.add_argument("--top", type=int, default=3)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        score_fixture()
        print("self-test ok")
        return 0
    zt_date = args.zt_date or default_zt_date()
    result = rank_first_boards(zt_date)
    result["top3"] = result["rows"][: args.top]
    sys.stdout.write(render_text(result))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    if args.html_out:
        with open(args.html_out, "w", encoding="utf-8") as f:
            f.write(render_html(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

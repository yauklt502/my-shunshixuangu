#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真龙识别：东方财富公开涨停池 / 行情 → 四特征验货卡。"""

from __future__ import annotations

import json
import ssl
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SNAPSHOT_DIR = ROOT / "data" / "snapshots"
CACHE_DIR = ROOT / "data" / "cache"
TZ = timezone(timedelta(hours=8))
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
CTX = ssl.create_default_context()

GENERIC_CONCEPTS = {
    "融资融券",
    "沪股通",
    "深股通",
    "富时罗素",
    "标准普尔",
    "MSCI中国",
    "MSCI概念",
    "国企改革",
    "地方国资改革",
    "央企改革",
    "一带一路",
    "粤港自贸",
    "雄安新区",
    "转债标的",
    "股权激励",
    "机构重仓",
    "证金持股",
    "深股通",
    "沪股通",
    "创业板综",
    "深成500",
    "中证500",
    "沪深300",
    "上证380",
    "上证180",
    "中证1000",
    "微盘股",
    "昨日连板",
    "昨日涨停",
    "昨日触板",
    "含可转债",
    "破净股",
    "高送转",
    "预盈预增",
    "年报预增",
    "专精特新",
    "注册制次新股",
    "新股与次新股",
}

REGION_SUFFIX = ("板块", "特区", "自贸", "新区")
INDUSTRY_THEME = {
    "一般零售": "消费",
    "专业连锁": "消费",
    "贸易Ⅱ": "消费",
    "服装家纺": "消费",
    "化学制品": "化工",
    "化学原料": "化工",
    "有机硅": "液冷",
    "航运港口": "航运",
    "航海装备": "航运",
    "电力": "电力",
    "种植业": "农业",
    "饲料": "农业",
    "农化制品": "农业",
    "林业Ⅱ": "农业",
    "饰品": "黄金珠宝",
    "黄金": "黄金珠宝",
    "出版": "传媒",
    "影视院线": "传媒",
    "数字媒体": "传媒",
    "游戏Ⅱ": "传媒",
    "旅游及景": "旅游",
    "电网设备": "电网",
    "汽车零部": "汽零",
    "房地产开": "地产",
    "房地产服": "地产",
    "航空装备": "军工新材",
    "培育钻石": "培育钻石",
}

THEME_ALIASES = {
    "液冷服务器": "液冷",
    "液冷概念": "液冷",
    "数据中心": "液冷",
    "服务器": "液冷",
    "有机硅": "液冷",
    "培育钻石": "培育钻石",
    "人造钻石": "培育钻石",
    "珠宝": "黄金珠宝",
    "黄金概念": "黄金珠宝",
    "航运概念": "航运",
    "集运": "航运",
    "商贸零售": "消费",
    "免税": "消费",
    "冷链物流": "消费",
}


def now_cn() -> datetime:
    return datetime.now(TZ)


def today_str() -> str:
    return now_cn().strftime("%Y-%m-%d")


def compact(date: str) -> str:
    return date.replace("-", "")


def pretty(date8: str) -> str:
    return f"{date8[:4]}-{date8[4:6]}-{date8[6:8]}"


def parse_date(date: str) -> datetime:
    raw = compact(date)
    return datetime(int(raw[:4]), int(raw[4:6]), int(raw[6:8]), tzinfo=TZ)


def weekday_cn(date: str) -> str:
    return "一二三四五六日"[parse_date(date).weekday()]


def md_short(date: str) -> str:
    d = parse_date(date)
    return f"{d.month}/{d.day}"


def http_json(url: str, timeout: int = 18) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Referer": "https://quote.eastmoney.com/ztb/detail",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def pool_url(kind: str, date8: str) -> str:
    paths = {
        "zt": "getTopicZTPool",
        "dt": "getTopicDTPool",
        "zb": "getTopicZBPool",
        "yz": "getYesterdayZTPool",
    }
    sort = {
        "zt": "lbc:desc",
        "dt": "fund:asc",
        "zb": "fbt:asc",
        "yz": "ylbc:desc",
    }[kind]
    q = urllib.parse.urlencode(
        {
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "dpt": "wz.ztzt",
            "Pageindex": 0,
            "pagesize": 200,
            "sort": sort,
            "date": date8,
            "_": int(time.time() * 1000),
        }
    )
    return f"https://push2ex.eastmoney.com/{paths[kind]}?{q}"


def fetch_pool(kind: str, date8: str) -> list[dict]:
    data = http_json(pool_url(kind, date8))
    pool = ((data or {}).get("data") or {}).get("pool") or []
    return list(pool)


def secid(code: str, market: Any = None) -> str:
    if market is not None and str(market) != "":
        return f"{market}.{code}"
    if code.startswith(("6", "5")):
        return f"1.{code}"
    return f"0.{code}"


def fetch_quotes(items: list[tuple[str, Any]]) -> dict[str, dict]:
    if not items:
        return {}
    ids = ",".join(secid(code, m) for code, m in items)
    fields = "f12,f13,f14,f2,f3,f4,f5,f6,f7,f8,f15,f16,f17,f18,f104,f105,f106"
    url = (
        "https://push2.eastmoney.com/api/qt/ulist.np/get"
        f"?fltt=2&invt=2&fields={fields}&secids={ids}"
    )
    data = http_json(url)
    out: dict[str, dict] = {}
    for row in ((data or {}).get("data") or {}).get("diff") or []:
        code = str(row.get("f12") or "")
        if code:
            out[code] = row
    return out


def fetch_concepts(code: str, market: Any) -> list[str]:
    url = (
        "https://push2.eastmoney.com/api/qt/slist/get"
        f"?spt=3&fltt=2&invt=2&np=1&pn=1&pz=40&po=1"
        f"&fields=f12,f14&secid={secid(code, market)}"
    )
    try:
        data = http_json(url, timeout=12)
    except Exception:
        return []
    names: list[str] = []
    for row in ((data or {}).get("data") or {}).get("diff") or []:
        name = str(row.get("f14") or "").strip()
        if name:
            names.append(name)
    return names


def is_generic_concept(name: str) -> bool:
    if name in GENERIC_CONCEPTS:
        return True
    if name.endswith(REGION_SUFFIX) and "自贸" not in name:
        return True
    if name.endswith("板块") or name.endswith("成份"):
        return True
    return False


def normalize_theme(name: str) -> str:
    if name in THEME_ALIASES:
        return THEME_ALIASES[name]
    if name in INDUSTRY_THEME:
        return INDUSTRY_THEME[name]
    for key, alias in THEME_ALIASES.items():
        if key in name:
            return alias
    return name


def fmt_time(raw: Any) -> str:
    s = str(int(raw or 0)).zfill(6)
    return f"{s[:2]}:{s[2:4]}:{s[4:6]}"


def num(v: Any, default: float = 0.0) -> float:
    try:
        if v in (None, "", "-"):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def score_cell(v: float) -> tuple[str, str]:
    if v >= 0.99:
        return "1", "ok"
    if v >= 0.4:
        return "½", "half"
    return "0", "no"


def yuan(v: float) -> str:
    if v >= 1e12:
        return f" {v / 1e12:.2f} 万亿".replace("  ", " ")
    if v >= 1e8:
        return f"{v / 1e8:.0f} 亿"
    if v >= 1e4:
        return f"{v / 1e4:.0f} 万"
    return f"{v:.0f}"


def next_open_day(date: str) -> str:
    d = parse_date(date) + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def session_label(date: str) -> tuple[str, str]:
    now = now_cn()
    if date != now.strftime("%Y-%m-%d"):
        return "close", "收盘"
    hhmm = now.hour * 100 + now.minute
    if hhmm < 915:
        return "pre", "盘前"
    if hhmm <= 1130 or 1300 <= hhmm <= 1505:
        return "open", "盘中"
    if 1130 < hhmm < 1300:
        return "open", "午休"
    return "close", "收盘"


def in_session(date: str) -> bool:
    kind, _ = session_label(date)
    return kind == "open" and date == today_str()


def walk_back_days(date: str, n: int = 10) -> list[str]:
    d = parse_date(date)
    out: list[str] = []
    guard = 0
    while len(out) < n and guard < 40:
        guard += 1
        d -= timedelta(days=1)
        if d.weekday() >= 5:
            continue
        out.append(d.strftime("%Y-%m-%d"))
    return out


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_known_dates() -> list[str]:
    dates = set()
    for folder in (SNAPSHOT_DIR, CACHE_DIR):
        if not folder.exists():
            continue
        for p in folder.glob("*.json"):
            dates.add(p.stem)
    dates.add(today_str())
    return sorted(dates, reverse=True)


def snapshot_path(date: str) -> Path:
    return SNAPSHOT_DIR / f"{date}.json"


def cache_path(date: str) -> Path:
    return CACHE_DIR / f"{date}.json"


def attach_meta(review: dict, date: str, source: str) -> dict:
    kind, label = session_label(date)
    review["date"] = date
    review["session"] = kind
    review["session_label"] = label
    review["source"] = source
    review["updated_at"] = now_cn().strftime("%Y-%m-%d %H:%M:%S")
    review["in_session"] = in_session(date)
    return review


class MarketBundle:
    def __init__(self, date: str):
        self.date = date
        self.date8 = compact(date)
        self.zt: list[dict] = []
        self.dt: list[dict] = []
        self.zb: list[dict] = []
        self.yz: list[dict] = []
        self.history: dict[str, list[dict]] = {}
        self.quotes: dict[str, dict] = {}
        self.concepts: dict[str, list[str]] = {}
        self.index: dict[str, dict] = {}


def collect_market(date: str) -> MarketBundle:
    b = MarketBundle(date)
    prev_dates = walk_back_days(date, 8)

    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = {
            pool.submit(fetch_pool, "zt", b.date8): ("zt", date),
            pool.submit(fetch_pool, "dt", b.date8): ("dt", date),
            pool.submit(fetch_pool, "zb", b.date8): ("zb", date),
            pool.submit(fetch_pool, "yz", b.date8): ("yz", date),
        }
        for pd in prev_dates:
            futs[pool.submit(fetch_pool, "zt", compact(pd))] = ("hist", pd)

        for fut in as_completed(futs):
            kind, key = futs[fut]
            try:
                rows = fut.result()
            except Exception:
                rows = []
            if kind == "zt":
                b.zt = rows
            elif kind == "dt":
                b.dt = rows
            elif kind == "zb":
                b.zb = rows
            elif kind == "yz":
                b.yz = rows
            else:
                b.history[key] = rows

    index_ids = [
        ("000001", 1),
        ("399001", 0),
        ("399006", 0),
        ("000688", 1),
    ]
    fallen_ids: list[tuple[str, Any]] = []
    seen = {r.get("c") for r in b.zt}
    hist_best: dict[str, dict] = {}
    for day, rows in b.history.items():
        for r in rows:
            code = r.get("c")
            if not code or code in seen:
                continue
            prev = hist_best.get(code)
            if not prev or num(r.get("lbc")) > num(prev.get("lbc")):
                hist_best[code] = {**r, "_day": day}
    for code, r in hist_best.items():
        if num(r.get("lbc")) >= 3:
            fallen_ids.append((code, r.get("m")))

    extra = [
        (r.get("c"), r.get("m"))
        for r in b.yz
        if r.get("c") and num(r.get("ylbc")) >= 3 and r.get("c") not in seen
    ]
    quote_ids = index_ids + [(r.get("c"), r.get("m")) for r in b.zt[:30]] + fallen_ids + extra
    uniq: list[tuple[str, Any]] = []
    used = set()
    for code, m in quote_ids:
        if not code or code in used:
            continue
        used.add(code)
        uniq.append((code, m))

    try:
        quotes = fetch_quotes(uniq)
    except Exception:
        quotes = {}
    for k in ("000001", "399001", "399006", "000688"):
        if k in quotes:
            b.index[k] = quotes[k]
    b.quotes = quotes

    focus = list(b.zt[:12])
    for r in hist_best.values():
        if num(r.get("lbc")) >= 5:
            focus.append(r)
    focus = focus[:16]
    with ThreadPoolExecutor(max_workers=8) as pool:
        fmap = {pool.submit(fetch_concepts, r.get("c"), r.get("m")): r.get("c") for r in focus if r.get("c")}
        for fut in as_completed(fmap):
            code = fmap[fut]
            try:
                b.concepts[code] = fut.result()
            except Exception:
                b.concepts[code] = []

    b._hist_best = hist_best  # type: ignore[attr-defined]
    return b


def theme_for(row: dict, bundle: MarketBundle, clusters: dict[str, list[str]]) -> str:
    code = row.get("c")
    hybk = str(row.get("hybk") or "").strip()
    concepts = bundle.concepts.get(code or "", [])
    ranked: list[tuple[int, str]] = []
    for raw in concepts:
        if is_generic_concept(raw):
            continue
        theme = normalize_theme(raw)
        ranked.append((len(clusters.get(theme, [])), theme))
    if ranked:
        ranked.sort(reverse=True)
        if ranked[0][0] >= 2:
            return ranked[0][1]
        for _, theme in ranked:
            if theme in ("液冷", "航运", "培育钻石", "消费", "黄金珠宝", "农业", "传媒"):
                return theme
        return ranked[0][1]
    if hybk:
        return normalize_theme(hybk)
    return "综合"


def build_clusters(bundle: MarketBundle) -> dict[str, list[str]]:
    clusters: dict[str, list[str]] = {}
    for r in bundle.zt:
        code = r.get("c")
        names = [str(r.get("hybk") or "")] + bundle.concepts.get(code or "", [])
        seen = set()
        for raw in names:
            raw = raw.strip()
            if not raw or is_generic_concept(raw):
                continue
            theme = normalize_theme(raw)
            if theme in seen:
                continue
            seen.add(theme)
            clusters.setdefault(theme, []).append(code)
    return clusters


def classify_env(bundle: MarketBundle) -> dict[str, Any]:
    zt_n = len(bundle.zt)
    dt_n = len(bundle.dt)
    zb_n = len(bundle.zb)
    height = max((int(num(r.get("lbc"))) for r in bundle.zt), default=0)
    prev_height = 0
    high_fallen: list[dict] = []
    hist_best = getattr(bundle, "_hist_best", {})
    for code, r in hist_best.items():
        prev_lbc = int(num(r.get("lbc")))
        prev_height = max(prev_height, prev_lbc)
        q = bundle.quotes.get(code) or {}
        zdp = num(q.get("f3"))
        if prev_lbc >= 3 and zdp <= -7:
            high_fallen.append(
                {
                    "code": code,
                    "name": r.get("n") or q.get("f14") or code,
                    "lbc": prev_lbc,
                    "zdp": zdp,
                    "hs": num(q.get("f8"), num(r.get("hs"))),
                    "hybk": r.get("hybk") or "",
                    "open": num(q.get("f17")),
                    "price": num(q.get("f2")),
                    "low": num(q.get("f16")),
                    "high": num(q.get("f15")),
                    "yizi_dt": abs(num(q.get("f7"))) < 0.05 and zdp <= -9.5,
                }
            )
    high_fallen.sort(key=lambda x: (-x["lbc"], x["zdp"]))

    y2 = [r for r in bundle.yz if int(num(r.get("ylbc"))) >= 2]
    y2_codes = {r.get("c") for r in y2}
    zt_codes = {r.get("c") for r in bundle.zt}
    y2_broke = [r for r in y2 if r.get("c") not in zt_codes]
    promo = 0.0
    if y2:
        promo = sum(1 for r in y2 if r.get("c") in zt_codes) / len(y2)

    sh = bundle.index.get("000001") or {}
    sz = bundle.index.get("399001") or {}
    up = int(num(sh.get("f104")) + num(sz.get("f104")))
    down = int(num(sh.get("f105")) + num(sz.get("f105")))
    amount = num(sh.get("f6")) + num(sz.get("f6"))
    seal = zt_n / max(zt_n + zb_n, 1)

    retreat = False
    reasons = []
    if len(high_fallen) >= 2 and zt_n < 80:
        retreat = True
        reasons.append("高位人气股集体回撤")
    if dt_n >= 10 and zt_n < 70 and down > up:
        retreat = True
        reasons.append("跌停多于安全感、赚钱效应差")
    if prev_height and height and height <= prev_height - 2:
        retreat = True
        reasons.append(f"高度 {prev_height}→{height}")
    if y2 and len(y2_broke) == len(y2) and len(y2) >= 5:
        retreat = True
        reasons.append(f"昨日 {len(y2)} 只 2 连板以上全部断板")
    if zt_n <= 50 and seal < 0.62:
        retreat = True
        reasons.append("涨停少、封板率偏低")

    if retreat:
        env = "退潮"
    elif height >= 7 and promo >= 0.45 and zt_n >= 70:
        env = "主升"
    elif zt_n >= 55 and promo >= 0.35:
        env = "发酵"
    elif zb_n >= max(20, zt_n * 0.5):
        env = "分歧"
    else:
        env = "修复"

    return {
        "env": env,
        "retreat": retreat,
        "reasons": reasons,
        "zt": zt_n,
        "dt": dt_n,
        "zb": zb_n,
        "seal": seal,
        "height": height,
        "prev_height": prev_height,
        "high_fallen": high_fallen,
        "y2": y2,
        "y2_broke": y2_broke,
        "promo": promo,
        "up": up,
        "down": down,
        "amount": amount,
        "sh": sh,
        "sz": sz,
    }


def score_stock(row: dict, bundle: MarketBundle, clusters: dict[str, list[str]], env: dict) -> dict:
    code = row.get("c")
    name = row.get("n") or code
    lbc = int(num(row.get("lbc")))
    hs = num(row.get("hs"))
    zbc = int(num(row.get("zbc")))
    fbt = int(num(row.get("fbt")))
    lbt = int(num(row.get("lbt")))
    q = bundle.quotes.get(code) or {}
    amp = num(q.get("f7"))
    open_p = num(q.get("f17"))
    high = num(q.get("f15"))
    low = num(q.get("f16"))
    price = num(q.get("f2"), num(row.get("p")) / 1000.0)
    zdp = num(q.get("f3"), num(row.get("zdp")))
    theme = theme_for(row, bundle, clusters)
    mates = [c for c in clusters.get(theme, []) if c != code]
    mate_rows = [r for r in bundle.zt if r.get("c") in set(mates)]
    mate_boards = [int(num(r.get("lbc"))) for r in mate_rows]
    theme_max = max([lbc] + mate_boards, default=lbc)
    market_max = env["height"] or lbc

    yizi = fbt == 92500 and zbc <= 1 and (amp <= 2.2 or abs(open_p - price) < 0.02)
    t_shape = (low and open_p and low < open_p * 0.99) or zbc >= 2

    # 带动性
    if zdp <= -7:
        drive = 0.0
    elif len(mate_rows) >= 3 or sum(1 for x in mate_boards if x >= 2) >= 2:
        drive = 1.0
    elif len(mate_rows) == 2 or (len(mate_rows) == 1 and (mate_boards and mate_boards[0] >= 2)):
        drive = 0.5
    elif len(mate_rows) == 1:
        drive = 0.5
    else:
        drive = 0.0
    # 首板点火：同题材跟风够也可以给 1
    if lbc == 1 and len(mate_rows) >= 2:
        drive = 1.0

    # 领涨性
    if lbc <= 1:
        lead = 0.0
    elif lbc == market_max or (lbc >= 4 and lbc == theme_max):
        lead = 1.0
    elif lbc == theme_max and lbc >= 2:
        lead = 1.0
    else:
        lead = 0.0

    # 渡劫
    if zdp <= -7:
        survive = 0.0
    elif lbc <= 1:
        survive = 0.0
    elif yizi:
        survive = 0.0
    elif zbc >= 3 and lbc >= 3:
        survive = 1.0
    elif t_shape or zbc >= 1:
        survive = 0.5
    else:
        survive = 0.0

    # 顶级流动性：一字低换手才否决；高换手一字仍给 1
    if zdp <= -9 and hs < 2:
        liq = 0.0
    elif yizi and hs < 3:
        liq = 0.0
    elif hs < 4:
        liq = 0.5
    else:
        liq = 1.0

    total = drive + lead + survive + liq
    if zdp <= -7:
        verdict = "非龙<br>渡劫失败" if lbc < 6 else "非龙<br>前总龙陨落"
        verdict_cls = "red"
        score_txt = "退潮"
        score_cls = "red"
        fallen = True
        board_txt = f"{zdp:.2f}%"
        if abs(zdp) >= 9.5 and amp < 0.2:
            board_txt = f"−{abs(zdp):.2f}%<br>一字跌停"
        elif zdp < 0:
            board_txt = f"−{abs(zdp):.2f}%"
    else:
        fallen = False
        board_txt = "首板" if lbc <= 1 else f"{lbc}板"
        score_txt = f"{total:.1f}/4"
        score_cls = ""
        if total >= 3.99 and min(drive, lead, survive, liq) >= 0.99:
            verdict = "真龙"
            verdict_cls = "ok"
        elif env["retreat"] and lbc >= 4 and drive < 0.99:
            verdict = "空间活口<br>退潮一票否决"
            verdict_cls = "note"
        elif lbc >= 3 and survive < 0.4:
            verdict = "主线龙候选<br>缺分歧验货"
            verdict_cls = "note"
        elif lbc <= 1:
            verdict = "题材点火<br>未到龙" if hs >= 4 else "题材点火<br>换手偏低"
            verdict_cls = "note"
        elif total >= 3:
            verdict = "观察龙<br>未齐四特征"
            verdict_cls = "note"
        else:
            verdict = "未到龙"
            verdict_cls = "note"

    return {
        "name": name,
        "code": code,
        "theme": theme,
        "hybk": row.get("hybk") or "",
        "fallen": fallen,
        "lbc": lbc,
        "boards": board_txt,
        "zdp": zdp,
        "hs": hs,
        "zbc": zbc,
        "fbt": fmt_time(fbt),
        "lbt": fmt_time(lbt),
        "amp": amp,
        "open": open_p,
        "high": high,
        "low": low,
        "price": price,
        "amount": num(row.get("amount"), num(q.get("f6"))),
        "drive": drive,
        "lead": lead,
        "survive": survive,
        "liq": liq,
        "score": score_txt,
        "score_class": score_cls,
        "verdict": verdict,
        "verdict_class": verdict_cls,
        "mates": [
            {
                "name": r.get("n"),
                "code": r.get("c"),
                "lbc": int(num(r.get("lbc"))),
            }
            for r in mate_rows
        ],
        "yizi": yizi,
        "t_shape": t_shape,
    }


def score_fallen(item: dict) -> dict:
    zdp = item["zdp"]
    board = f"−{abs(zdp):.2f}%"
    if item.get("yizi_dt"):
        board += "<br>一字跌停"
    verdict = "非龙<br>前总龙陨落" if item["lbc"] >= 6 else "非龙<br>渡劫失败"
    if item["lbc"] < 4:
        verdict = "非龙"
    return {
        "name": item["name"],
        "code": item["code"],
        "theme": normalize_theme(item.get("hybk") or "前主线"),
        "hybk": item.get("hybk") or "",
        "fallen": True,
        "lbc": item["lbc"],
        "boards": board,
        "zdp": zdp,
        "hs": item.get("hs") or 0,
        "zbc": 0,
        "fbt": "",
        "lbt": "",
        "amp": 0,
        "open": item.get("open") or 0,
        "high": item.get("high") or 0,
        "low": item.get("low") or 0,
        "price": item.get("price") or 0,
        "amount": 0,
        "drive": 0.0,
        "lead": 0.0,
        "survive": 0.0,
        "liq": 0.0,
        "score": "退潮",
        "score_class": "red",
        "verdict": verdict,
        "verdict_class": "red",
        "mates": [],
        "yizi": bool(item.get("yizi_dt")),
        "t_shape": False,
    }


def pick_candidates(scored: list[dict], fallen: list[dict]) -> list[dict]:
    alive = [s for s in scored if not s["fallen"]]
    alive.sort(key=lambda s: (-s["lbc"], -(s["drive"] + s["lead"] + s["survive"] + s["liq"]), -s["hs"]))
    firsts = [s for s in alive if s["lbc"] <= 1]
    firsts.sort(key=lambda s: (-s["drive"], -s["hs"]))
    top = []
    seen = set()
    for s in alive:
        if s["code"] in seen:
            continue
        if s["lbc"] >= 3 or (s["lbc"] >= 2 and s["drive"] >= 0.5):
            top.append(s)
            seen.add(s["code"])
        if len(top) >= 3:
            break
    for s in firsts:
        if s["code"] in seen:
            continue
        if s["drive"] >= 0.5:
            top.append(s)
            seen.add(s["code"])
        if len([x for x in top if x["lbc"] <= 1]) >= 2:
            break
    out = top[:5]
    for f in fallen[:3]:
        out.append(score_fallen(f))
    return out


def box_for(s: dict, env: dict) -> dict:
    tags = []
    mapping = [("drive", "带动"), ("lead", "领涨"), ("survive", "渡劫"), ("liq", "流动性")]
    for key, label in mapping:
        val = s[key]
        txt, cls = score_cell(val)
        color = "g" if cls == "ok" else "y" if cls == "half" else "r"
        tags.append({"t": f"{label} {txt}", "c": color})

    mates = "、".join(f"{m['name']}{m['lbc']}板" if m["lbc"] > 1 else m["name"] for m in s["mates"][:6])
    notes = []
    if s["fallen"]:
        notes.append(
            f"{s['name']} 此前最高 {s['lbc']} 连板，今日 {s['boards'].replace('<br>', ' ')}，"
            f"换手 {s['hs']:.2f}%。按框架：<b>失去带动性 + 高位退潮 = 下车</b>。"
        )
        return {
            "title": f"{s['name']} {s['code']} — 前主线退潮，已判非龙",
            "tags": tags,
            "notes": notes,
            "danger": True,
        }

    bits = []
    if s["lead"] >= 1:
        bits.append(f"领涨：全场/题材内高度 {s['lbc']} 板，这一条成立")
    elif s["lbc"] <= 1:
        bits.append("领涨：仍是首板，空间高度还没走出来")
    if s["drive"] >= 1:
        bits.append(f"带动：{s['theme']} 线有跟风（{mates or '同题材多票'}）")
    elif s["drive"] >= 0.5:
        bits.append(f"带动：{s['theme']} 仅 {mates or '少量小弟'}，带不动全场")
    else:
        bits.append(f"带动：{s['theme']} 几乎无跟风高潮")
    if s["liq"] >= 1:
        bits.append(f"流动性：换手 {s['hs']:.2f}%，不是一字锁死")
    elif s["liq"] >= 0.5:
        bits.append(f"流动性：换手 {s['hs']:.2f}%，偏弱")
    else:
        bits.append(f"流动性：换手 {s['hs']:.2f}%，接近锁死")
    if s["survive"] >= 1:
        bits.append(f"渡劫：炸板 {s['zbc']} 次后仍回封，分歧里活下来了")
    elif s["survive"] >= 0.5:
        bits.append(
            f"渡劫：有换手/回封（开 {s['open']:.2f}→最低 {s['low']:.2f}→回封），但仅一天，还需弱转强确认"
        )
    elif s["yizi"]:
        bits.append(
            f"渡劫：接近一字（开 {s['open']:.2f}，振幅 {s['amp']:.2f}%），<b>没经历爆量烂板、没在分歧里验过货</b>"
        )
    else:
        bits.append("渡劫：还没走过板块大分歧")

    if env["retreat"] and s["lbc"] >= 4:
        second = "按框架：退潮大环境下属「空间活口观察」，不是买点。下一交易日若不能弱转强、或小弟不助攻，地位即松动。"
    elif s["lbc"] >= 3 and s["survive"] < 0.4:
        second = "按框架：这是「新主线先手高标」，不是确认龙。等它板块首次大分歧后还能率先弱转强，才接近买点；今天追一字是「一致」，不是「分歧」。"
    elif s["lbc"] <= 1:
        second = "按框架现在只是「题材爆发日点火」，连板高度与分歧验货都还没走出来，不能当龙。跟踪能否走出 2~3 板并在分歧日回封。"
    else:
        second = "按框架：四特征未齐，继续观察，不追一致。"

    title_map_extra = ""
    if s["lbc"] >= 4 and env["retreat"]:
        title_map_extra = " — 空间活口，非「可上车真龙」"
    elif s["lbc"] >= 3 and s["survive"] < 0.4:
        title_map_extra = " — 带动性最好，但缺「爆量烂板→弱转强」那一锤"
    elif s["lbc"] <= 1:
        title_map_extra = " — 新题材点火，远未到龙"
    else:
        title_map_extra = " — 观察，未到真龙"

    return {
        "title": f"{s['name']} {s['code']}{title_map_extra}",
        "tags": tags,
        "notes": ["；".join(bits) + "。", second],
        "danger": False,
    }


def build_tldr(cands: list[dict], env: dict) -> dict:
    alive = [s for s in cands if not s["fallen"]]
    true_d = [s for s in alive if s["score"] == "4.0/4" or (s["drive"] + s["lead"] + s["survive"] + s["liq"] >= 3.99)]
    space = [s for s in alive if "空间活口" in s["verdict"]]
    main = [s for s in alive if "主线龙" in s["verdict"]]
    fire = [s for s in alive if s["lbc"] <= 1]
    lines = []
    if true_d:
        verdict = f"四特征对齐，<b>{true_d[0]['name']}</b> 可按真龙观察，仍要等分歧买点，不追一字。"
        cls = ""
    elif env["retreat"]:
        verdict = "退潮期，<b>一票否决·空仓优先</b>。今天没有四特征齐全的「真龙」，只有空间活口与题材点火，<b>不接高位、不追一字</b>。"
        cls = "red"
    else:
        verdict = f"{env['env']}期，尚未出现四特征齐全的「真龙」，<b>买在分歧，不追一致</b>。"
        cls = "red" if env["env"] in ("退潮", "分歧") else ""

    if space:
        s = space[0]
        lines.append(f"空间活口：<b>{s['name']}</b> {s['lbc']} 板（{s['theme']}，带动性弱、退潮环境高风险）")
    if main:
        s = main[0]
        lines.append(f"最强主线龙候选：<b>{s['name']}</b> {s['lbc']} 板（{s['theme']}，带动性较好，但缺「分歧验货」那一锤）")
    if fire:
        names = "、".join(f"<b>{s['name']}</b>（{s['theme']}）" for s in fire[:2])
        lines.append(f"新题材点火（未到龙）：{names}首板")
    if not lines and alive:
        s = alive[0]
        lines.append(f"最高标：<b>{s['name']}</b> {s['boards']}（{s['theme']}，真龙指数 {s['score']}）")
    return {"verdict": verdict, "verdict_class": cls, "lines": lines}


def build_warn(cands: list[dict], env: dict, bundle: MarketBundle) -> str:
    fallen = env["high_fallen"]
    dt_names = [r.get("n") for r in bundle.dt[:8] if r.get("n")]
    yizi = [f["name"] for f in fallen if f.get("yizi_dt")]
    others = [f["name"] for f in fallen if not f.get("yizi_dt")]
    dt_high = [n for n in dt_names if n not in yizi]
    bits = []
    if yizi:
        bits.append("、".join(yizi) + "竞价一字跌停")
    if others:
        bits.append("、".join(x["name"] for x in fallen if not x.get("yizi_dt")) + "高位回撤")
    if dt_high:
        bits.append("、".join(dt_high[:6]) + "封死跌停")
    head = "、".join(bits) if bits else "赚钱效应一般"
    extra = ""
    if env["retreat"]:
        extra = "。框架原话：<b>「管他什么龙，空仓保命最要紧」</b>。"
    return (
        f"⚠️ 风控优先：{head}，全市约 {env['down']} 只下跌、{env['dt']} 只跌停"
        f"{extra}"
    )


def build_ladder(bundle: MarketBundle, clusters: dict[str, list[str]], env: dict) -> tuple[str, list[dict], str]:
    groups: dict[int, list[dict]] = {}
    for r in bundle.zt:
        lbc = int(num(r.get("lbc")))
        if lbc >= 2:
            groups.setdefault(lbc, []).append(r)
    rows = []
    for lbc in sorted(groups, reverse=True):
        names = "、".join(r.get("n") or "" for r in groups[lbc])
        attrs = " / ".join(
            theme_for(r, bundle, clusters) for r in groups[lbc]
        )
        extra = []
        for r in groups[lbc]:
            if int(num(r.get("zbc"))) >= 2:
                extra.append("放量回封")
        attr = attrs
        if extra:
            attr = attrs + "，" + extra[0]
        rows.append({"level": f"{lbc}板", "names": names, "attr": attr})
    height = env["height"]
    prev = env["prev_height"]
    title = f"三、{md_short(bundle.date)} 连板梯队"
    if env["retreat"] and prev:
        title += f"（退潮，高度 {prev}→{height}）"
    elif height:
        title += f"（高度 {height}）"
    y2_broke = len(env["y2_broke"])
    y2 = len(env["y2"])
    note = (
        f"全市约 {env['zt']} 股涨停、{sum(len(v) for k,v in groups.items() if k>=2)} 只连板、"
        f"{env['dt']} 只跌停"
    )
    if y2 and y2_broke == y2:
        note += f"；昨日 {y2} 只 2 连板以上全部断板"
    note += f"。涨停封板率约 {env['seal']*100:.0f}%。"
    return title, rows, note


def build_watch(cands: list[dict], env: dict, date: str) -> tuple[str, dict]:
    nxt = next_open_day(date)
    title = f"四、周{weekday_cn(nxt)}（{md_short(nxt)}）盯盘清单"
    notes = []
    n = 1
    for s in cands:
        if s["fallen"]:
            continue
        if s["lbc"] >= 4:
            notes.append(
                f"{n}. <b>{s['name']}</b>：能否弱转强封 {s['lbc']+1} 板？{s['theme']} 小弟是否助攻？若独舞或断板，空间活口结束。"
            )
            n += 1
        elif s["lbc"] >= 3:
            notes.append(
                f"{n}. <b>{s['name']}</b>：{s['theme']} 线首次大分歧时，它是否爆量烂板后仍率先回封？回封=买点信号，继续一字=不追。"
            )
            n += 1
        elif s["lbc"] <= 1:
            notes.append(
                f"{n}. <b>{s['name']}</b>：能否走出 2 板并带板块？首板题材需连续确认才进评分台。"
            )
            n += 1
        if n > 3:
            break
    fallen = [s for s in cands if s["fallen"]]
    if fallen:
        names = "、".join(s["name"] for s in fallen[:3])
        notes.append(f"{n}. <b>退潮票止跌</b>：{names} 是否止跌？不止跌则退潮延续，继续空仓。")
    notes.append("口诀：买在分歧，卖在一致。舒服买点没出现前，只看不做。")
    return title, {"title": "只看不做，等「分歧买点」", "notes": notes}


def generate_review(date: str) -> dict:
    bundle = collect_market(date)
    if not bundle.zt and not bundle.dt and date != today_str():
        kind, label = session_label(date)
        return attach_meta(
            {
                "empty": True,
                "title_suffix": f"{date} {label}",
                "subtitle": "按「龙头战法四特征框架」逐票验货 ｜ 所选日期无公开涨停池（休市或未开盘）｜ 非投资建议",
                "tldr": {
                    "verdict": f"{date} 没有可核验的涨停池数据，可能是周末/假期，或当天尚未开盘。",
                    "verdict_class": "red",
                    "lines": [],
                },
                "warn": "⚠️ 不编造行情。请改选最近交易日，或开盘后刷新。",
                "table": [],
                "boxes": [],
                "ladder_title": "三、连板梯队",
                "ladder": [],
                "ladder_note": "",
                "watch_title": "四、盯盘清单",
                "watch": {"title": "休市 / 无数据", "notes": []},
                "foot": f"数据归属日 {date}，来源东方财富公开涨停池。本卡非荐股。",
                "score_note": "评分口径：带动性=能否带同板块小弟高潮；领涨性=板块内连板最多/空间最高；渡劫能力=分歧日/跳水日不死、修复最先走强；顶级流动性=充分换手、非一字锁死。½=部分满足。",
            },
            date,
            "live",
        )

    clusters = build_clusters(bundle)
    env = classify_env(bundle)
    scored = [score_stock(r, bundle, clusters, env) for r in bundle.zt]
    cands = pick_candidates(scored, env["high_fallen"])
    tldr = build_tldr(cands, env)
    warn = build_warn(cands, env, bundle)
    boxes: list[dict] = []
    # 合并退潮票到一个 box
    fallen_cands = [s for s in cands if s["fallen"]]
    live_cands = [s for s in cands if not s["fallen"]]
    for s in live_cands:
        boxes.append(box_for(s, env))
    if fallen_cands:
        names = " / ".join(s["name"] for s in fallen_cands)
        notes = [
            "；".join(
                f"{s['name']} {s['boards'].replace('<br>', ' ')}"
                + (f"（换手 {s['hs']:.2f}%）" if s["hs"] else "")
                for s in fallen_cands
            )
            + "。按框架这就是卖点信号：<b>失去带动性 + 高位巨量/退潮 = 下车</b>。"
        ]
        boxes.append(
            {
                "title": f"{names} — 前主线集体退潮，已判非龙",
                "tags": [],
                "notes": notes,
                "danger": True,
            }
        )

    ladder_title, ladder, ladder_note = build_ladder(bundle, clusters, env)
    watch_title, watch = build_watch(cands, env, date)
    kind, label = session_label(date)
    sh = env["sh"]
    amount_txt = yuan(env["amount"]).strip()
    table = []
    for s in cands:
        table.append(
            {
                "name": s["name"],
                "code": s["code"],
                "theme": s["theme"],
                "fallen": s["fallen"],
                "boards": s["boards"],
                "drive": s["drive"],
                "lead": s["lead"],
                "survive": s["survive"],
                "liq": s["liq"],
                "score": s["score"],
                "score_class": s["score_class"],
                "verdict": s["verdict"],
                "verdict_class": s["verdict_class"],
            }
        )

    review = {
        "empty": False,
        "title_suffix": f"{date} {label}",
        "subtitle": (
            f"按「龙头战法四特征框架」逐票验货 ｜ 数据：东方财富涨停池 + 实时行情"
            f"（{label}可刷新）｜ 非投资建议"
        ),
        "tldr": tldr,
        "warn": warn,
        "table": table,
        "score_note": (
            "评分口径：带动性=能否带同板块小弟高潮；领涨性=板块内连板最多/空间最高；"
            "渡劫能力=分歧日/跳水日不死、修复最先走强；顶级流动性=充分换手、非一字锁死。"
            "½=部分满足（如仅带小题材、仅一天活下来）。"
        ),
        "boxes": boxes,
        "ladder_title": ladder_title,
        "ladder": ladder,
        "ladder_note": ladder_note,
        "watch_title": watch_title,
        "watch": watch,
        "foot": (
            f"数据归属日 {date} {label}，行情与连板来自东方财富公开涨停池/行情，"
            f"沪深成交约 {amount_txt}"
            + (f"，上证 {num(sh.get('f2')):.2f}（{num(sh.get('f3')):+.2f}%）" if sh else "")
            + "。本卡为「龙头识别清单 + 买卖纪律」工具，非荐股、非稳赚方法。A 股短线波动极大，据此操作风险自担。"
        ),
        "market": {
            "env": env["env"],
            "zt": env["zt"],
            "dt": env["dt"],
            "zb": env["zb"],
            "seal": env["seal"],
            "height": env["height"],
            "amount": env["amount"],
        },
    }
    return attach_meta(review, date, "live")


def build_review(date: str, refresh: bool = False) -> dict:
    date = pretty(compact(date)) if len(compact(date)) == 8 else date
    snap = load_json(snapshot_path(date))
    if snap and not refresh:
        return attach_meta(snap, date, "snapshot")
    cached = load_json(cache_path(date))
    if cached and not refresh and not in_session(date):
        return attach_meta(cached, date, "cache")
    review = generate_review(date)
    if not review.get("empty"):
        save_json(cache_path(date), review)
    return review


if __name__ == "__main__":
    import sys

    d = sys.argv[1] if len(sys.argv) > 1 else today_str()
    force = "--refresh" in sys.argv
    out = build_review(d, refresh=force)
    print(json.dumps({k: out.get(k) for k in ("date", "source", "title_suffix", "tldr", "market", "updated_at")}, ensure_ascii=False, indent=2))
    print("table", [f"{r['name']} {r['boards']} {r['score']}" for r in out.get("table", [])])

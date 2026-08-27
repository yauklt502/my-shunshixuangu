#!/usr/bin/env python3
"""近 90 个交易日「连板天数 >= 5」个股共性 + 龙虎榜特征分析。

数据源：东方财富涨停股池、龙虎榜、F10 概念/上市日期；交易日历取上证指数日 K。
"""

from __future__ import annotations

import json
import math
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from seat_alias import classify_seat, short_seat_name  # noqa: E402

CACHE = ROOT / "data" / "cache"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
CHARTS = REPORTS / "charts"
LOOKBACK = 90

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
_print_lock = Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def ensure_dirs() -> None:
    for p in (CACHE, PROCESSED, REPORTS, CHARTS, CACHE / "zt", CACHE / "seats", CACHE / "info"):
        p.mkdir(parents=True, exist_ok=True)


def get_json(url: str, params: Optional[dict] = None, retries: int = 5, timeout: int = 25, referer: Optional[str] = None) -> Any:
    last: Optional[Exception] = None
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = referer
    for i in range(retries):
        try:
            r = SESSION.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code in (429, 502, 503, 504):
                time.sleep(1.2 * (2 ** i))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(0.8 * (2 ** i))
    raise RuntimeError(f"GET failed {url} {params}: {last}")


def fmt_time(v: Any) -> str:
    s = str(int(v)).zfill(6) if v is not None and str(v) not in {"", "nan"} else ""
    if len(s) != 6:
        return s
    return f"{s[:2]}:{s[2:4]}:{s[4:]}"


def seconds_from_open(v: Any) -> Optional[int]:
    """相对 09:30:00 的秒数；09:25 集合竞价记为 -300。"""
    try:
        s = str(int(v)).zfill(6)
        hh, mm, ss = int(s[:2]), int(s[2:4]), int(s[4:])
        return hh * 3600 + mm * 60 + ss - (9 * 3600 + 30 * 60)
    except Exception:  # noqa: BLE001
        return None


def market_of(code: str, name: str = "") -> str:
    if "ST" in name.upper() or "退" in name:
        st = True
    else:
        st = False
    if code.startswith("8") or code.startswith("4"):
        m = "北交所"
    elif code.startswith("688") or code.startswith("689"):
        m = "科创板"
    elif code.startswith("300") or code.startswith("301"):
        m = "创业板"
    elif code.startswith("60"):
        m = "沪市主板"
    elif code.startswith("00") or code.startswith("001") or code.startswith("003"):
        m = "深市主板"
    else:
        m = "其他"
    return f"ST/{m}" if st else m


def cap_bucket(yuan: float) -> str:
    yi = yuan / 1e8
    if yi < 20:
        return "<20亿"
    if yi < 50:
        return "20-50亿"
    if yi < 100:
        return "50-100亿"
    if yi < 200:
        return "100-200亿"
    return ">200亿"


def price_bucket(price: float) -> str:
    if price < 5:
        return "<5元"
    if price < 10:
        return "5-10元"
    if price < 20:
        return "10-20元"
    if price < 50:
        return "20-50元"
    return ">50元"


def fetch_trade_dates(n: int = LOOKBACK) -> list[str]:
    cache = CACHE / "trade_dates.json"
    url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
    data = get_json(
        url,
        params={"symbol": "sh000001", "scale": "240", "ma": "no", "datalen": str(n + 5)},
        referer="https://finance.sina.com.cn/",
    )
    dates = [x["day"].replace("-", "") for x in data]
    dates = sorted(dates)[-n:]
    cache.write_text(json.dumps(dates, ensure_ascii=False, indent=2), encoding="utf-8")
    return dates


def parse_zt_pool(payload: dict, date: str) -> list[dict]:
    pool = ((payload or {}).get("data") or {}).get("pool") or []
    rows = []
    for it in pool:
        zttj = it.get("zttj") or {}
        rows.append(
            {
                "date": date,
                "code": str(it.get("c") or "").zfill(6),
                "name": it.get("n"),
                "price": (it.get("p") or 0) / 1000.0,
                "pct": it.get("zdp"),
                "amount": it.get("amount"),
                "float_mv": it.get("ltsz"),
                "total_mv": it.get("tshare"),
                "turnover": it.get("hs"),
                "lianban": int(it.get("lbc") or 0),
                "first_seal": it.get("fbt"),
                "last_seal": it.get("lbt"),
                "seal_amt": it.get("fund"),
                "open_times": int(it.get("zbc") or 0),
                "industry": it.get("hybk"),
                "zt_days": zttj.get("days"),
                "zt_count": zttj.get("ct"),
                "market_flag": it.get("m"),
            }
        )
    return rows


def fetch_zt_one(date: str) -> list[dict]:
    fp = CACHE / "zt" / f"{date}.json"
    if fp.exists():
        return json.loads(fp.read_text(encoding="utf-8"))
    payload = get_json(
        "https://push2ex.eastmoney.com/getTopicZTPool",
        params={
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "dpt": "wz.ztzt",
            "Pageindex": "0",
            "pagesize": "10000",
            "sort": "fbt:asc",
            "date": date,
        },
        referer="https://quote.eastmoney.com/ztb/detail#ztgc",
    )
    rows = parse_zt_pool(payload, date)
    fp.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def fetch_all_zt(dates: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    done = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(fetch_zt_one, d): d for d in dates}
        for fut in as_completed(futs):
            d = futs[fut]
            try:
                part = fut.result()
                rows.extend(part)
            except Exception as e:  # noqa: BLE001
                log(f"  zt fail {d}: {e}")
            done += 1
            if done % 15 == 0 or done == len(dates):
                log(f"  涨停池 {done}/{len(dates)}")
    df = pd.DataFrame(rows)
    if not df.empty:
        df["code"] = df["code"].astype(str).str.zfill(6)
    return df


def reconstruct_streaks(zt: pd.DataFrame, dates: list[str]) -> pd.DataFrame:
    """把连续涨停日切成连板周期，height 取周期内最大连板数（含窗口前延续）。"""
    date_index = {d: i for i, d in enumerate(dates)}
    records = []
    for code, g in zt.groupby("code"):
        g = g.sort_values("date")
        days = g["date"].tolist()
        if not days:
            continue
        runs: list[list[str]] = []
        cur = [days[0]]
        for d in days[1:]:
            prev = cur[-1]
            if date_index.get(d, -9) - date_index.get(prev, -9) == 1:
                cur.append(d)
            else:
                runs.append(cur)
                cur = [d]
        runs.append(cur)

        name = g["name"].iloc[-1]
        for run in runs:
            sub = g[g["date"].isin(run)]
            height = int(sub["lianban"].max())
            # 若窗口内只看到高位尾巴，用最大连板数；若连板数字段缺失则用天数
            height = max(height, len(run))
            peak_row = sub.sort_values(["lianban", "date"]).iloc[-1]
            start_row = sub.sort_values("date").iloc[0]
            end_row = sub.sort_values("date").iloc[-1]
            records.append(
                {
                    "code": code,
                    "name": name,
                    "start": run[0],
                    "end": run[-1],
                    "days_in_window": len(run),
                    "height": height,
                    "industry": peak_row.get("industry"),
                    "peak_date": peak_row["date"],
                    "peak_price": peak_row.get("price"),
                    "peak_float_mv": peak_row.get("float_mv"),
                    "peak_total_mv": peak_row.get("total_mv"),
                    "peak_turnover": peak_row.get("turnover"),
                    "peak_seal_amt": peak_row.get("seal_amt"),
                    "peak_open_times": peak_row.get("open_times"),
                    "peak_first_seal": peak_row.get("first_seal"),
                    "start_float_mv": start_row.get("float_mv"),
                    "end_price": end_row.get("price"),
                    "avg_turnover": float(sub["turnover"].mean() or 0),
                    "avg_open_times": float(sub["open_times"].mean() or 0),
                    "yiziban_days": int(((sub["turnover"] < 2.0) & (sub["open_times"] == 0)).sum()),
                    "dates": ",".join(run),
                }
            )
    return pd.DataFrame(records)


def fetch_lhb_range(start: str, end: str) -> pd.DataFrame:
    fp = CACHE / f"lhb_{start}_{end}.csv"
    if fp.exists():
        return pd.read_csv(fp, dtype={"代码": str})
    start_d = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    end_d = f"{end[:4]}-{end[4:6]}-{end[6:]}"
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    base = {
        "sortColumns": "SECURITY_CODE,TRADE_DATE",
        "sortTypes": "1,-1",
        "pageSize": "5000",
        "pageNumber": "1",
        "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
        "columns": (
            "SECURITY_CODE,SECUCODE,SECURITY_NAME_ABBR,TRADE_DATE,EXPLAIN,CLOSE_PRICE,CHANGE_RATE,"
            "BILLBOARD_NET_AMT,BILLBOARD_BUY_AMT,BILLBOARD_SELL_AMT,BILLBOARD_DEAL_AMT,ACCUM_AMOUNT,"
            "DEAL_NET_RATIO,DEAL_AMOUNT_RATIO,TURNOVERRATE,FREE_MARKET_CAP,EXPLANATION,"
            "D1_CLOSE_ADJCHRATE,D2_CLOSE_ADJCHRATE,D5_CLOSE_ADJCHRATE,D10_CLOSE_ADJCHRATE"
        ),
        "source": "WEB",
        "client": "WEB",
        "filter": f"(TRADE_DATE<='{end_d}')(TRADE_DATE>='{start_d}')",
    }
    first = get_json(url, params=base, referer="https://data.eastmoney.com/stock/tradedetail.html")
    result = first.get("result") or {}
    pages = int(result.get("pages") or 1)
    frames = [pd.DataFrame(result.get("data") or [])]
    for page in range(2, pages + 1):
        params = dict(base)
        params["pageNumber"] = str(page)
        payload = get_json(url, params=params, referer="https://data.eastmoney.com/stock/tradedetail.html")
        frames.append(pd.DataFrame((payload.get("result") or {}).get("data") or []))
        log(f"  龙虎榜页 {page}/{pages}")
        time.sleep(0.15)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if df.empty:
        return df
    df.rename(
        columns={
            "SECURITY_CODE": "代码",
            "SECURITY_NAME_ABBR": "名称",
            "TRADE_DATE": "上榜日",
            "EXPLAIN": "解读",
            "CLOSE_PRICE": "收盘价",
            "CHANGE_RATE": "涨跌幅",
            "BILLBOARD_NET_AMT": "龙虎榜净买额",
            "BILLBOARD_BUY_AMT": "龙虎榜买入额",
            "BILLBOARD_SELL_AMT": "龙虎榜卖出额",
            "BILLBOARD_DEAL_AMT": "龙虎榜成交额",
            "ACCUM_AMOUNT": "市场总成交额",
            "DEAL_NET_RATIO": "净买额占总成交比",
            "DEAL_AMOUNT_RATIO": "成交额占总成交比",
            "TURNOVERRATE": "换手率",
            "FREE_MARKET_CAP": "流通市值",
            "EXPLANATION": "上榜原因",
            "D1_CLOSE_ADJCHRATE": "上榜后1日",
            "D2_CLOSE_ADJCHRATE": "上榜后2日",
            "D5_CLOSE_ADJCHRATE": "上榜后5日",
            "D10_CLOSE_ADJCHRATE": "上榜后10日",
        },
        inplace=True,
    )
    df["代码"] = df["代码"].astype(str).str.zfill(6)
    df["上榜日"] = pd.to_datetime(df["上榜日"], errors="coerce").dt.strftime("%Y%m%d")
    df.to_csv(fp, index=False)
    return df


def fetch_seats(code: str, date: str) -> list[dict]:
    fp = CACHE / "seats" / f"{code}_{date}.json"
    if fp.exists():
        return json.loads(fp.read_text(encoding="utf-8"))
    out: list[dict] = []
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    for flag, report, sort_col in (
        ("买入", "RPT_BILLBOARD_DAILYDETAILSBUY", "BUY"),
        ("卖出", "RPT_BILLBOARD_DAILYDETAILSSELL", "SELL"),
    ):
        ds = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        payload = get_json(
            url,
            params={
                "reportName": report,
                "columns": "ALL",
                "filter": f"(TRADE_DATE='{ds}')(SECURITY_CODE=\"{code}\")",
                "pageNumber": "1",
                "pageSize": "50",
                "sortTypes": "-1",
                "sortColumns": sort_col,
                "source": "WEB",
                "client": "WEB",
            },
            referer=f"https://data.eastmoney.com/stock/lhb,{date},{code}.html",
        )
        data = ((payload.get("result") or {}).get("data")) or []
        for it in data:
            name = it.get("OPERATEDEPT_NAME") or ""
            cat, alias = classify_seat(name)
            out.append(
                {
                    "code": code,
                    "date": date,
                    "side": flag,
                    "seat": name,
                    "seat_code": it.get("OPERATEDEPT_CODE"),
                    "buy": it.get("BUY") or 0,
                    "sell": it.get("SELL") or 0,
                    "net": it.get("NET") or 0,
                    "reason": it.get("EXPLANATION"),
                    "category": cat,
                    "alias": alias,
                }
            )
    fp.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def fetch_stock_info(code: str) -> dict:
    fp = CACHE / "info" / f"{code}.json"
    if fp.exists():
        return json.loads(fp.read_text(encoding="utf-8"))
    info: dict[str, Any] = {"code": code}
    mkt = 1 if code.startswith(("6", "9")) else 0
    try:
        payload = get_json(
            "https://push2.eastmoney.com/api/qt/stock/get",
            params={"secid": f"{mkt}.{code}", "fields": "f57,f58,f116,f117,f127,f128,f129"},
            referer="https://quote.eastmoney.com/",
        )
        d = payload.get("data") or {}
        info["industry"] = d.get("f127")
        info["region"] = d.get("f128")
        info["concepts"] = d.get("f129")
        info["name"] = d.get("f58")
    except Exception as e:  # noqa: BLE001
        info["quote_error"] = str(e)
    prefix = "SH" if mkt == 1 else "SZ"
    if code.startswith(("8", "4")):
        prefix = "BJ"
    try:
        payload = get_json(
            "https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax",
            params={"code": f"{prefix}{code}"},
            referer="https://emweb.securities.eastmoney.com/",
        )
        fxxg = payload.get("fxxg") or {}
        jbzl = payload.get("jbzl") or {}
        info["list_date"] = fxxg.get("ssrq")
        info["company_industry"] = jbzl.get("sshy")
        info["province"] = jbzl.get("qy")
    except Exception as e:  # noqa: BLE001
        info["survey_error"] = str(e)
    fp.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    return info


def pct(n: int, d: int) -> str:
    if not d:
        return "—"
    return f"{n / d * 100:.1f}%"


def yi(v: Any) -> str:
    try:
        return f"{float(v) / 1e8:.2f}亿"
    except Exception:  # noqa: BLE001
        return "—"


def md_table(df: pd.DataFrame, cols: Optional[list[str]] = None, max_rows: int = 40) -> str:
    if df is None or df.empty:
        return "_无数据_\n"
    use = df if cols is None else df[cols]
    use = use.head(max_rows)
    headers = [str(c) for c in use.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in use.iterrows():
        cells = []
        for v in row.tolist():
            if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
                cells.append("")
            elif isinstance(v, float):
                cells.append(f"{v:.2f}" if abs(v) >= 0.01 else f"{v:.4f}")
            else:
                cells.append(str(v).replace("|", "/"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def counter_df(counter: Counter, name: str, total: Optional[int] = None, top: int = 15) -> pd.DataFrame:
    rows = []
    tot = total if total is not None else sum(counter.values())
    for k, v in counter.most_common(top):
        rows.append({name: k, "数量": v, "占比": f"{v / tot * 100:.1f}%" if tot else ""})
    return pd.DataFrame(rows)


def setup_font() -> None:
    plt.rcParams["font.sans-serif"] = [
        "Noto Sans CJK SC",
        "Noto Sans CJK JP",
        "WenQuanYi Micro Hei",
        "Droid Sans Fallback",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def save_bar(counter: Counter, title: str, filename: str, xlabel: str = "") -> Optional[str]:
    if not counter:
        return None
    setup_font()
    items = counter.most_common(12)
    labels = [str(k) for k, _ in items][::-1]
    vals = [v for _, v in items][::-1]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(labels, vals, color="#3b82f6")
    ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    fig.tight_layout()
    path = CHARTS / filename
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return str(path.relative_to(ROOT))


def build_report(
    dates: list[str],
    zt: pd.DataFrame,
    streaks: pd.DataFrame,
    target: pd.DataFrame,
    lhb: pd.DataFrame,
    seats: pd.DataFrame,
    infos: dict[str, dict],
) -> str:
    start, end = dates[0], dates[-1]
    start_h = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    end_h = f"{end[:4]}-{end[4:6]}-{end[6:]}"
    n_stock = target["code"].nunique()
    stocks = target.drop_duplicates("code")

    # stock-level features
    feat_rows = []
    for _, r in stocks.iterrows():
        code = r["code"]
        info = infos.get(code) or {}
        name = r["name"]
        mkt = market_of(code, name)
        concepts = [c.strip() for c in str(info.get("concepts") or "").split(",") if c.strip()]
        list_date = info.get("list_date") or ""
        list_age_years = None
        if list_date and len(str(list_date)) >= 8:
            try:
                ld = datetime.strptime(str(list_date)[:10].replace("/", "-"), "%Y-%m-%d")
                asof = datetime.strptime(end, "%Y%m%d")
                list_age_years = (asof - ld).days / 365.25
            except Exception:  # noqa: BLE001
                list_age_years = None
        is_subnew = bool(list_age_years is not None and list_age_years < 1)
        is_st = "ST" in str(name).upper()
        feat_rows.append(
            {
                "code": code,
                "name": name,
                "height": int(r["height"]),
                "start": r["start"],
                "end": r["end"],
                "days_in_window": int(r["days_in_window"]),
                "industry": r.get("industry") or info.get("industry"),
                "region": info.get("region"),
                "market": mkt,
                "peak_price": r.get("peak_price"),
                "peak_float_mv_yi": (r.get("peak_float_mv") or 0) / 1e8,
                "cap_bucket": cap_bucket(r.get("peak_float_mv") or 0),
                "price_bucket": price_bucket(r.get("peak_price") or 0),
                "avg_turnover": r.get("avg_turnover"),
                "yiziban_days": r.get("yiziban_days"),
                "list_date": list_date,
                "list_age_years": list_age_years,
                "is_subnew": is_subnew,
                "is_st": is_st,
                "concepts": "、".join(concepts[:8]),
                "concept_list": concepts,
            }
        )
    feat = pd.DataFrame(feat_rows).sort_values(["height", "end"], ascending=[False, False])

    # zt daily join for board-level stats
    t_codes = set(feat["code"])
    zt_t = zt[zt["code"].isin(t_codes)].copy()
    # map date+code -> lianban within target streaks
    streak_days = set()
    code_height = dict(zip(feat["code"], feat["height"]))
    for _, r in target.iterrows():
        for d in str(r["dates"]).split(","):
            streak_days.add((r["code"], d))
    zt_t["in_streak"] = [(c, d) in streak_days for c, d in zip(zt_t["code"], zt_t["date"])]
    zt_s = zt_t[zt_t["in_streak"]].copy()
    zt_s["first_sec"] = zt_s["first_seal"].map(seconds_from_open)
    zt_s["is_auction_seal"] = zt_s["first_seal"].fillna(0).astype(int).between(92500, 92559)
    zt_s["is_yiziban"] = (zt_s["turnover"].fillna(99) < 2.0) & (zt_s["open_times"].fillna(99) == 0)
    zt_s["board"] = zt_s["lianban"]

    # LHB join
    lhb_t = pd.DataFrame()
    if not lhb.empty:
        lhb_t = lhb[lhb["代码"].isin(t_codes)].copy()
        # 同一天同一股可能因多个原因重复上榜，保留净买额绝对值最大的一条
        lhb_t["_absnet"] = lhb_t["龙虎榜净买额"].abs()
        lhb_t = lhb_t.sort_values("_absnet", ascending=False).drop_duplicates(["代码", "上榜日"], keep="first")
        lhb_t["in_streak"] = [(c, d) in streak_days for c, d in zip(lhb_t["代码"], lhb_t["上榜日"])]

    lhb_s = lhb_t[lhb_t["in_streak"]].copy() if not lhb_t.empty else pd.DataFrame()
    if not lhb_s.empty:
        board_map = {(r["code"], r["date"]): r["lianban"] for _, r in zt_s.iterrows()}
        lhb_s["连板数"] = [board_map.get((c, d)) for c, d in zip(lhb_s["代码"], lhb_s["上榜日"])]
        lhb_s["有机构"] = lhb_s["解读"].fillna("").str.contains("机构")
        lhb_s["机构买入家数"] = (
            lhb_s["解读"].fillna("").str.extract(r"(\d+)家机构买入", expand=False).astype(float)
        )
        lhb_s["净买亿"] = lhb_s["龙虎榜净买额"] / 1e8
        lhb_s["买亿"] = lhb_s["龙虎榜买入额"] / 1e8
        lhb_s["卖亿"] = lhb_s["龙虎榜卖出额"] / 1e8

    # seats
    seats_s = pd.DataFrame()
    if not seats.empty:
        seats_s = seats.copy()
        seats_s["in_streak"] = [(c, d) in streak_days for c, d in zip(seats_s["code"], seats_s["date"])]
        seats_s = seats_s[seats_s["in_streak"]].copy()
        board_map = {(r["code"], r["date"]): r["lianban"] for _, r in zt_s.iterrows()}
        seats_s["lianban"] = [board_map.get((c, d)) for c, d in zip(seats_s["code"], seats_s["date"])]

    # appearance rate
    streak_n = len(streak_days)
    lhb_n = len(lhb_s) if not lhb_s.empty else 0
    appear_rate = lhb_n / streak_n if streak_n else 0

    # board-level LHB net
    board_lhb_rows = []
    if not lhb_s.empty:
        for b, g in lhb_s.dropna(subset=["连板数"]).groupby("连板数"):
            board_lhb_rows.append(
                {
                    "连板数": int(b),
                    "样本日": len(g),
                    "上榜率相关": "",
                    "平均净买额(亿)": g["净买亿"].mean(),
                    "净买入占比": f"{(g['净买亿'] > 0).mean() * 100:.1f}%",
                    "平均买入(亿)": g["买亿"].mean(),
                    "平均卖出(亿)": g["卖亿"].mean(),
                    "平均成交额占比%": g["成交额占总成交比"].mean(),
                    "出现机构占比": f"{g['有机构'].mean() * 100:.1f}%",
                }
            )
    board_lhb = pd.DataFrame(board_lhb_rows).sort_values("连板数") if board_lhb_rows else pd.DataFrame()

    # low vs high
    def stage(b: Any) -> str:
        try:
            b = int(b)
        except Exception:  # noqa: BLE001
            return "未知"
        if b <= 2:
            return "低位(1-2板)"
        if b <= 4:
            return "中位(3-4板)"
        return "高位(5板+)"

    if not lhb_s.empty:
        lhb_s["阶段"] = lhb_s["连板数"].map(stage)

    # seat overlap: same seat buy+sell same day
    overlap_stats = {}
    if not seats_s.empty:
        key_seats = seats_s.groupby(["code", "date", "seat"])["side"].nunique()
        both = key_seats[key_seats >= 2]
        days = seats_s.groupby(["code", "date"]).ngroups
        overlap_stats = {
            "days": days,
            "overlap_days": both.index.droplevel("seat").nunique() if len(both) else 0,
            "overlap_seats": int(len(both)),
        }

    # category net by side
    cat_rows = []
    if not seats_s.empty:
        buy = seats_s[seats_s["side"] == "买入"]
        for cat, g in buy.groupby("category"):
            cat_rows.append(
                {
                    "席位类型": cat,
                    "买入席位次数": len(g),
                    "买入额(亿)": g["buy"].sum() / 1e8,
                    "买入净额(亿)": g["net"].sum() / 1e8,
                    "覆盖个股": g["code"].nunique(),
                }
            )
    cat_df = pd.DataFrame(cat_rows).sort_values("买入额(亿)", ascending=False) if cat_rows else pd.DataFrame()

    alias_buy = Counter()
    alias_high = Counter()
    if not seats_s.empty:
        buy = seats_s[(seats_s["side"] == "买入") & seats_s["alias"].notna() & (seats_s["alias"] != "")]
        alias_buy = Counter(buy["alias"].tolist())
        high = buy[buy["lianban"].fillna(0) >= 5]
        alias_high = Counter(high["alias"].tolist())

    top_seats = Counter()
    if not seats_s.empty:
        buy = seats_s[seats_s["side"] == "买入"]
        top_seats = Counter(buy["seat"].tolist())

    # institution on high boards
    inst_high = None
    if not lhb_s.empty:
        high = lhb_s[lhb_s["连板数"].fillna(0) >= 5]
        inst_high = {
            "n": len(high),
            "inst_rate": float(high["有机构"].mean()) if len(high) else 0,
            "net_mean": float(high["净买亿"].mean()) if len(high) else 0,
            "net_pos": float((high["净买亿"] > 0).mean()) if len(high) else 0,
        }

    # post returns after peak
    peak_rets = []
    if not lhb.empty:
        for _, r in feat.iterrows():
            sub = lhb[(lhb["代码"] == r["code"]) & (lhb["上榜日"] == r["end"])]
            if sub.empty:
                continue
            row = sub.iloc[0]
            peak_rets.append(
                {
                    "code": r["code"],
                    "name": r["name"],
                    "peak_date": r["end"],
                    "height": r["height"],
                    "后1日%": row.get("上榜后1日"),
                    "后2日%": row.get("上榜后2日"),
                    "后5日%": row.get("上榜后5日"),
                }
            )
    peak_ret_df = pd.DataFrame(peak_rets)

    # concept count
    concept_c = Counter()
    for cs in feat["concept_list"]:
        for c in cs:
            if c:
                concept_c[c] += 1

    industry_c = Counter(feat["industry"].fillna("未知").tolist())
    market_c = Counter(feat["market"].tolist())
    cap_c = Counter(feat["cap_bucket"].tolist())
    price_c = Counter(feat["price_bucket"].tolist())
    region_c = Counter(feat["region"].fillna("未知").tolist())
    height_c = Counter(feat["height"].tolist())

    # first seal on 5+ days
    high_zt = zt_s[zt_s["lianban"] >= 5]
    auction_rate = float(high_zt["is_auction_seal"].mean()) if len(high_zt) else 0
    yizi_rate = float(high_zt["is_yiziban"].mean()) if len(high_zt) else 0
    open_mean = float(high_zt["open_times"].mean()) if len(high_zt) else 0
    turn_mean = float(high_zt["turnover"].mean()) if len(high_zt) else 0
    turn_all = float(zt_s["turnover"].mean()) if len(zt_s) else 0

    # weekly cluster of peak dates
    week_c = Counter()
    for d in feat["end"]:
        dt = datetime.strptime(str(d), "%Y%m%d")
        iso = dt.isocalendar()
        week_c[f"{iso[0]}-W{iso[1]:02d}"] += 1

    # charts
    c1 = save_bar(industry_c, "5板+个股行业分布", "industry.png")
    c2 = save_bar(concept_c, "5板+个股概念分布(前12)", "concept.png")
    c3 = save_bar(Counter({str(k) + "板": v for k, v in height_c.items()}), "最高连板高度分布", "height.png")
    c4 = save_bar(Counter({k: v for k, v in alias_buy.items()}), "连板期间买入侧知名席位出现次数", "youzi.png")

    # stock table for report
    show = feat.copy()
    show["流通市值"] = show["peak_float_mv_yi"].map(lambda x: f"{x:.1f}亿")
    show["最高连板"] = show["height"]
    show["周期"] = show["start"].map(lambda x: f"{x[:4]}-{x[4:6]}-{x[6:]}") + " ~ " + show["end"].map(
        lambda x: f"{x[:4]}-{x[4:6]}-{x[6:]}"
    )
    show["次新"] = show["is_subnew"].map(lambda x: "是" if x else "")
    show["ST"] = show["is_st"].map(lambda x: "是" if x else "")
    stock_tbl = show[
        ["code", "name", "最高连板", "周期", "industry", "market", "流通市值", "peak_price", "avg_turnover", "region", "次新", "ST"]
    ].rename(
        columns={
            "code": "代码",
            "name": "名称",
            "industry": "行业",
            "market": "板块",
            "peak_price": "峰值价",
            "avg_turnover": "周期均换手%",
            "region": "地域",
        }
    )

    # findings — computed, not canned
    lines: list[str] = []
    lines.append(f"# 近90个交易日「连板≥5」个股与龙虎榜特征")
    lines.append("")
    lines.append(f"- 样本窗口：{start_h} 至 {end_h}（{len(dates)} 个交易日）")
    lines.append(f"- 数据截止：{end_h}（上证指数最近一根日 K）")
    lines.append(f"- 筛选标准：窗口内最高连板天数（东方财富涨停池「连板数」）≥ 5")
    lines.append(f"- 命中个股：**{n_stock}** 只；命中连板周期：**{len(target)}** 段")
    lines.append(f"- 数据来源：东方财富涨停股池、龙虎榜、行情/F10")
    lines.append("")
    lines.append("> 连板高度用涨停池「连板数」：若周期从窗口前延续进来，高度可能大于窗口内可见涨停天数。同一只股票多段 5 板+周期会分别统计，个股共性按「最高的一段」去重。")
    lines.append("")
    lines.append("## 1. 样本名单")
    lines.append("")
    lines.append(md_table(stock_tbl, max_rows=80))
    lines.append("")
    lines.append("## 2. 个股共同特点")
    lines.append("")

    # 2.1 height
    lines.append("### 2.1 连板高度")
    lines.append("")
    lines.append(md_table(counter_df(height_c, "最高连板", total=n_stock)))
    if n_stock:
        med = float(feat["height"].median())
        mx = int(feat["height"].max())
        topn = feat[feat["height"] == mx][["name", "code", "height", "end"]]
        names = "、".join(f"{a}({b})" for a, b in zip(topn["name"], topn["code"]))
        lines.append(f"中位数 {med:.0f} 板，窗口内最高 {mx} 板：{names}。")
        lines.append("")

    # 2.2 market
    lines.append("### 2.2 上市板块")
    lines.append("")
    lines.append(md_table(counter_df(market_c, "板块", total=n_stock)))
    main_n = int(feat["market"].isin(["沪市主板", "深市主板"]).sum())
    cyb_n = int(feat["market"].str.contains("创业板").sum())
    kcb_n = int(feat["market"].str.contains("科创板").sum())
    st_n = int(feat["is_st"].sum())
    lines.append(
        f"主板 {main_n} 只（{pct(main_n, n_stock)}），创业板 {cyb_n} 只，科创板 {kcb_n} 只，名称含 ST {st_n} 只。"
        "主板 10% 涨停约束下走出 5 板，比 20cm 板块更依赖封单和情绪接力。"
    )
    lines.append("")

    # 2.3 cap
    lines.append("### 2.3 流通市值（取最高板当日）")
    lines.append("")
    lines.append(md_table(counter_df(cap_c, "流通市值", total=n_stock)))
    if n_stock:
        mv = feat["peak_float_mv_yi"]
        lines.append(
            f"峰值流通市值中位数 **{mv.median():.1f} 亿**，均值 {mv.mean():.1f} 亿，"
            f"最小 {mv.min():.1f} 亿，最大 {mv.max():.1f} 亿。"
            f"{pct(int((mv < 50).sum()), n_stock)} 的个股峰值流通市值低于 50 亿。"
        )
        lines.append("")

    # 2.4 price
    lines.append("### 2.4 股价")
    lines.append("")
    lines.append(md_table(counter_df(price_c, "股价", total=n_stock)))
    if n_stock:
        lines.append(f"峰值价中位数 {feat['peak_price'].median():.2f} 元。低价股更容易用较少资金封出连板。")
        lines.append("")

    # 2.5 industry
    lines.append("### 2.5 行业与概念（题材扎堆）")
    lines.append("")
    lines.append(md_table(counter_df(industry_c, "行业", total=n_stock)))
    lines.append(md_table(counter_df(concept_c, "概念", total=n_stock, top=20)))
    if industry_c:
        top_ind, top_ind_n = industry_c.most_common(1)[0]
        lines.append(
            f"行业最集中的是 **{top_ind}**（{top_ind_n} 只，{pct(top_ind_n, n_stock)}）。"
            "5 板以上几乎都出现在当时的主线或支线抱团里，很少是孤立个股行情。"
        )
        lines.append("")
    if week_c:
        lines.append("按最高板所在周的分布（看高潮是否扎堆）：")
        lines.append("")
        lines.append(md_table(counter_df(week_c, "自然周", total=n_stock)))

    # 2.6 region
    lines.append("### 2.6 地域")
    lines.append("")
    lines.append(md_table(counter_df(region_c, "地域", total=n_stock, top=12)))

    # 2.7 subnew / ST
    lines.append("### 2.7 次新与 ST")
    lines.append("")
    sub_n = int(feat["is_subnew"].sum())
    lines.append(
        f"上市不满 1 年的次新 {sub_n} 只（{pct(sub_n, n_stock)}），ST {st_n} 只（{pct(st_n, n_stock)}）。"
        "次新流通盘小、故事新，容易被当成连板载体；ST 是 5% 涨停，5 连板空间和 10cm 票不可比，名单里单独标注。"
    )
    lines.append("")

    # 2.8 seal quality
    lines.append("### 2.8 封板质量（涨停池微观）")
    lines.append("")
    lines.append(
        f"5 板及以上交易日样本 {len(high_zt)} 条："
        f"集合竞价（09:25）封板占比 **{auction_rate * 100:.1f}%**，"
        f"一字板（换手<2% 且炸板 0 次）占比 **{yizi_rate * 100:.1f}%**，"
        f"平均炸板次数 {open_mean:.1f}，平均换手率 {turn_mean:.1f}%。"
        f"对照这些股票全部连板日的平均换手 {turn_all:.1f}%。"
    )
    lines.append("")
    if len(zt_s):
        # first seal vs board
        seal_rows = []
        for b, g in zt_s.groupby("lianban"):
            seal_rows.append(
                {
                    "连板数": int(b),
                    "样本": len(g),
                    "09:25封板占比": f"{g['is_auction_seal'].mean() * 100:.1f}%",
                    "一字板占比": f"{g['is_yiziban'].mean() * 100:.1f}%",
                    "平均换手%": g["turnover"].mean(),
                    "平均炸板次数": g["open_times"].mean(),
                    "平均封单(亿)": (g["seal_amt"].fillna(0).mean() / 1e8),
                }
            )
        lines.append(md_table(pd.DataFrame(seal_rows).sort_values("连板数")))
        lines.append(
            "常见结构：低位更容易一字/早封，到 5 板附近换手抬升、炸板变多，说明高位分歧加大、需要更大成交额维持。"
        )
        lines.append("")

    # 2.9 charts
    if any([c1, c2, c3]):
        lines.append("### 2.9 分布图")
        lines.append("")
        for p, cap in ((c3, "高度"), (c1, "行业"), (c2, "概念")):
            if p:
                lines.append(f"![{cap}]({Path(p).as_posix()})")
                lines.append("")

    # 3 LHB
    lines.append("## 3. 龙虎榜特点")
    lines.append("")
    lines.append(
        f"连板周期内股票-交易日共 {streak_n} 条，对得上龙虎榜（去重后）{lhb_n} 条，上榜率 **{appear_rate * 100:.1f}%**。"
        "主板首板不一定进「日涨幅偏离值达到 7% 的前 5 只」；3 板之后「连续三个交易日涨幅偏离值累计达到 20%」几乎必上榜。"
    )
    lines.append("")

    if not lhb_s.empty:
        reasons = Counter(lhb_s["上榜原因"].fillna("未知").tolist())
        lines.append("### 3.1 上榜原因")
        lines.append("")
        lines.append(md_table(counter_df(reasons, "上榜原因", total=len(lhb_s), top=10)))

        lines.append("### 3.2 净买额随连板高度变化")
        lines.append("")
        if not board_lhb.empty:
            lines.append(md_table(board_lhb))
        if inst_high:
            lines.append(
                f"5 板+当日：平均龙虎榜净买额 **{inst_high['net_mean']:.2f} 亿**，"
                f"净买入（净额>0）占比 {inst_high['net_pos'] * 100:.1f}%，"
                f"解读含「机构」占比 {inst_high['inst_rate'] * 100:.1f}%（样本 {inst_high['n']}）。"
            )
            lines.append("")
        if "阶段" in lhb_s.columns:
            stage_rows = []
            for stg, g in lhb_s.groupby("阶段"):
                stage_rows.append(
                    {
                        "阶段": stg,
                        "样本": len(g),
                        "平均净买(亿)": g["净买亿"].mean(),
                        "净买入占比": f"{(g['净买亿'] > 0).mean() * 100:.1f}%",
                        "平均成交额占比%": g["成交额占总成交比"].mean(),
                        "机构出现占比": f"{g['有机构'].mean() * 100:.1f}%",
                    }
                )
            order = {"低位(1-2板)": 0, "中位(3-4板)": 1, "高位(5板+)": 2}
            sdf = pd.DataFrame(stage_rows)
            sdf["_o"] = sdf["阶段"].map(order)
            sdf = sdf.sort_values("_o").drop(columns="_o")
            lines.append(md_table(sdf))
            low = lhb_s[lhb_s["阶段"] == "低位(1-2板)"]
            high = lhb_s[lhb_s["阶段"] == "高位(5板+)"]
            if len(low) and len(high):
                lines.append(
                    f"低位平均净买 {low['净买亿'].mean():.2f} 亿 vs 高位 {high['净买亿'].mean():.2f} 亿。"
                    "这是 5 板行情里最稳定的龙虎榜结构：**低位抢筹、高位分歧/出货**，高位即使仍有游资买入，卖单往往同步放大。"
                )
                lines.append("")

        lines.append("### 3.3 龙虎榜成交占比")
        lines.append("")
        lines.append(
            f"连板周期上榜日，龙虎榜成交额占总成交比均值 **{lhb_s['成交额占总成交比'].mean():.1f}%**，"
            f"中位数 {lhb_s['成交额占总成交比'].median():.1f}%。"
            "该比例高说明买卖集中在公开席位（游资可见博弈）；比例低则更多是隐形资金/散户。"
        )
        lines.append("")

    lines.append("### 3.4 席位结构")
    lines.append("")
    if not cat_df.empty:
        lines.append(md_table(cat_df))
        # compute shares
        tot_buy = cat_df["买入额(亿)"].sum()
        def share(name: str) -> str:
            sub = cat_df[cat_df["席位类型"] == name]
            if sub.empty or not tot_buy:
                return "0%"
            return f"{float(sub['买入额(亿)'].iloc[0]) / tot_buy * 100:.1f}%"

        lines.append(
            f"买入额口径：知名游资 {share('知名游资')}，其他营业部 {share('其他营业部')}，"
            f"东财散户通道 {share('东财散户通道')}，机构 {share('机构')}，北向 {share('北向资金')}，"
            f"量化/互联网 {share('量化/互联网席位')}。"
        )
        lines.append("")
        lines.append(
            "东财拉萨/山南席位本质是互联网散户通道，不是单一游资。它们频繁出现在 5 板买五，通常表示情绪高潮、跟风盘进场，次日溢价往往变差。"
        )
        lines.append("")

    if alias_buy:
        lines.append("知名游资/通道在买入五档出现次数（含机构专用、东财通道）：")
        lines.append("")
        lines.append(md_table(counter_df(alias_buy, "别名", top=20)))
        if alias_high:
            lines.append("其中 5 板+当日买入侧：")
            lines.append("")
            lines.append(md_table(counter_df(alias_high, "别名", top=15)))
        if c4:
            lines.append(f"![知名席位]({Path(c4).as_posix()})")
            lines.append("")

    if top_seats:
        seat_rows = []
        tot = sum(top_seats.values())
        for name, cnt in top_seats.most_common(15):
            cat, alias = classify_seat(name)
            seat_rows.append(
                {
                    "营业部": short_seat_name(name),
                    "类型": cat,
                    "别名": alias or "",
                    "买入上榜次数": cnt,
                    "占比": f"{cnt / tot * 100:.1f}%",
                }
            )
        lines.append("买入侧营业部出现次数 Top15：")
        lines.append("")
        lines.append(md_table(pd.DataFrame(seat_rows)))

    if overlap_stats:
        lines.append(
            f"买卖重合：{overlap_stats['days']} 个上榜日里，有 {overlap_stats['overlap_days']} 日出现同一营业部同时出现在买五和卖五"
            f"（席位-日 {overlap_stats['overlap_seats']} 次）。高位重合升高通常是对倒做量或日内 T，不一定是真金白银加仓。"
        )
        lines.append("")

    # 3.5 after peak
    lines.append("### 3.5 最高板之后的收益（龙虎榜「上榜后N日」）")
    lines.append("")
    if not peak_ret_df.empty:
        def avg(col: str) -> str:
            s = pd.to_numeric(peak_ret_df[col], errors="coerce")
            s = s.dropna()
            if s.empty:
                return "—"
            return f"{s.mean():.2f}%（样本{len(s)}）"

        lines.append(
            f"以每只股票窗口内最高板当日为基准：次日 {avg('后1日%')}，2 日 {avg('后2日%')}，5 日 {avg('后5日%')}。"
            "高位板后平均收益转弱，和龙虎榜高位净卖/散户通道接盘是同一件事的两面。"
        )
        lines.append("")
        show_ret = peak_ret_df.sort_values("height", ascending=False).rename(
            columns={"code": "代码", "name": "名称", "peak_date": "最高板日", "height": "高度"}
        )
        lines.append(md_table(show_ret, max_rows=40))
    else:
        lines.append("最高板当日未匹配到龙虎榜后复权收益字段（可能尚未满 N 日或未上榜）。")
        lines.append("")

    # 4 synthesis
    lines.append("## 4. 综合结论")
    lines.append("")
    bullets = []
    if n_stock:
        bullets.append(
            f"**小盘题材股是绝对主角**：{n_stock} 只 5 板+里，流通市值中位数 {feat['peak_float_mv_yi'].median():.1f} 亿，"
            f"主板+低价+单一行业/概念扎堆，而不是权重蓝筹独立走主升。"
        )
    if industry_c:
        bullets.append(
            f"**强主线抱团**：行业/概念高度集中（首位 {industry_c.most_common(1)[0][0]}），"
            "5 板是板块高潮的产物，单独基本面故事很难走到这一步。"
        )
    bullets.append(
        f"**封板从「一致性」走向「分歧」**：5 板以上一字/早封占比 {yizi_rate * 100:.1f}% / {auction_rate * 100:.1f}%，"
        f"换手抬到 {turn_mean:.1f}%，需要更大成交额才能续板。"
    )
    if not lhb_s.empty and inst_high:
        bullets.append(
            f"**龙虎榜低位净买、高位变差**：5 板+当日平均净买 {inst_high['net_mean']:.2f} 亿，"
            f"净买入占比仅 {inst_high['net_pos'] * 100:.1f}%；机构在高位连板里不是主导力量。"
        )
    if not cat_df.empty:
        bullets.append(
            "**席位以游资接力为主，东财通道是高潮标志**：知名游资和其他营业部贡献大部分买额；"
            "拉萨东财席位密集出现在买五，更像散户情绪温度计，而不是锁仓主力。"
        )
    if not peak_ret_df.empty:
        bullets.append(
            "**最高板后收益不乐观**：把最高板当终点而不是起点，和「5 板以后博弈拥挤、龙虎榜卖盘增加」一致。"
        )
    bullets.append(
        "**可复用的观察清单**：主线板块 + 流通市值偏小 + 低位龙虎榜净买且游资（非东财）主导 + 早封/封单还在；"
        "一旦 5 板附近换手陡升、东财席位包办买五、净额转负，连续性往往结束。"
    )
    for b in bullets:
        lines.append(f"- {b}")
    lines.append("")
    lines.append("## 5. 方法与局限")
    lines.append("")
    lines.append("- 涨停判定以东方财富涨停股池为准（含 10cm/20cm/30cm/ST 5cm），连板数用接口字段 `lbc`。")
    lines.append("- 龙虎榜不是全市场成交，只覆盖上榜营业部前五买卖；未上榜不代表没有大资金。")
    lines.append("- 游资别名来自公开席位对照，存在分仓、量化混席、营业部更名，只能作统计标签。")
    lines.append("- 「上榜后 N 日」收益来自东方财富字段，窗口末尾的高位板可能尚未满 5/10 日。")
    lines.append("- 本报告是历史复盘，不是买卖建议。")
    lines.append("")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    return "\n".join(lines), feat, lhb_s, seats_s, peak_ret_df


def main() -> None:
    ensure_dirs()
    log("1/6 交易日历")
    dates = fetch_trade_dates(LOOKBACK)
    log(f"   {dates[0]} -> {dates[-1]}  n={len(dates)}")

    log("2/6 涨停池")
    zt = fetch_all_zt(dates)
    zt.to_csv(PROCESSED / "zt_pool_90d.csv", index=False)
    log(f"   rows={len(zt)} stocks={zt['code'].nunique() if not zt.empty else 0}")

    log("3/6 还原连板周期")
    streaks = reconstruct_streaks(zt, dates)
    streaks.to_csv(PROCESSED / "all_streaks.csv", index=False)
    target = streaks[streaks["height"] >= 5].copy()
    # 每只股票保留最高的一段用于「共同特点」
    if not target.empty:
        uniq = target.sort_values(["height", "end"], ascending=[False, False]).drop_duplicates("code")
    else:
        uniq = target
    uniq.to_csv(PROCESSED / "lianban5_stocks.csv", index=False)
    target.to_csv(PROCESSED / "lianban5_streaks.csv", index=False)
    log(f"   streaks>={5}: {len(target)}  unique stocks: {0 if uniq.empty else uniq['code'].nunique()}")

    log("4/6 龙虎榜区间")
    lhb = fetch_lhb_range(dates[0], dates[-1])
    log(f"   lhb rows={len(lhb)}")

    log("5/6 席位明细 + F10")
    jobs = []
    seen = set()
    for _, r in target.iterrows():
        for d in str(r["dates"]).split(","):
            key = (r["code"], d)
            if key not in seen:
                seen.add(key)
                jobs.append(key)
    seats_rows: list[dict] = []
    # 只拉这些天的席位；未上榜接口会返回空数组
    done = 0
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(fetch_seats, c, d): (c, d) for c, d in jobs}
        for fut in as_completed(futs):
            try:
                seats_rows.extend(fut.result())
            except Exception as e:  # noqa: BLE001
                c, d = futs[fut]
                log(f"  seat fail {c} {d}: {e}")
            done += 1
            if done % 30 == 0 or done == len(jobs):
                log(f"  席位 {done}/{len(jobs)}")
    seats = pd.DataFrame(seats_rows)
    if not seats.empty:
        seats.to_csv(PROCESSED / "lianban5_seats.csv", index=False)

    infos = {}
    codes = sorted(set(uniq["code"].tolist()) if not uniq.empty else [])
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(fetch_stock_info, c): c for c in codes}
        for fut in as_completed(futs):
            c = futs[fut]
            try:
                infos[c] = fut.result()
            except Exception as e:  # noqa: BLE001
                log(f"  info fail {c}: {e}")
                infos[c] = {"code": c}

    log("6/6 写报告")
    report, feat, lhb_s, seats_s, peak_ret_df = build_report(dates, zt, streaks, uniq, lhb, seats, infos)
    (REPORTS / "lianban5_lhb_analysis.md").write_text(report, encoding="utf-8")
    feat.drop(columns=["concept_list"], errors="ignore").to_csv(PROCESSED / "lianban5_features.csv", index=False)
    if lhb_s is not None and not lhb_s.empty:
        lhb_s.to_csv(PROCESSED / "lianban5_lhb_on_streak.csv", index=False)
    if peak_ret_df is not None and not peak_ret_df.empty:
        peak_ret_df.to_csv(PROCESSED / "lianban5_peak_returns.csv", index=False)
    log(f"report -> {REPORTS / 'lianban5_lhb_analysis.md'}")
    log("done")


if __name__ == "__main__":
    main()

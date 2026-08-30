#!/usr/bin/env python3
"""顺势选股 · 龙头盯盘 — 命令行表格版（东方财富数据源）。"""

from __future__ import annotations

import argparse
import re
import sys
from functools import cmp_to_key
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from tabulate import tabulate

PUSH2 = "https://push2delay.eastmoney.com/api/qt"
PUSH2EX = "https://push2ex.eastmoney.com"
UT = "bd1d9ddb04089700cf9c27f6f7426281"
ZT_UT = "7eea3edcaed734bea9cbfc24409ed989"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/center/boardlist.html",
    "Accept": "application/json,text/plain,*/*",
}

NOISE_PATTERNS = [
    r"昨日", r"前日", r"连板", r"涨停", r"跌停", r"破板", r"炸板", r"打板",
    r"首板", r"二板", r"三板", r"历史新高", r"历史新低", r"近期新高", r"近期新低",
    r"近期解禁", r"公告", r"^ST", r"ST股", r"次新股", r"沪股通", r"深股通",
    r"融资融券", r"转融通", r"高开低走", r"低开高走", r"高换手", r"成交活跃",
    r"含一字", r"题材股", r"热股", r"多板", r"东方财富",
]
NOISE_RES = [re.compile(p) for p in NOISE_PATTERNS]
ST_RE = re.compile(r"(?:\*?ST|S\*ST|\bST)", re.I)

BJ_TZ = timezone(timedelta(hours=8))


def beijing_ymd(when: datetime | None = None) -> str:
    dt = when or datetime.now(BJ_TZ)
    return dt.strftime("%Y%m%d")


def as_number(value: Any) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        n = float(value)
        return n if n == n else None
    except (TypeError, ValueError):
        return None


def as_string(value: Any) -> str | None:
    if value in (None, "-"):
        return None
    s = str(value).strip()
    return s or None


def format_amount(value: float | None) -> str:
    if value is None:
        return "--"
    sign = "-" if value < 0 else ""
    a = abs(value)
    if a >= 1e8:
        return f"{sign}{a / 1e8:.2f}亿"
    if a >= 1e4:
        return f"{sign}{a / 1e4:.1f}万" if a < 1e5 else f"{sign}{a / 1e4:.0f}万"
    return f"{sign}{a:.0f}"


def format_percent(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value:+.2f}%"


def format_fbt(value: int | float | None) -> str:
    if value is None:
        return "--"
    raw = int(value)
    if raw <= 0:
        return "--"
    s = str(raw).zfill(6)
    return f"{s[:2]}:{s[2:4]}:{s[4:6]}"


def eastmoney_market(code: str) -> int:
    code = code.strip()
    if code.startswith(("88", "6")):
        return 1
    return 0


def is_noise_board(name: str) -> bool:
    trimmed = name.strip()
    return any(p.search(trimmed) for p in NOISE_RES)


def is_st_stock(name: str) -> bool:
    return bool(ST_RE.search(name.replace(" ", "")))


def fetch_json(url: str, timeout: float = 8.0) -> Any:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def diff_rows(payload: Any) -> list[dict[str, Any]]:
    diff = (payload or {}).get("data", {}).get("diff")
    if not diff:
        return []
    if isinstance(diff, list):
        return diff
    return list(diff.values())


def clist_url(fs: str, fields: str, pz: int, fid: str = "f3") -> str:
    params = {
        "pn": "1",
        "pz": str(pz),
        "po": "1",
        "np": "1",
        "ut": UT,
        "fltt": "2",
        "invt": "2",
        "fid": fid,
        "fs": fs,
        "fields": fields,
        "_": str(int(datetime.now().timestamp() * 1000)),
    }
    return f"{PUSH2}/clist/get?" + "&".join(f"{k}={v}" for k, v in params.items())


def fetch_indices() -> list[dict[str, Any]]:
    params = {
        "fltt": "2",
        "invt": "2",
        "secids": "1.000001,0.399001,0.399006,1.000688",
        "fields": "f12,f14,f2,f3,f4,f6,f104,f105,f106",
    }
    url = f"{PUSH2}/ulist.np/get?" + "&".join(f"{k}={v}" for k, v in params.items())
    rows = diff_rows(fetch_json(url))
    out = []
    for row in rows:
        out.append(
            {
                "code": as_string(row.get("f12")) or "",
                "name": as_string(row.get("f14")) or "",
                "price": as_number(row.get("f2")),
                "change_percent": as_number(row.get("f3")),
                "amount": as_number(row.get("f6")),
                "up_count": as_number(row.get("f104")),
                "down_count": as_number(row.get("f105")),
            }
        )
    return out


def fetch_boards(kind: str) -> list[dict[str, Any]]:
    fs = "m:90+t:3+f:!50" if kind == "concept" else "m:90+t:2+f:!50"
    url = clist_url(
        fs,
        "f12,f14,f2,f3,f6,f8,f62,f104,f105,f128,f136,f140,f184",
        80,
    )
    rows = diff_rows(fetch_json(url))
    boards = []
    for row in rows:
        code = as_string(row.get("f12"))
        name = as_string(row.get("f14"))
        if not code or not name:
            continue
        boards.append(
            {
                "code": code,
                "name": name,
                "kind": kind,
                "change_percent": as_number(row.get("f3")),
                "amount": as_number(row.get("f6")),
                "main_net_inflow": as_number(row.get("f62")),
                "up_count": as_number(row.get("f104")),
                "down_count": as_number(row.get("f105")),
            }
        )
    return boards


def fetch_constituents(board_code: str) -> list[dict[str, Any]]:
    url = clist_url(
        f"b:{board_code}+f:!50",
        "f12,f13,f14,f2,f3,f6,f8,f15,f16,f17,f22,f62",
        80,
    )
    rows = diff_rows(fetch_json(url))
    stocks = []
    for row in rows:
        code = as_string(row.get("f12"))
        name = as_string(row.get("f14"))
        if not code or not name:
            continue
        stocks.append(
            {
                "code": code,
                "name": name,
                "market": int(as_number(row.get("f13")) or 0),
                "price": as_number(row.get("f2")),
                "change_percent": as_number(row.get("f3")),
                "amount": as_number(row.get("f6")),
            }
        )
    return stocks


def parse_zt(row: dict[str, Any]) -> dict[str, Any] | None:
    code = as_string(row.get("c"))
    if not code:
        return None
    stat = row.get("zttj") or {}
    return {
        "code": code,
        "name": as_string(row.get("n")) or code,
        "first_seal_time": int(as_number(row.get("fbt")) or 0),
        "consecutive_boards": int(as_number(row.get("lbc")) or 1),
        "seal_amount": as_number(row.get("fund")),
        "open_count": int(as_number(row.get("zbc")) or 0),
        "industry": as_string(row.get("hybk")),
    }


def parse_zb(row: dict[str, Any]) -> dict[str, Any] | None:
    code = as_string(row.get("c"))
    if not code:
        return None
    return {
        "code": code,
        "name": as_string(row.get("n")) or code,
        "first_seal_time": int(as_number(row.get("fbt")) or 0),
        "open_count": int(as_number(row.get("zbc")) or 1),
        "change_percent": as_number(row.get("zdp")),
    }


def fetch_zt_pool(date: str) -> tuple[str, int, list[dict[str, Any]]]:
    params = {
        "ut": ZT_UT,
        "dpt": "wz.ztzt",
        "Pageindex": "0",
        "pagesize": "500",
        "sort": "fbt:asc",
        "date": date,
    }
    url = f"{PUSH2EX}/getTopicZTPool?" + "&".join(f"{k}={v}" for k, v in params.items())
    data = fetch_json(url).get("data") or {}
    pool = [x for row in (data.get("pool") or []) if (x := parse_zt(row))]
    qdate = str(data.get("qdate") or date)
    tc = int(data.get("tc") or len(pool))
    return qdate, tc, pool


def fetch_zb_pool(date: str) -> tuple[str, int, list[dict[str, Any]]]:
    params = {
        "ut": ZT_UT,
        "dpt": "wz.ztzt",
        "Pageindex": "0",
        "pagesize": "300",
        "sort": "fbt:asc",
        "date": date,
    }
    url = f"{PUSH2EX}/getTopicZBPool?" + "&".join(f"{k}={v}" for k, v in params.items())
    data = fetch_json(url).get("data") or {}
    pool = [x for row in (data.get("pool") or []) if (x := parse_zb(row))]
    qdate = str(data.get("qdate") or date)
    tc = int(data.get("tc") or len(pool))
    return qdate, tc, pool


def compare_leaders(a: dict[str, Any], b: dict[str, Any]) -> int:
    if a["is_limit_up"] != b["is_limit_up"]:
        return -1 if a["is_limit_up"] else 1
    if a["is_limit_up"] and b["is_limit_up"] and a.get("zt") and b.get("zt"):
        za, zb = a["zt"], b["zt"]
        if za["first_seal_time"] != zb["first_seal_time"]:
            return za["first_seal_time"] - zb["first_seal_time"]
        if za["consecutive_boards"] != zb["consecutive_boards"]:
            return zb["consecutive_boards"] - za["consecutive_boards"]
        return int((zb.get("seal_amount") or 0) - (za.get("seal_amount") or 0))
    ca = a["stock"].get("change_percent")
    cb = b["stock"].get("change_percent")
    ca = ca if ca is not None else float("-inf")
    cb = cb if cb is not None else float("-inf")
    if ca != cb:
        return -1 if ca > cb else (1 if ca < cb else 0)
    aa = a["stock"].get("amount") or 0
    ab = b["stock"].get("amount") or 0
    if aa != ab:
        return -1 if aa > ab else (1 if aa < ab else 0)
    return 0


def leader_reason(item: dict[str, Any]) -> str:
    if item["is_limit_up"] and item.get("zt"):
        zt = item["zt"]
        time = format_fbt(zt["first_seal_time"])
        boards = f"{zt['consecutive_boards']}连板" if zt["consecutive_boards"] > 1 else "首板"
        kind = "竞价封" if zt["first_seal_time"] <= 92559 else "盘中封"
        open_txt = f" · 开板{zt['open_count']}次" if zt["open_count"] else " · 未开板"
        return f"{time}{kind} · {boards}{open_txt}"
    if item["is_broken"] and item.get("zb"):
        zb = item["zb"]
        return f"{format_fbt(zb['first_seal_time'])}曾封 · 炸板{zb['open_count']}次"
    pct = item["stock"].get("change_percent")
    if pct is not None:
        return f"板块内涨幅 {pct:+.2f}%"
    return "板块内排序"


def rank_leaders(
    stocks: list[dict[str, Any]],
    zt_by_code: dict[str, dict[str, Any]],
    zb_by_code: dict[str, dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    ranks = ["龙一", "龙二", "龙三"]
    scored = []
    for stock in stocks:
        if is_st_stock(stock["name"]):
            continue
        if stock.get("price") is None or stock.get("change_percent") is None:
            continue
        code = stock["code"]
        zt = zt_by_code.get(code)
        zb = zb_by_code.get(code)
        scored.append(
            {
                "stock": stock,
                "zt": zt,
                "zb": zb,
                "is_limit_up": bool(zt),
                "is_broken": bool(not zt and zb),
            }
        )
    scored.sort(key=cmp_to_key(compare_leaders))
    leaders = []
    for idx, item in enumerate(scored[:limit]):
        stock = item["stock"]
        zt = item.get("zt")
        zb = item.get("zb")
        leaders.append(
            {
                "rank": ranks[idx] if idx < len(ranks) else "龙三",
                "code": stock["code"],
                "name": stock["name"],
                "change_percent": stock.get("change_percent"),
                "price": stock.get("price"),
                "seal_amount": zt.get("seal_amount") if zt else None,
                "first_seal_time": format_fbt(zt["first_seal_time"] if zt else zb.get("first_seal_time") if zb else None),
                "consecutive_boards": zt["consecutive_boards"] if zt else None,
                "is_limit_up": item["is_limit_up"],
                "is_broken": item["is_broken"],
                "reason": leader_reason(item),
            }
        )
    return leaders


def rank_market_leaders(zt_pool: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    market_ranks = ["总龙头", "龙二", "龙三"]
    zt_by_code: dict[str, dict[str, Any]] = {}
    for zt in zt_pool:
        if is_st_stock(zt["name"]):
            continue
        zt_by_code.setdefault(zt["code"], zt)
    stocks = [
        {
            "code": zt["code"],
            "name": zt["name"],
            "market": eastmoney_market(zt["code"]),
            "price": 0.0,
            "change_percent": 10.0,
            "amount": zt.get("seal_amount"),
        }
        for zt in zt_by_code.values()
    ]
    ranked = rank_leaders(stocks, zt_by_code, {}, limit)
    out = []
    for idx, leader in enumerate(ranked):
        zt = zt_by_code.get(leader["code"])
        sector = (zt.get("industry") or "").strip() if zt else ""
        prefix = f"{sector} · " if sector else "全市场 · "
        out.append(
            {
                **leader,
                "rank": market_ranks[idx] if idx < len(market_ranks) else "龙三",
                "sector_name": sector or None,
                "reason": prefix + leader["reason"],
            }
        )
    return out


def sort_boards(boards: list[dict[str, Any]], sort_key: str) -> list[dict[str, Any]]:
    if sort_key == "amount":
        return sorted(boards, key=lambda b: b.get("amount") or 0, reverse=True)
    if sort_key == "inflow":
        return sorted(boards, key=lambda b: b.get("main_net_inflow") or 0, reverse=True)
    return sorted(boards, key=lambda b: b.get("change_percent") or float("-inf"), reverse=True)


def member_floor(board: dict[str, Any]) -> int:
    return int((board.get("up_count") or 0) + (board.get("down_count") or 0))


def build_snapshot(
    *,
    trade_date: str,
    universe: str = "all",
    sort: str = "change",
) -> dict[str, Any]:
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(fetch_indices): "indices",
            pool.submit(fetch_zt_pool, trade_date): "zt",
            pool.submit(fetch_zb_pool, trade_date): "zb",
        }
        if universe != "industry":
            futures[pool.submit(fetch_boards, "concept")] = "concept"
        if universe != "concept":
            futures[pool.submit(fetch_boards, "industry")] = "industry"

        results: dict[str, Any] = {}
        for fut in as_completed(futures):
            key = futures[fut]
            results[key] = fut.result()

    indices = results.get("indices", [])
    zt_date, zt_count, zt_pool = results["zt"]
    _, zb_count, zb_pool = results["zb"]
    zt_by_code = {x["code"]: x for x in zt_pool}
    zb_by_code = {x["code"]: x for x in zb_pool}

    boards = results.get("concept", []) + results.get("industry", [])
    boards = [b for b in boards if not is_noise_board(b["name"]) and member_floor(b) >= 4]
    boards = sort_boards(boards, "change" if sort == "limitUp" else sort)
    candidate_count = 12 if sort == "limitUp" else 6
    candidates = boards[:candidate_count]

    enriched = []
    for board in candidates:
        members = fetch_constituents(board["code"])
        leaders = rank_leaders(members, zt_by_code, zb_by_code, 3)
        limit_up_count = sum(1 for m in members if m["code"] in zt_by_code)
        broken_count = sum(
            1 for m in members if m["code"] not in zt_by_code and m["code"] in zb_by_code
        )
        enriched.append(
            {
                "board": board,
                "leaders": leaders,
                "member_count": len(members),
                "limit_up_count": limit_up_count,
                "broken_count": broken_count,
            }
        )

    if sort == "limitUp":
        enriched.sort(
            key=lambda x: (x["limit_up_count"], x["board"].get("change_percent") or 0),
            reverse=True,
        )

    sectors = enriched[:3]
    market_leaders = rank_market_leaders(zt_pool, 3)
    replay = trade_date != beijing_ymd()

    return {
        "trade_date": zt_date or trade_date,
        "replay_mode": replay,
        "indices": indices,
        "zt_count": zt_count,
        "zb_count": zb_count,
        "market_leaders": market_leaders,
        "sectors": sectors,
    }


def print_table(title: str, headers: list[str], rows: list[list[Any]]) -> None:
    print()
    print(title)
    print("=" * min(72, max(len(title), 40)))
    if not rows:
        print("(暂无数据)")
        return
    print(tabulate(rows, headers=headers, tablefmt="simple", stralign="left", numalign="right"))


def render_snapshot(snapshot: dict[str, Any]) -> None:
    trade_date = snapshot["trade_date"]
    y, m, d = trade_date[:4], trade_date[4:6], trade_date[6:8]
    print(f"\n顺势选股 · 龙头盯盘  |  交易日 {y}-{m}-{d}  |  数据源：东方财富")
    if snapshot["replay_mode"]:
        print("复盘模式：涨停/炸板池为所选日期，板块行情仍为实时数据")

    index_rows = [
        [
            item["name"],
            format_percent(item.get("change_percent")),
            f"{item.get('price') or '--'}",
            format_amount(item.get("amount")),
            f"{int(item.get('up_count') or 0)}/{int(item.get('down_count') or 0)}",
        ]
        for item in snapshot["indices"]
    ]
    print_table("大盘指数", ["指数", "涨幅", "点位", "成交额", "涨/跌家"], index_rows)
    print(f"全市场涨停 {snapshot['zt_count']}  ·  炸板 {snapshot['zb_count']}")

    market_rows = [
        [
            leader["rank"],
            leader["name"],
            leader["code"],
            leader.get("sector_name") or "--",
            format_percent(leader.get("change_percent")),
            leader.get("first_seal_time") or "--",
            leader.get("consecutive_boards") or "--",
            format_amount(leader.get("seal_amount")),
            leader["reason"],
        ]
        for leader in snapshot["market_leaders"]
    ]
    print_table(
        "今日全市场龙头（总龙头 / 龙二 / 龙三）",
        ["席位", "名称", "代码", "所属", "涨幅", "首封", "连板", "封单", "判定依据"],
        market_rows,
    )

    for idx, sector in enumerate(snapshot["sectors"], start=1):
        board = sector["board"]
        kind = "概念" if board["kind"] == "concept" else "行业"
        title = (
            f"板块{idx} · {kind} · {board['name']}  "
            f"({format_percent(board.get('change_percent'))}  "
            f"涨停{sector['limit_up_count']} 炸板{sector['broken_count']}  "
            f"成交{format_amount(board.get('amount'))})"
        )
        leader_rows = [
            [
                leader["rank"],
                leader["name"],
                leader["code"],
                "涨停" if leader["is_limit_up"] else ("炸板" if leader["is_broken"] else "--"),
                format_percent(leader.get("change_percent")),
                leader.get("first_seal_time") or "--",
                leader.get("consecutive_boards") or "--",
                format_amount(leader.get("seal_amount")),
                leader["reason"],
            ]
            for leader in sector["leaders"]
        ]
        print_table(title, ["席位", "名称", "代码", "状态", "涨幅", "首封", "连板", "封单", "判定依据"], leader_rows)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="顺势选股 · 龙头盯盘（命令行表格版）")
    parser.add_argument(
        "--date",
        default=beijing_ymd(),
        help="交易日 YYYYMMDD，默认今日（北京时间）",
    )
    parser.add_argument(
        "--universe",
        choices=["all", "concept", "industry"],
        default="all",
        help="板块范围：综合 / 概念 / 行业",
    )
    parser.add_argument(
        "--sort",
        choices=["change", "limitUp", "amount", "inflow"],
        default="change",
        help="板块排序：涨幅 / 涨停数 / 成交额 / 主力净流入",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    date = re.sub(r"\D", "", args.date)
    if len(date) != 8:
        print("日期格式应为 YYYYMMDD", file=sys.stderr)
        return 2
    try:
        snapshot = build_snapshot(trade_date=date, universe=args.universe, sort=args.sort)
        render_snapshot(snapshot)
        return 0
    except requests.RequestException as exc:
        print(f"行情获取失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""东方财富公开接口数据源。"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from engine.models import Board, LimitBreakInfo, LimitUpInfo, MarketSnapshot, Stock
from sources.base import DataSource

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
BJ_TZ = timezone(timedelta(hours=8))


def beijing_ymd(when: datetime | None = None) -> str:
    return (when or datetime.now(BJ_TZ)).strftime("%Y%m%d")


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


def fetch_json(url: str, timeout: float = 10.0) -> Any:
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


class EastMoneySource(DataSource):
    name = "eastmoney"
    label = "东方财富"

    def available(self) -> bool:
        try:
            fetch_json(
                f"{PUSH2}/ulist.np/get?fltt=2&invt=2&secids=1.000001&fields=f12,f14,f2,f3",
                timeout=5,
            )
            return True
        except Exception:
            return False

    def fetch_indices(self) -> list[dict[str, Any]]:
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

    def fetch_boards(self, kind: str) -> list[Board]:
        fs = "m:90+t:3+f:!50" if kind == "concept" else "m:90+t:2+f:!50"
        url = clist_url(fs, "f12,f14,f2,f3,f6,f8,f62,f104,f105,f128,f136,f140,f184", 80)
        rows = diff_rows(fetch_json(url))
        boards: list[Board] = []
        for row in rows:
            code = as_string(row.get("f12"))
            name = as_string(row.get("f14"))
            if not code or not name:
                continue
            boards.append(
                Board(
                    code=code,
                    name=name,
                    kind=kind,
                    change_percent=as_number(row.get("f3")),
                    amount=as_number(row.get("f6")),
                    main_net_inflow=as_number(row.get("f62")),
                    up_count=int(as_number(row.get("f104")) or 0),
                    down_count=int(as_number(row.get("f105")) or 0),
                    source=self.name,
                )
            )
        return boards

    def fetch_constituents(self, board_code: str) -> list[Stock]:
        url = clist_url(f"b:{board_code}+f:!50", "f12,f13,f14,f2,f3,f6,f8,f15,f16,f17,f22,f62", 80)
        rows = diff_rows(fetch_json(url))
        stocks: list[Stock] = []
        for row in rows:
            code = as_string(row.get("f12"))
            name = as_string(row.get("f14"))
            if not code or not name:
                continue
            # 过滤指数/基金成分噪声
            if re.match(r"^(1|5)\d{5}$", code) and not code.startswith(("60", "00", "30")):
                if code.startswith(("1", "5")):
                    continue
            stocks.append(
                Stock(
                    code=code,
                    name=name,
                    market=int(as_number(row.get("f13")) or 0),
                    price=as_number(row.get("f2")),
                    change_percent=as_number(row.get("f3")),
                    amount=as_number(row.get("f6")),
                    turnover=as_number(row.get("f8")),
                    main_net_inflow=as_number(row.get("f62")),
                    board_code=board_code,
                    source=self.name,
                )
            )
        return stocks

    def fetch_zt_pool(self, date: str) -> tuple[str, list[LimitUpInfo]]:
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
        pool: list[LimitUpInfo] = []
        for row in data.get("pool") or []:
            code = as_string(row.get("c"))
            if not code:
                continue
            pool.append(
                LimitUpInfo(
                    code=code,
                    name=as_string(row.get("n")) or code,
                    first_seal_time=int(as_number(row.get("fbt")) or 0),
                    consecutive_boards=int(as_number(row.get("lbc")) or 1),
                    seal_amount=as_number(row.get("fund")),
                    open_count=int(as_number(row.get("zbc")) or 0),
                    industry=as_string(row.get("hybk")),
                )
            )
        return str(data.get("qdate") or date), pool

    def fetch_zb_pool(self, date: str) -> list[LimitBreakInfo]:
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
        pool: list[LimitBreakInfo] = []
        for row in data.get("pool") or []:
            code = as_string(row.get("c"))
            if not code:
                continue
            pool.append(
                LimitBreakInfo(
                    code=code,
                    name=as_string(row.get("n")) or code,
                    first_seal_time=int(as_number(row.get("fbt")) or 0),
                    open_count=int(as_number(row.get("zbc")) or 1),
                    change_percent=as_number(row.get("zdp")),
                )
            )
        return pool

    def fetch_snapshot(self, trade_date: str | None = None) -> MarketSnapshot:
        date = trade_date or beijing_ymd()
        with ThreadPoolExecutor(max_workers=6) as pool:
            f_idx = pool.submit(self.fetch_indices)
            f_zt = pool.submit(self.fetch_zt_pool, date)
            f_zb = pool.submit(self.fetch_zb_pool, date)
            f_c = pool.submit(self.fetch_boards, "concept")
            f_i = pool.submit(self.fetch_boards, "industry")
            indices = f_idx.result()
            qdate, zt_pool = f_zt.result()
            zb_pool = f_zb.result()
            boards = f_c.result() + f_i.result()

        # 取涨幅靠前板块拉取成分，控制请求量
        boards_sorted = sorted(boards, key=lambda b: b.change_percent or float("-inf"), reverse=True)
        top = boards_sorted[:16]
        stocks_by_board: dict[str, list[Stock]] = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = {pool.submit(self.fetch_constituents, b.code): b for b in top}
            for fut in as_completed(futs):
                board = futs[fut]
                stocks = fut.result()
                for s in stocks:
                    s.board_name = board.name
                stocks_by_board[board.code] = stocks

        return MarketSnapshot(
            trade_date=qdate,
            source=self.name,
            indices=indices,
            boards=boards,
            stocks_by_board=stocks_by_board,
            zt_by_code={x.code: x for x in zt_pool},
            zb_by_code={x.code: x for x in zb_pool},
            notes=["东方财富公开行情 / 涨停池"],
        )

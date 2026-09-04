"""同花顺数据源 —— 免费公开接口（无需 API Key）。

数据来自同花顺网页/开放热榜接口（data.10jqka.com.cn / dq.10jqka.com.cn），
不经过扶摇付费通道。可选本地 CSV 导出作离线兜底。
"""

from __future__ import annotations

import csv
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import requests

from engine.models import Board, LimitUpInfo, MarketSnapshot, Stock
from sources.base import DataSource
from sources.eastmoney import beijing_ymd

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://data.10jqka.com.cn/",
    "Accept": "application/json,text/plain,*/*",
}

# 涨停板块榜（含成分股）
BLOCK_TOP_URL = "https://data.10jqka.com.cn/dataapi/limit_up/block_top"
# 涨停池
ZT_POOL_URL = "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool"
# 热门概念 / 行业板块
HOT_PLATE_URL = "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/plate"
# 热股榜（含概念标签）
HOT_STOCK_URL = "https://eq.10jqka.com.cn/open/api/hot_list/v1/hot_stock/a/hour/data.txt"


def _f(value: Any) -> float | None:
    if value in (None, "", "-", "--"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _unix_to_hhmmss(ts: Any) -> int:
    """unix 秒 → 093015 形式；失败返回 0。"""
    try:
        from datetime import datetime, timedelta, timezone

        bj = timezone(timedelta(hours=8))
        dt = datetime.fromtimestamp(int(ts), tz=bj)
        return int(dt.strftime("%H%M%S"))
    except Exception:
        return 0


class TonghuashunSource(DataSource):
    name = "tonghuashun"
    label = "同花顺(免费)"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def available(self) -> bool:
        try:
            resp = self.session.get(
                HOT_PLATE_URL,
                params={"type": "concept"},
                timeout=6,
            )
            if resp.status_code == 200 and resp.json().get("status_code") == 0:
                return True
        except Exception:
            pass
        return self._has_export_data()

    def _has_export_data(self) -> bool:
        for root in self._export_dirs():
            if (root / "boards.csv").exists():
                return True
        return False

    def _export_dirs(self) -> list[Path]:
        roots = [
            Path(__file__).resolve().parent.parent / "plugins" / "ths_export",
            Path(os.environ.get("THS_EXPORT_DIR") or ""),
        ]
        return [p for p in roots if p and p.is_dir()]

    def _get_json(self, url: str, params: dict | None = None, timeout: float = 12.0) -> Any:
        resp = self.session.get(url, params=params or {}, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def fetch_hot_plates(self, kind: str) -> list[Board]:
        """kind: concept | industry"""
        payload = self._get_json(HOT_PLATE_URL, {"type": kind})
        plates = ((payload or {}).get("data") or {}).get("plate_list") or []
        boards: list[Board] = []
        for row in plates:
            code = str(row.get("code") or "").strip()
            name = str(row.get("name") or "").strip()
            if not code or not name:
                continue
            boards.append(
                Board(
                    code=f"THS{code}",
                    name=name,
                    kind="concept" if kind == "concept" else "industry",
                    change_percent=_f(row.get("rise_and_fall")),
                    up_count=8,  # 热榜无家数，给策略门槛一个合理默认
                    down_count=2,
                    source=self.name,
                )
            )
        return boards

    def fetch_block_top(self) -> tuple[list[Board], dict[str, list[Stock]], dict[str, LimitUpInfo]]:
        payload = self._get_json(BLOCK_TOP_URL, {"page": 1, "limit": 30})
        rows = (payload or {}).get("data") or []
        boards: list[Board] = []
        stocks_by_board: dict[str, list[Stock]] = {}
        zt_by_code: dict[str, LimitUpInfo] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get("code") or "").strip()
            name = str(row.get("name") or "").strip()
            if not code or not name:
                continue
            bcode = f"THS{code}"
            limit_up_num = int(_f(row.get("limit_up_num")) or 0)
            boards.append(
                Board(
                    code=bcode,
                    name=name,
                    kind="concept",
                    change_percent=_f(row.get("change")),
                    up_count=max(limit_up_num, 4),
                    down_count=0,
                    source=self.name,
                )
            )
            stocks: list[Stock] = []
            for s in row.get("stock_list") or []:
                scode = str(s.get("code") or "").strip()
                sname = str(s.get("name") or scode).strip()
                if not scode:
                    continue
                if int(s.get("is_st") or 0) == 1:
                    continue
                pct = _f(s.get("change_rate"))
                price = _f(s.get("latest"))
                cont = int(_f(s.get("continue_num")) or 1)
                fbt = _unix_to_hhmmss(s.get("first_limit_up_time"))
                stocks.append(
                    Stock(
                        code=scode,
                        name=sname,
                        price=price,
                        change_percent=pct,
                        board_code=bcode,
                        board_name=name,
                        source=self.name,
                    )
                )
                # 涨停池信息（板块成分多为涨停股）
                if pct is not None and pct >= 9.5:
                    zt_by_code[scode] = LimitUpInfo(
                        code=scode,
                        name=sname,
                        first_seal_time=fbt,
                        consecutive_boards=max(cont, 1),
                        seal_amount=None,
                        open_count=0,
                        industry=name,
                    )
            stocks_by_board[bcode] = stocks
        return boards, stocks_by_board, zt_by_code

    def fetch_zt_pool(self) -> tuple[str, dict[str, LimitUpInfo]]:
        payload = self._get_json(ZT_POOL_URL, {"page": 1, "limit": 100, "filter": "HS,GEM2STAR"})
        data = (payload or {}).get("data") or {}
        date = str(data.get("date") or beijing_ymd())
        zt: dict[str, LimitUpInfo] = {}
        for row in data.get("info") or []:
            code = str(row.get("code") or "").strip()
            name = str(row.get("name") or code).strip()
            if not code:
                continue
            zt[code] = LimitUpInfo(
                code=code,
                name=name,
                first_seal_time=0,
                consecutive_boards=1,
                open_count=0,
            )
        return date, zt

    def fetch_hot_stocks(self) -> list[Stock]:
        payload = self._get_json(HOT_STOCK_URL)
        rows = ((payload or {}).get("data") or {}).get("stock_list") or []
        out: list[Stock] = []
        for row in rows:
            code = str(row.get("code") or "").strip()
            name = str(row.get("name") or code).strip()
            if not code:
                continue
            tag = row.get("tag") or {}
            concepts = tag.get("concept_tag") if isinstance(tag, dict) else None
            board_name = None
            if isinstance(concepts, list) and concepts:
                board_name = str(concepts[0])
            out.append(
                Stock(
                    code=code,
                    name=name,
                    change_percent=_f(row.get("rise_and_fall")),
                    board_name=board_name,
                    source=self.name,
                )
            )
        return out

    def _from_export(self, trade_date: str) -> MarketSnapshot | None:
        for root in self._export_dirs():
            boards_file = root / "boards.csv"
            if not boards_file.exists():
                continue
            boards: list[Board] = []
            with boards_file.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    boards.append(
                        Board(
                            code=(row.get("code") or row.get("代码") or "").strip(),
                            name=(row.get("name") or row.get("名称") or "").strip(),
                            kind=(row.get("kind") or row.get("类型") or "concept").strip(),
                            change_percent=_f(row.get("change_percent") or row.get("涨幅")),
                            amount=_f(row.get("amount") or row.get("成交额")),
                            main_net_inflow=_f(row.get("main_net_inflow") or row.get("主力净流入")),
                            up_count=int(_f(row.get("up_count") or row.get("上涨家数")) or 0),
                            down_count=int(_f(row.get("down_count") or row.get("下跌家数")) or 0),
                            source=self.name,
                        )
                    )
            stocks_by_board: dict[str, list[Stock]] = {}
            for b in boards:
                mf = root / f"members_{b.code}.csv"
                if not mf.exists():
                    continue
                with mf.open(encoding="utf-8-sig", newline="") as f:
                    stocks_by_board[b.code] = [
                        Stock(
                            code=(row.get("code") or row.get("代码") or "").strip(),
                            name=(row.get("name") or row.get("名称") or "").strip(),
                            price=_f(row.get("price") or row.get("现价")),
                            change_percent=_f(row.get("change_percent") or row.get("涨幅")),
                            amount=_f(row.get("amount") or row.get("成交额")),
                            board_code=b.code,
                            board_name=b.name,
                            source=self.name,
                        )
                        for row in csv.DictReader(f)
                    ]
            zt_by_code: dict[str, LimitUpInfo] = {}
            zt_file = root / "zt.csv"
            if zt_file.exists():
                with zt_file.open(encoding="utf-8-sig", newline="") as f:
                    for row in csv.DictReader(f):
                        code = (row.get("code") or row.get("代码") or "").strip()
                        if not code:
                            continue
                        zt_by_code[code] = LimitUpInfo(
                            code=code,
                            name=(row.get("name") or row.get("名称") or code).strip(),
                            first_seal_time=int(_f(row.get("first_seal_time") or row.get("首次封板")) or 0),
                            consecutive_boards=int(_f(row.get("consecutive_boards") or row.get("连板")) or 1),
                            seal_amount=_f(row.get("seal_amount") or row.get("封单额")),
                            open_count=int(_f(row.get("open_count") or row.get("开板次数")) or 0),
                        )
            return MarketSnapshot(
                trade_date=trade_date,
                source=self.name,
                boards=boards,
                stocks_by_board=stocks_by_board,
                zt_by_code=zt_by_code,
                notes=[f"同花顺导出目录 {root}"],
            )
        return None

    def fetch_snapshot(self, trade_date: str | None = None) -> MarketSnapshot:
        date = trade_date or beijing_ymd()
        try:
            with ThreadPoolExecutor(max_workers=4) as pool:
                f_block = pool.submit(self.fetch_block_top)
                f_zt = pool.submit(self.fetch_zt_pool)
                f_concept = pool.submit(self.fetch_hot_plates, "concept")
                f_industry = pool.submit(self.fetch_hot_plates, "industry")
                block_boards, stocks_by_board, zt_from_block = f_block.result()
                zt_date, zt_pool = f_zt.result()
                hot_boards = f_concept.result() + f_industry.result()

            # 合并板块：涨停板块榜优先（含成分），热榜补强
            board_map = {b.code: b for b in hot_boards}
            for b in block_boards:
                board_map[b.code] = b
            boards = list(board_map.values())

            # 热榜板块若无成分，用热股里挂同概念名的股票填充
            hot_stocks = self.fetch_hot_stocks()
            for b in boards:
                if b.code in stocks_by_board and stocks_by_board[b.code]:
                    continue
                matched = [s for s in hot_stocks if s.board_name and b.name in s.board_name]
                if matched:
                    for s in matched:
                        s.board_code = b.code
                        s.board_name = b.name
                        # 热股无涨幅时给观察门槛一个占位，避免被策略全滤掉
                        if s.change_percent is None:
                            s.change_percent = b.change_percent
                    stocks_by_board[b.code] = matched

            zt_by_code = {**zt_pool, **zt_from_block}
            return MarketSnapshot(
                trade_date=str(zt_date or date),
                source=self.name,
                boards=boards,
                stocks_by_board=stocks_by_board,
                zt_by_code=zt_by_code,
                notes=[
                    "同花顺免费公开接口：涨停板块榜 + 热门概念/行业 + 热股",
                    "无需 API Key",
                ],
            )
        except Exception as exc:
            offline = self._from_export(date)
            if offline:
                offline.notes.append(f"在线接口失败，已回退导出：{exc}")
                return offline
            raise RuntimeError(f"同花顺免费数据源不可用：{exc}") from exc

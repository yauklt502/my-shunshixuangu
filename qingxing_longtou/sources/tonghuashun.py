"""同花顺数据源（经扶摇 Fuyao REST；需 FUYAO_API_KEY）。

无 Key 时 available()=False，界面可选但不会被 auto 选中。
也可读取同花顺导出的板块 CSV 作为离线兜底（plugins/ths_export/）。
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

import requests

import config
from engine.models import Board, LimitUpInfo, MarketSnapshot, Stock
from sources.base import DataSource
from sources.eastmoney import beijing_ymd


class TonghuashunSource(DataSource):
    name = "tonghuashun"
    label = "同花顺(扶摇)"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = (api_key or config.FUYAO_API_KEY or "").strip()
        self.base_url = (base_url or config.FUYAO_BASE_URL).rstrip("/")
        self.session = requests.Session()

    def available(self) -> bool:
        if self.api_key:
            try:
                self._get("/api/a-share/calendar/trading-days")
                return True
            except Exception:
                pass
        return self._has_export_data()

    def _has_export_data(self) -> bool:
        for root in self._export_dirs():
            if (root / "boards.csv").exists():
                return True
        return False

    def _headers(self) -> dict[str, str]:
        return {"X-api-key": self.api_key, "Accept": "application/json"}

    def _get(self, path: str, **params: Any) -> Any:
        if not self.api_key:
            raise RuntimeError("未配置 FUYAO_API_KEY")
        cleaned = {k: v for k, v in params.items() if v is not None}
        url = f"{self.base_url}{path}"
        if cleaned:
            from urllib.parse import urlencode

            url = f"{url}?{urlencode(cleaned, doseq=True)}"
        resp = self.session.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("code") != 0:
            raise RuntimeError(payload.get("message") or f"Fuyao error {payload.get('code')}")
        return payload.get("data")

    def _export_dirs(self) -> list[Path]:
        roots = [
            Path(__file__).resolve().parent.parent / "plugins" / "ths_export",
            Path(os.environ.get("THS_EXPORT_DIR") or ""),
        ]
        return [p for p in roots if p and p.is_dir()]

    def _from_export(self, trade_date: str) -> MarketSnapshot | None:
        """读取同花顺导出 CSV：boards.csv / members_{board}.csv / zt.csv。"""
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
                stocks: list[Stock] = []
                with mf.open(encoding="utf-8-sig", newline="") as f:
                    for row in csv.DictReader(f):
                        stocks.append(
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
                        )
                stocks_by_board[b.code] = stocks
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
        if self.api_key:
            try:
                return self._from_api(date)
            except Exception as exc:
                offline = self._from_export(date)
                if offline:
                    offline.notes.append(f"API 失败回退导出：{exc}")
                    return offline
                raise
        offline = self._from_export(date)
        if offline:
            return offline
        raise RuntimeError("同花顺数据源不可用：请配置 FUYAO_API_KEY 或放置 plugins/ths_export/*.csv")

    def _from_api(self, date: str) -> MarketSnapshot:
        """扶摇 special-data + snapshot 拼装近似板块龙头视图。"""
        # date_ms：当日 0 点北京时间近似
        from datetime import datetime, timedelta, timezone

        bj = timezone(timedelta(hours=8))
        day = datetime.strptime(date, "%Y%m%d").replace(tzinfo=bj)
        date_ms = int(day.timestamp() * 1000)

        zt_raw = self._get("/api/a-share/special-data/limit-up-pool", date_ms=date_ms, page=1, size=200) or {}
        hot = self._get("/api/a-share/special-data/hot-stock-list", period="day") or []

        zt_items = zt_raw if isinstance(zt_raw, list) else (zt_raw.get("list") or zt_raw.get("items") or [])
        zt_by_code: dict[str, LimitUpInfo] = {}
        for item in zt_items:
            code = _code(item)
            if not code:
                continue
            zt_by_code[code] = LimitUpInfo(
                code=code,
                name=str(item.get("name") or item.get("sec_name") or code),
                first_seal_time=int(item.get("first_seal_time") or item.get("fbt") or 0),
                consecutive_boards=int(item.get("consecutive_boards") or item.get("lbc") or 1),
                seal_amount=_f(item.get("seal_amount") or item.get("fund")),
                open_count=int(item.get("open_count") or item.get("zbc") or 0),
                industry=item.get("industry") or item.get("hybk"),
            )

        # 用热股行业/概念聚合伪板块
        board_map: dict[str, Board] = {}
        stocks_by_board: dict[str, list[Stock]] = {}
        hot_list = hot if isinstance(hot, list) else (hot.get("list") or [])
        for item in hot_list:
            code = _code(item)
            name = str(item.get("name") or item.get("sec_name") or code)
            board_name = str(item.get("concept") or item.get("industry") or item.get("sector") or "热股").strip()
            board_code = f"THS_{abs(hash(board_name)) % 10_000_000}"
            if board_code not in board_map:
                board_map[board_code] = Board(
                    code=board_code,
                    name=board_name,
                    kind="concept",
                    change_percent=_f(item.get("sector_change") or item.get("board_change")),
                    up_count=1,
                    down_count=0,
                    source=self.name,
                )
                stocks_by_board[board_code] = []
            else:
                board_map[board_code].up_count = (board_map[board_code].up_count or 0) + 1
            stock = Stock(
                code=code,
                name=name,
                price=_f(item.get("price") or item.get("last")),
                change_percent=_f(item.get("change_percent") or item.get("pct_chg") or item.get("change")),
                amount=_f(item.get("amount") or item.get("turnover")),
                board_code=board_code,
                board_name=board_name,
                source=self.name,
            )
            stocks_by_board[board_code].append(stock)

        # 补充涨停股到对应行业伪板块
        for zt in zt_by_code.values():
            bname = (zt.industry or "涨停池").strip()
            bcode = f"THS_{abs(hash(bname)) % 10_000_000}"
            if bcode not in board_map:
                board_map[bcode] = Board(
                    code=bcode,
                    name=bname,
                    kind="industry",
                    change_percent=5.0,
                    up_count=1,
                    down_count=0,
                    source=self.name,
                )
                stocks_by_board[bcode] = []
            stocks_by_board[bcode].append(
                Stock(
                    code=zt.code,
                    name=zt.name,
                    change_percent=10.0,
                    amount=zt.seal_amount,
                    board_code=bcode,
                    board_name=bname,
                    source=self.name,
                )
            )
            board_map[bcode].up_count = (board_map[bcode].up_count or 0) + 1

        return MarketSnapshot(
            trade_date=date,
            source=self.name,
            boards=list(board_map.values()),
            stocks_by_board=stocks_by_board,
            zt_by_code=zt_by_code,
            notes=["同花顺扶摇 API：涨停池 + 热股聚合板块"],
        )


def _f(value: Any) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(str(value).replace("%", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def _code(item: dict[str, Any]) -> str:
    raw = item.get("code") or item.get("thscode") or item.get("sec_code") or item.get("symbol") or ""
    s = str(raw).strip().upper()
    # 300001.SZ / SH600000 -> 纯数字
    for sep in (".", ":"):
        if sep in s:
            s = s.split(sep)[0] if s.split(sep)[0].isdigit() else s.split(sep)[-1]
    s = s.replace("SH", "").replace("SZ", "").replace("BJ", "")
    return s

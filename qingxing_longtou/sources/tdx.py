"""通达信 (TDX) 数据源。

支持三种接入方式（按优先级）：
1. 第三方插件导出目录 plugins/tdx/export/*.csv（推荐，跨平台）
2. 本地通达信安装目录下的板块/自定义板块文本（Windows TDX_HOME）
3. 插件协议占位：plugins/tdx/plugin_bridge.py 可对接 DLL/HTTP 插件

CSV 约定见 plugins/tdx/README.md
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

import config
from engine.models import Board, LimitBreakInfo, LimitUpInfo, MarketSnapshot, Stock
from sources.base import DataSource
from sources.eastmoney import beijing_ymd


class TdxSource(DataSource):
    name = "tdx"
    label = "通达信(插件/本地)"

    def __init__(self, tdx_home: str | None = None, export_dir: Path | None = None) -> None:
        self.tdx_home = Path(tdx_home or config.TDX_HOME).expanduser() if (tdx_home or config.TDX_HOME) else None
        self.export_dir = export_dir or (Path(__file__).resolve().parent.parent / "plugins" / "tdx" / "export")

    def available(self) -> bool:
        if self.export_dir.is_dir() and (self.export_dir / "boards.csv").exists():
            return True
        if self.tdx_home and self.tdx_home.is_dir():
            return True
        endpoint = __import__("os").environ.get("TDX_PLUGIN_URL", "").strip()
        return bool(endpoint)

    def fetch_snapshot(self, trade_date: str | None = None) -> MarketSnapshot:
        date = trade_date or beijing_ymd()
        if self.export_dir.is_dir() and (self.export_dir / "boards.csv").exists():
            return self._from_export(date)
        if self.tdx_home and self.tdx_home.is_dir():
            snap = self._from_local_blocks(date)
            if snap.boards:
                return snap
        # 尝试插件桥
        try:
            from plugins.tdx import plugin_bridge

            data = plugin_bridge.fetch_market_bundle(date)
            if data:
                return self._from_bridge(date, data)
        except Exception as exc:
            raise RuntimeError(
                "通达信数据源无可用数据。请将插件导出 CSV 放到 plugins/tdx/export/，"
                f"或设置 TDX_HOME。详情：{exc}"
            ) from exc
        raise RuntimeError("通达信数据源无可用数据。请配置 plugins/tdx/export/boards.csv 或 TDX_HOME")

    def _from_export(self, date: str) -> MarketSnapshot:
        root = self.export_dir
        boards: list[Board] = []
        with (root / "boards.csv").open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                boards.append(
                    Board(
                        code=_cell(row, "code", "代码", "板块代码"),
                        name=_cell(row, "name", "名称", "板块名称"),
                        kind=_cell(row, "kind", "类型") or "concept",
                        change_percent=_f(_cell(row, "change_percent", "涨幅", "涨跌幅")),
                        amount=_f(_cell(row, "amount", "成交额")),
                        main_net_inflow=_f(_cell(row, "main_net_inflow", "主力净流入")),
                        up_count=int(_f(_cell(row, "up_count", "上涨家数")) or 0),
                        down_count=int(_f(_cell(row, "down_count", "下跌家数")) or 0),
                        source=self.name,
                    )
                )
        stocks_by_board: dict[str, list[Stock]] = {}
        members_all = root / "members.csv"
        if members_all.exists():
            with members_all.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    bcode = _cell(row, "board_code", "板块代码")
                    stock = Stock(
                        code=_cell(row, "code", "代码"),
                        name=_cell(row, "name", "名称"),
                        price=_f(_cell(row, "price", "现价")),
                        change_percent=_f(_cell(row, "change_percent", "涨幅", "涨跌幅")),
                        amount=_f(_cell(row, "amount", "成交额")),
                        board_code=bcode,
                        board_name=_cell(row, "board_name", "板块名称"),
                        source=self.name,
                    )
                    stocks_by_board.setdefault(bcode, []).append(stock)
        else:
            for b in boards:
                mf = root / f"members_{b.code}.csv"
                if not mf.exists():
                    continue
                with mf.open(encoding="utf-8-sig", newline="") as f:
                    stocks_by_board[b.code] = [
                        Stock(
                            code=_cell(row, "code", "代码"),
                            name=_cell(row, "name", "名称"),
                            price=_f(_cell(row, "price", "现价")),
                            change_percent=_f(_cell(row, "change_percent", "涨幅")),
                            amount=_f(_cell(row, "amount", "成交额")),
                            board_code=b.code,
                            board_name=b.name,
                            source=self.name,
                        )
                        for row in csv.DictReader(f)
                    ]

        zt_by_code: dict[str, LimitUpInfo] = {}
        zb_by_code: dict[str, LimitBreakInfo] = {}
        zt_path = root / "zt.csv"
        if zt_path.exists():
            with zt_path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    code = _cell(row, "code", "代码")
                    if not code:
                        continue
                    zt_by_code[code] = LimitUpInfo(
                        code=code,
                        name=_cell(row, "name", "名称") or code,
                        first_seal_time=int(_f(_cell(row, "first_seal_time", "首次封板", "封板时间")) or 0),
                        consecutive_boards=int(_f(_cell(row, "consecutive_boards", "连板")) or 1),
                        seal_amount=_f(_cell(row, "seal_amount", "封单额")),
                        open_count=int(_f(_cell(row, "open_count", "开板次数")) or 0),
                    )
        zb_path = root / "zb.csv"
        if zb_path.exists():
            with zb_path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    code = _cell(row, "code", "代码")
                    if not code:
                        continue
                    zb_by_code[code] = LimitBreakInfo(
                        code=code,
                        name=_cell(row, "name", "名称") or code,
                        first_seal_time=int(_f(_cell(row, "first_seal_time", "首次封板")) or 0),
                        open_count=int(_f(_cell(row, "open_count", "开板次数")) or 1),
                        change_percent=_f(_cell(row, "change_percent", "涨幅")),
                    )
        return MarketSnapshot(
            trade_date=date,
            source=self.name,
            boards=boards,
            stocks_by_board=stocks_by_board,
            zt_by_code=zt_by_code,
            zb_by_code=zb_by_code,
            notes=[f"通达信导出 {root}"],
        )

    def _from_local_blocks(self, date: str) -> MarketSnapshot:
        """读取通达信自定义板块 .blk（仅代码列表，行情需另接）。"""
        assert self.tdx_home is not None
        blocknew = self.tdx_home / "T0002" / "blocknew"
        boards: list[Board] = []
        stocks_by_board: dict[str, list[Stock]] = {}
        if not blocknew.is_dir():
            return MarketSnapshot(trade_date=date, source=self.name, notes=["未找到 T0002/blocknew"])

        for blk in sorted(blocknew.glob("*.blk"))[:30]:
            codes = _parse_blk(blk.read_bytes())
            if not codes:
                continue
            bcode = blk.stem
            bname = blk.stem
            boards.append(
                Board(
                    code=bcode,
                    name=bname,
                    kind="concept",
                    up_count=len(codes),
                    down_count=0,
                    change_percent=0.0,
                    source=self.name,
                )
            )
            stocks_by_board[bcode] = [
                Stock(code=c, name=c, board_code=bcode, board_name=bname, change_percent=0.0, source=self.name)
                for c in codes
            ]
        return MarketSnapshot(
            trade_date=date,
            source=self.name,
            boards=boards,
            stocks_by_board=stocks_by_board,
            notes=[
                f"已读取本地板块 {len(boards)} 个，但 .blk 仅含代码。"
                "请用第三方插件导出带行情的 CSV 以获得完整选股。"
            ],
        )

    def _from_bridge(self, date: str, data: dict[str, Any]) -> MarketSnapshot:
        boards = [
            Board(
                code=str(b["code"]),
                name=str(b["name"]),
                kind=str(b.get("kind") or "concept"),
                change_percent=_f(b.get("change_percent")),
                amount=_f(b.get("amount")),
                main_net_inflow=_f(b.get("main_net_inflow")),
                up_count=int(b.get("up_count") or 0),
                down_count=int(b.get("down_count") or 0),
                source=self.name,
            )
            for b in data.get("boards") or []
        ]
        stocks_by_board: dict[str, list[Stock]] = {}
        for bcode, rows in (data.get("stocks_by_board") or {}).items():
            stocks_by_board[bcode] = [
                Stock(
                    code=str(s["code"]),
                    name=str(s.get("name") or s["code"]),
                    price=_f(s.get("price")),
                    change_percent=_f(s.get("change_percent")),
                    amount=_f(s.get("amount")),
                    board_code=bcode,
                    source=self.name,
                )
                for s in rows
            ]
        return MarketSnapshot(
            trade_date=date,
            source=self.name,
            boards=boards,
            stocks_by_board=stocks_by_board,
            notes=["通达信第三方插件桥接"],
        )


def _cell(row: dict[str, str], *keys: str) -> str:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return str(row[k]).strip()
    # 兼容大小写
    lower = {str(k).lower(): v for k, v in row.items()}
    for k in keys:
        if k.lower() in lower and lower[k.lower()] not in (None, ""):
            return str(lower[k.lower()]).strip()
    return ""


def _f(value: Any) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(str(value).replace("%", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def _parse_blk(raw: bytes) -> list[str]:
    """通达信 .blk 常见为每 7 字节：市场1位+代码6位。"""
    codes: list[str] = []
    if len(raw) % 7 == 0 and len(raw) > 0:
        for i in range(0, len(raw), 7):
            chunk = raw[i : i + 7]
            code = chunk[1:7].decode("ascii", errors="ignore")
            if re.fullmatch(r"\d{6}", code):
                codes.append(code)
        if codes:
            return codes
    # 文本回退
    text = raw.decode("gbk", errors="ignore")
    return re.findall(r"\b\d{6}\b", text)

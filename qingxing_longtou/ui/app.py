"""清醒龙头战法 · 桌面选股界面。"""

from __future__ import annotations

import csv
import sys
import threading
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from engine.models import Candidate
from engine.strategy import StrategyParams, run_strategy
from screenshot_util import grab_fullscreen, grab_window_bbox
from sources import get_source, source_status
from sources.eastmoney import beijing_ymd


ATTENTION_ORDER = {"聚焦": 0, "观察": 1, "回避": 2}

COLUMNS = (
    ("关注", 56),
    ("评级", 88),
    ("代码", 72),
    ("名称", 96),
    ("板块", 120),
    ("涨幅%", 64),
    ("现价", 64),
    ("连板", 48),
    ("封板", 72),
    ("得分", 56),
    ("标签", 160),
    ("要点", 280),
    ("弱势信号", 180),
    ("数据源", 80),
)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("清醒龙头战法 · 选股")
        self.geometry("1280x760")
        self.minsize(1024, 640)
        self.configure(bg="#f3f0e8")
        self._candidates: list[Candidate] = []
        self._busy = False
        self._build_style()
        self._build_ui()
        self.after(200, self.refresh_source_status)

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#f3f0e8")
        style.configure("TLabel", background="#f3f0e8", foreground="#1c2430", font=("Microsoft YaHei UI", 10))
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 16, "bold"), foreground="#0b3d2e")
        style.configure("Sub.TLabel", font=("Microsoft YaHei UI", 9), foreground="#5a6570")
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=6)
        style.configure("Accent.TButton", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure(
            "Treeview",
            font=("Microsoft YaHei UI", 9),
            rowheight=28,
            background="#fffdf8",
            fieldbackground="#fffdf8",
            foreground="#1c2430",
        )
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 9, "bold"), background="#dde8e1")
        style.map("Treeview", background=[("selected", "#c8e0d4")])

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=(16, 12, 16, 4))
        top.pack(fill="x")
        ttk.Label(top, text="清醒龙头战法", style="Title.TLabel").pack(side="left")
        ttk.Label(
            top,
            text="  聚焦真核心 · 看懂强弱切换 · 管理注意力与风险",
            style="Sub.TLabel",
        ).pack(side="left", padx=(8, 0))

        bar = ttk.Frame(self, padding=(16, 8))
        bar.pack(fill="x")

        ttk.Label(bar, text="数据源").pack(side="left")
        self.source_var = tk.StringVar(value=config.DEFAULT_SOURCE or "auto")
        self.source_box = ttk.Combobox(
            bar,
            textvariable=self.source_var,
            values=("auto", "eastmoney", "tonghuashun", "tdx"),
            width=14,
            state="readonly",
        )
        self.source_box.pack(side="left", padx=(6, 12))

        ttk.Label(bar, text="交易日").pack(side="left")
        self.date_var = tk.StringVar(value=beijing_ymd())
        ttk.Entry(bar, textvariable=self.date_var, width=12).pack(side="left", padx=(6, 12))

        ttk.Label(bar, text="主线板块数").pack(side="left")
        self.top_boards_var = tk.IntVar(value=config.TOP_BOARDS)
        ttk.Spinbox(bar, from_=3, to=30, textvariable=self.top_boards_var, width=5).pack(side="left", padx=(6, 12))

        self.run_btn = ttk.Button(bar, text="刷新选股", style="Accent.TButton", command=self.on_run)
        self.run_btn.pack(side="left", padx=(4, 6))
        ttk.Button(bar, text="一键截屏", command=self.on_screenshot).pack(side="left", padx=4)
        ttk.Button(bar, text="导出CSV", command=self.on_export).pack(side="left", padx=4)

        # 连接指示灯：绿=已连接，红=未连接（替代「数据源状态」五字按钮）
        lamp_frame = ttk.Frame(bar)
        lamp_frame.pack(side="left", padx=(10, 4))
        self._source_lamp = tk.Canvas(lamp_frame, width=18, height=18, highlightthickness=0, bg="#f3f0e8")
        self._source_lamp.pack(side="left")
        self._lamp_id = self._source_lamp.create_oval(2, 2, 16, 16, fill="#c0392b", outline="#7f1d1d")
        self._lamp_label = ttk.Label(lamp_frame, text="未连接", style="Sub.TLabel")
        self._lamp_label.pack(side="left", padx=(4, 0))
        self._source_lamp.bind("<Button-1>", lambda _e: self.refresh_source_status())
        self._lamp_label.bind("<Button-1>", lambda _e: self.refresh_source_status())

        self.status_var = tk.StringVar(value="就绪。东方财富 / 同花顺(免费公开) / 通达信均可选，无需付费 Key。")
        ttk.Label(self, textvariable=self.status_var, style="Sub.TLabel", padding=(16, 0)).pack(fill="x")

        theory = ttk.Frame(self, padding=(16, 6))
        theory.pack(fill="x")
        self.theory_var = tk.StringVar(
            value=(
                "规则摘要：①谁满足观察条件再研究 ②不替市场提前下结论 ③核心该强不强→结构失效/资金换向 "
                "④优先全局带动性，勿把局部热闹当中心 ⑤看懂弱势 ⑥接受回撤 ⑦交易的清醒=管理注意力"
            )
        )
        ttk.Label(theory, textvariable=self.theory_var, style="Sub.TLabel", wraplength=1200).pack(fill="x")

        table_frame = ttk.Frame(self, padding=(12, 4, 12, 12))
        table_frame.pack(fill="both", expand=True)
        cols = [c[0] for c in COLUMNS]
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        for name, width in COLUMNS:
            self.tree.heading(name, text=name)
            anchor = "w" if name in ("名称", "板块", "标签", "要点", "弱势信号") else "center"
            self.tree.column(name, width=width, anchor=anchor, stretch=(name in ("要点", "弱势信号", "标签")))
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.tag_configure("聚焦", background="#d8f0e2")
        self.tree.tag_configure("观察", background="#fff8e8")
        self.tree.tag_configure("回避", background="#f5e4e0")

        foot = ttk.Frame(self, padding=(16, 0, 16, 10))
        foot.pack(fill="x")
        ttk.Label(
            foot,
            text="免责声明：内容供学习研究，不构成任何投资建议。数据来自第三方接口/本地插件导出，可能延迟或缺失。",
            style="Sub.TLabel",
        ).pack(side="left")

    def refresh_source_status(self) -> None:
        try:
            rows = source_status()
            ok_any = any(bool(r.get("available")) for r in rows)
            text = " | ".join(
                f"{r['label']}:{'OK' if r['available'] else '—'}" for r in rows
            )
            self.status_var.set(text)
            # 绿=有可用源，红=全部不可用
            if ok_any:
                self._source_lamp.itemconfig(self._lamp_id, fill="#1a7f37", outline="#0b3d2e")
                self._lamp_label.configure(text="已连接")
            else:
                self._source_lamp.itemconfig(self._lamp_id, fill="#c0392b", outline="#7f1d1d")
                self._lamp_label.configure(text="未连接")
        except Exception as exc:
            self.status_var.set(f"状态检查失败：{exc}")
            self._source_lamp.itemconfig(self._lamp_id, fill="#c0392b", outline="#7f1d1d")
            self._lamp_label.configure(text="未连接")

    def on_run(self) -> None:
        if self._busy:
            return
        self._busy = True
        self.run_btn.configure(state="disabled")
        self.status_var.set("正在拉取行情并计算……")
        src_name = self.source_var.get()
        trade_date = self.date_var.get().strip() or beijing_ymd()
        params = StrategyParams(top_boards=int(self.top_boards_var.get()))

        def worker() -> None:
            err: str | None = None
            candidates: list[Candidate] = []
            note = ""
            try:
                source = get_source(src_name)
                snap = source.fetch_snapshot(trade_date)
                candidates = run_strategy(snap, params)
                note = (
                    f"完成 · 源={source.label} · 日={snap.trade_date} · "
                    f"板块{len(snap.boards)} · 涨停{len(snap.zt_by_code)} · 候选{len(candidates)}"
                )
                if snap.notes:
                    note += " · " + "；".join(snap.notes[:2])
            except Exception as exc:
                err = f"{exc}\n{traceback.format_exc()}"
            self.after(0, lambda: self._on_run_done(candidates, note, err))

        threading.Thread(target=worker, daemon=True).start()

    def _on_run_done(self, candidates: list[Candidate], note: str, err: str | None) -> None:
        self._busy = False
        self.run_btn.configure(state="normal")
        if err:
            self.status_var.set("选股失败")
            messagebox.showerror("选股失败", err[:2000])
            return
        self._candidates = sorted(
            candidates,
            key=lambda c: (ATTENTION_ORDER.get(c.attention, 9), -c.score),
        )
        self._fill_table(self._candidates)
        self.status_var.set(note)

    def _fill_table(self, rows: list[Candidate]) -> None:
        self.tree.delete(*self.tree.get_children())
        for c in rows:
            row = c.to_row()
            values = [row.get(col[0], "") for col in COLUMNS]
            self.tree.insert("", "end", values=values, tags=(c.attention,))

    def on_screenshot(self) -> None:
        self.update_idletasks()
        try:
            # 优先截主窗口；Linux 无 DISPLAY 时降级提示
            left = self.winfo_rootx()
            top = self.winfo_rooty()
            right = left + self.winfo_width()
            bottom = top + self.winfo_height()
            path = grab_window_bbox(left, top, right, bottom)
            self.status_var.set(f"截屏已保存：{path}")
            messagebox.showinfo("一键截屏", f"已保存到\n{path}")
        except Exception as exc:
            try:
                path = grab_fullscreen()
                self.status_var.set(f"窗口截取失败，已保存全屏：{path}")
                messagebox.showinfo("一键截屏", f"窗口截取失败，已保存全屏到\n{path}\n\n原因：{exc}")
            except Exception as exc2:
                messagebox.showerror("截屏失败", f"{exc2}\n\n提示：无图形界面时请在本机桌面运行。")

    def on_export(self) -> None:
        if not self._candidates:
            messagebox.showwarning("导出", "暂无结果，请先刷新选股。")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"qingxing_longtou_{beijing_ymd()}.csv",
        )
        if not path:
            return
        fieldnames = [c[0] for c in COLUMNS]
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for c in self._candidates:
                writer.writerow(c.to_row())
        self.status_var.set(f"已导出 {path}")


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

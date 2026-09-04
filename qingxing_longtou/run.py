#!/usr/bin/env python3
"""启动清醒龙头战法选股软件（带错误捕获，避免闪退）。"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
LOG = ROOT / "start_log.txt"


def _write_log(msg: str) -> None:
    try:
        LOG.write_text(msg, encoding="utf-8")
    except Exception:
        pass


def _show_error(title: str, msg: str) -> None:
    print(msg, file=sys.stderr)
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, msg[:1500])
        root.destroy()
    except Exception:
        pass


def main() -> int:
    try:
        from ui.app import main as app_main

        app_main()
        return 0
    except Exception:
        tb = traceback.format_exc()
        _write_log(tb)
        _show_error(
            "清醒龙头战法 · 启动失败",
            "程序启动失败，详情已写入 start_log.txt\n\n" + tb,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

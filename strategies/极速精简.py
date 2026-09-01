# -*- coding: utf-8 -*-
"""已并入「趋势稳健少」。旧快捷方式仍可用。"""
import runpy
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "趋势稳健少.py"
print("本脚本已合并到 趋势稳健少.py（最多 3 只、量比≥1.2、持有 3–5 日、无票空仓）。正在转发…\n")
runpy.run_path(str(_TARGET), run_name="__main__")

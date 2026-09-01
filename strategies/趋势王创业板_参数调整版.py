# -*- coding: utf-8 -*-
"""已并入「创业板放宽版」。旧快捷方式仍可用。"""
import runpy
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "趋势王创业板_放宽版.py"
print("本脚本已合并到 趋势王创业板_放宽版.py（去掉 MA5、扫全部 300 开头、最多 8 只）。正在转发…\n")
runpy.run_path(str(_TARGET), run_name="__main__")

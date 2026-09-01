# -*- coding: utf-8 -*-
"""已并入「主板妖龙优化」。旧快捷方式仍可用。"""
import runpy
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "主板妖龙优化.py"
print("本脚本已合并到 主板妖龙优化.py（红灯空仓 + 只做隔夜，不再单独维护优化1）。正在转发…\n")
runpy.run_path(str(_TARGET), run_name="__main__")

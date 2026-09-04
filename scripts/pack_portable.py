#!/usr/bin/env python3
"""打包「顺势竞价」本机部署 zip，供下载解压即用。"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "release" / "顺势竞价选股"
OUT = ROOT / "deploy" / "顺势竞价选股-本机版.zip"
ARTIFACT = Path("/opt/cursor/artifacts/顺势竞价选股-本机版.zip")

INCLUDE_DIRS = [
    "app",
    "auction_screener",
    "formulas",
    "docs",
    "scripts",
    "tests",
    "results",
]
INCLUDE_FILES = [
    "README.md",
    "requirements.txt",
    "启动选股.bat",
    "启动选股.sh",
]

START_BAT = r"""@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 顺势竞价选股

echo.
echo  ========================================
echo   顺势竞价 · 本机选股软件
echo   浏览器将打开 http://127.0.0.1:8787/
echo  ========================================
echo.

where python >nul 2>&1
if %errorlevel%==0 (
  set "PY=python"
  goto :havepy
)
where py >nul 2>&1
if %errorlevel%==0 (
  set "PY=py -3"
  goto :havepy
)

echo [错误] 未找到 Python 3
echo 请先安装: https://www.python.org/downloads/
echo 安装时务必勾选 Add python.exe to PATH
start https://www.python.org/downloads/
pause
exit /b 1

:havepy
if not exist ".venv\Scripts\python.exe" (
  echo 正在创建虚拟环境 .venv ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo 创建虚拟环境失败
    pause
    exit /b 1
  )
)

set "VPY=.venv\Scripts\python.exe"
set "VPIP=.venv\Scripts\pip.exe"

echo 检查依赖...
"%VPY%" -c "import urllib.request" >nul 2>&1
"%VPIP%" install -q -r requirements.txt
if errorlevel 1 (
  echo 依赖安装失败，请检查网络后重试
  pause
  exit /b 1
)

echo.
echo 启动中... 关闭本窗口即停止服务
echo.
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8787/"
"%VPY%" -m app --no-open --host 127.0.0.1 --port 8787
pause
"""

STOP_BAT = r"""@echo off
chcp 65001 >nul
echo 正在结束占用 8787 端口的进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8787 ^| findstr LISTENING') do (
  taskkill /F /PID %%a >nul 2>&1
)
echo 完成
pause
"""

README_TXT = """顺势竞价 · 本机选股软件
========================

一、安装（只需一次）
1. 解压本压缩包到任意目录，例如：
   D:\\顺势竞价选股\\
   或  F:\\顺势竞价选股\\
2. 安装 Python 3.10+：
   https://www.python.org/downloads/
   ★ 安装时勾选「Add python.exe to PATH」
3. 双击「启动选股.bat」
   首次会自动创建 .venv 并安装依赖（需联网）

二、每天使用
1. 双击 启动选股.bat
2. 浏览器打开 http://127.0.0.1:8787/
3. 左侧选策略：
   - 连板优化
   - 胜率100%（开盘后挂 +0.8% 止盈）
   - 原版公式
4. 9:15–9:30 用「盘前盯盘」；9:25 后用「扫描选股」

三、停止
- 关闭黑色命令行窗口
- 或双击 停止选股.bat

四、注意
- 必须用 bat 启动，不要直接双击打开 html（file:// 会跨域失败）
- 需要能访问东方财富 / 新浪行情（普通宽带即可）
- 研究笔记，不构成投资建议

五、目录说明
  app/              选股软件界面与接口
  auction_screener/ 选股规则引擎
  formulas/         问财 / 通达信公式
  results/          回测报告
  docs/             优化说明
  scripts/          命令行扫描 / 回测脚本
"""

START_SH = r"""#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "顺势竞价 · http://127.0.0.1:8787/"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
(sleep 1; command -v xdg-open >/dev/null && xdg-open http://127.0.0.1:8787/ || true) &
python -m app --no-open --host 127.0.0.1 --port 8787
"""


def _should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & {".venv", "__pycache__", ".pytest_cache", ".git", "node_modules"}:
        return True
    if path.suffix in {".pyc", ".pyo", ".parquet"}:
        return True
    if path.name in {"lianban_grid_ranked.csv"}:
        return True
    return False


def copy_tree(src: Path, dst: Path) -> None:
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return
    for p in src.rglob("*"):
        if _should_skip(p):
            continue
        if p.is_dir():
            continue
        rel = p.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)


def main() -> None:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    (ROOT / "deploy").mkdir(parents=True, exist_ok=True)

    for d in INCLUDE_DIRS:
        src = ROOT / d
        if src.exists():
            copy_tree(src, STAGE / d)
    for f in INCLUDE_FILES:
        src = ROOT / f
        if src.exists():
            shutil.copy2(src, STAGE / f)

    # 覆盖/补充启动文件（Windows 友好）
    (STAGE / "启动选股.bat").write_text(START_BAT.replace("\n", "\r\n"), encoding="utf-8")
    (STAGE / "停止选股.bat").write_text(STOP_BAT.replace("\n", "\r\n"), encoding="utf-8")
    (STAGE / "启动选股.sh").write_text(START_SH, encoding="utf-8")
    (STAGE / "启动选股.sh").chmod(0o755)
    (STAGE / "使用说明.txt").write_text(README_TXT.replace("\n", "\r\n"), encoding="utf-8")

    # 空 data 目录占位
    (STAGE / "data").mkdir(exist_ok=True)
    (STAGE / "data" / "README.txt").write_text(
        "可选：运行 scripts/download_backtest_data.py 下载回测行情。\r\n选股软件本身不依赖此目录。\r\n",
        encoding="utf-8",
    )

    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for p in STAGE.rglob("*"):
            if p.is_file():
                z.write(p, arcname=str(Path("顺势竞价选股") / p.relative_to(STAGE)))

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT, ARTIFACT)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.1f} KB)")
    print(f"artifact {ARTIFACT}")


if __name__ == "__main__":
    main()

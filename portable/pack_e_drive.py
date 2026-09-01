#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pack a copy-to-E-drive zip: portable/shunshi-xuangu-E.zip"""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "portable" / "shunshi-xuangu-E.zip"
INNER = "顺势选股"

BAT = r"""@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  顺势选股  解压到 E:\顺势选股\ 后双击本文件
echo  浏览器将打开 http://127.0.0.1:8787/
echo  点「扫描主板」或「扫描创业板」，不会扫全市场
echo.
where python >nul 2>&1
if %errorlevel%==0 set PY=python
if not defined PY (
  where py >nul 2>&1
  if %errorlevel%==0 set PY=py -3
)
if not defined PY (
  echo 未找到 Python 3。请先安装 https://www.python.org/downloads/ 并勾选 Add python.exe to PATH
  pause
  goto :eof
)
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8787/"
%PY% serve_web.py
"""

README_TXT = """拷到 E 盘

1. 把本文件夹整个复制（或解压）到 E:\\顺势选股\\
2. 安装 Python 3：https://www.python.org/downloads/  安装时勾选 Add python.exe to PATH
3. 双击 打开选股.bat
4. 浏览器打开 http://127.0.0.1:8787/
5. 点「扫描主板」或「扫描创业板」
   - 主板：600/601/603/605/000/001/002，非 ST
   - 创业板：300 开头，非 ST
   - 不扫科创板 688、北交所、301、ST/退市
   - 不会拉全市场 4000+ 行情

不要用文件协议直接打开 index.html（file://），必须走 bat 启动的本地服务，否则腾讯接口会被浏览器跨域拦住。
"""


def main() -> None:
    serve = (ROOT / "serve_web.py").read_bytes()
    html = (ROOT / "web" / "index.html").read_bytes()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{INNER}/打开选股.bat", BAT.replace("\n", "\r\n"))
        z.writestr(f"{INNER}/拷到E盘.txt", README_TXT.replace("\n", "\r\n"))
        z.writestr(f"{INNER}/serve_web.py", serve)
        z.writestr(f"{INNER}/web/index.html", html)
    print("wrote", OUT, OUT.stat().st_size)


if __name__ == "__main__":
    main()

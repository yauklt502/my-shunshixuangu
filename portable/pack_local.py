#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pack Sequoia-X local-deploy zip: portable/sequoia-x.zip"""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "portable" / "sequoia-x.zip"
INNER = "Sequoia-X"

BAT = r"""@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  Sequoia-X     http://127.0.0.1:9801/
echo  顺势选股请用原来的文件夹，地址是 http://127.0.0.1:8787/
echo  本包必须解压到独立目录，不要解压进「顺势选股」
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
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:9801/"
%PY% serve_web.py
if errorlevel 1 pause
"""

README_TXT = """Sequoia-X 本地部署

必须解压到独立文件夹，例如 D:\\Sequoia-X\\
不要解压进原来的「顺势选股」目录，否则会把那边的网页盖掉，两个都会变成 Sequoia-X。

1. 安装 Python 3：https://www.python.org/downloads/  安装时勾选 Add python.exe to PATH
2. 双击 打开Sequoia-X.bat
3. 浏览器打开 http://127.0.0.1:9801/   （页顶会显示「端口 9801」）
4. 顺势选股仍用原来的文件夹，双击那边的 打开选股.bat
   顺势选股地址：http://127.0.0.1:8787/

两套可以同时开：
  顺势选股  8787
  Sequoia-X  9801

不要用 file:// 直接打开 html。
无需 pip 安装其它包。
"""


def main() -> None:
    serve = (ROOT / "serve_web.py").read_bytes()
    html = (ROOT / "web" / "index.html").read_bytes()
    vendor = ROOT / "web" / "vendor" / "html2canvas.min.js"
    if not vendor.is_file():
        raise FileNotFoundError(vendor)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{INNER}/打开Sequoia-X.bat", BAT.replace("\n", "\r\n").encode("utf-8"))
        z.writestr(f"{INNER}/使用说明.txt", README_TXT.replace("\n", "\r\n").encode("utf-8"))
        z.writestr(f"{INNER}/serve_web.py", serve)
        z.writestr(f"{INNER}/web/index.html", html)
        z.writestr(f"{INNER}/web/vendor/html2canvas.min.js", vendor.read_bytes())
    print("wrote", OUT, OUT.stat().st_size)


if __name__ == "__main__":
    main()

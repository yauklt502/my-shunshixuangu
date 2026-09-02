#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a flat overwrite pack that restores 顺势选股 on 8787."""
from __future__ import annotations

import io
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "portable" / "shunshi-xuangu-restore.zip"
GIT_REF = "origin/cursor/strategy-backtest-analysis-2e2d:portable/shunshi-xuangu-E.zip"
INNER_OLD = "顺势选股/"

BAT = r"""@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  ======================================
echo   这是【顺势选股】  http://127.0.0.1:8787/
echo   Sequoia-X 请用另一个文件夹，地址 9801
echo  ======================================
echo.
echo  先清掉占用 8787 的旧进程...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8787 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":8787" ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1
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
if errorlevel 1 pause
"""

NOTE = """把本压缩包里的文件，解压到你现在点「打开选股」的那个文件夹，全部覆盖。

不要解压成「顺势选股/顺势选股/...」套娃。
解压后这个文件夹里应直接看到：
  打开选股.bat
  serve_web.py
  web\\index.html

然后双击 打开选股.bat。
页顶应是「顺势选股」，地址 http://127.0.0.1:8787/

Sequoia-X 必须放在另一个文件夹，地址是 9801。
"""

SERVE_PATCH_HEAD = '''def _web_root() -> Path:
    here = Path(__file__).resolve().parent
    web = here / "web"
    if (web / "index.html").is_file():
        return web
    raise SystemExit(
        "找不到 web/index.html。请把还原包解压到打开选股.bat 所在文件夹并覆盖。"
    )
'''


def _load_original() -> dict[str, bytes]:
    raw = subprocess.check_output(["git", "show", GIT_REF], cwd=str(ROOT))
    out: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for name in z.namelist():
            key = name[len(INNER_OLD) :] if name.startswith(INNER_OLD) else name
            if not key or key.endswith("/"):
                continue
            out[key] = z.read(name)
    if "web/index.html" not in out or "serve_web.py" not in out:
        raise RuntimeError(f"unexpected source zip layout: {sorted(out)}")
    return out


def _harden_serve(src: str) -> str:
    src = src.replace("\r\n", "\n")
    src = src.replace(
        """def _web_root() -> Path:
    here = Path(__file__).resolve().parent
    if (here / "index.html").is_file():
        return here
    web = here / "web"
    if (web / "index.html").is_file():
        return web
    return here.parent / "web"
""",
        SERVE_PATCH_HEAD,
    )
    src = src.replace(
        """if __name__ == "__main__":
    port = 8787
    print(f"打开 http://127.0.0.1:{port}/")
    print(f"页面目录 {ROOT}")
    print("点「扫描主板」或「扫描创业板」，只扫该板块非 ST，不会扫全市场。")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
""",
        """class Server(ThreadingHTTPServer):
    allow_reuse_address = False


if __name__ == "__main__":
    import sys
    html = (ROOT / "index.html").read_text(encoding="utf-8", errors="ignore")
    if "Sequoia-X" in html:
        print("web/index.html 还是 Sequoia-X。请用还原包覆盖 web 文件夹后再打开。")
        sys.exit(1)
    if "顺势选股" not in html:
        print("web/index.html 不是顺势选股页面。")
        sys.exit(1)
    port = 8787
    print("======== 顺势选股 http://127.0.0.1:8787/ ========")
    print(f"页面目录 {ROOT}")
    try:
        httpd = Server(("127.0.0.1", port), Handler)
    except OSError:
        print("8787 仍被占用。请关掉所有黑窗口后再试。")
        sys.exit(1)
    httpd.serve_forever()
""",
    )
    if "allow_reuse_address = False" not in src:
        raise RuntimeError("failed to patch serve_web.py")
    return src


def _mark_html(html: str) -> str:
    html = html.replace("\r\n", "\n")
    html = html.replace(
        "<title>顺势选股 · 四套合一</title>",
        "<title>顺势选股 · 8787</title>",
    )
    html = html.replace(
        '<div class="title">顺势选股<small>主板 · 创业板 · 妖龙隔夜 · 龙头观察 · 非 ST · 非次新</small></div>',
        '<div class="title">顺势选股<small>本机 http://127.0.0.1:8787/ · 不是 Sequoia-X</small></div>',
    )
    if "Sequoia-X" in html and "不是 Sequoia-X" not in html:
        raise RuntimeError("html unexpectedly contains Sequoia-X")
    return html


def main() -> None:
    files = _load_original()
    html = _mark_html(files["web/index.html"].decode("utf-8"))
    serve = _harden_serve(files["serve_web.py"].decode("utf-8"))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("打开选股.bat", BAT.replace("\n", "\r\n").encode("utf-8"))
        z.writestr("覆盖到顺势选股文件夹.txt", NOTE.replace("\n", "\r\n").encode("utf-8"))
        z.writestr("serve_web.py", serve.encode("utf-8"))
        z.writestr("web/index.html", html.encode("utf-8"))
        z.writestr("web/vendor/html2canvas.min.js", files["web/vendor/html2canvas.min.js"])
    OUT.write_bytes(buf.getvalue())
    print("wrote", OUT, OUT.stat().st_size)


if __name__ == "__main__":
    main()

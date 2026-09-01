@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  顺势选股  http://127.0.0.1:8787/
echo  点「扫描主板」或「扫描创业板」，不会扫全市场
echo.
where python >nul 2>&1
if %errorlevel%==0 (
  start "" http://127.0.0.1:8787/
  python serve_web.py
  goto :eof
)
where py >nul 2>&1
if %errorlevel%==0 (
  start "" http://127.0.0.1:8787/
  py -3 serve_web.py
  goto :eof
)
echo 未找到 Python 3。请先安装 https://www.python.org/downloads/ 并勾选 Add python.exe to PATH
pause

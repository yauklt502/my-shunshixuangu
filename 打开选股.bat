@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  Sequoia-X  http://127.0.0.1:8787/
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

@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  Sequoia-X     http://127.0.0.1:9801/
echo  顺势选股请用原来的文件夹，地址是 http://127.0.0.1:8787/
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

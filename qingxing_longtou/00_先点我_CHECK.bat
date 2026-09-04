@echo off
cd /d "%~dp0"
title QingXing LongTou - Diagnose
setlocal
echo ==== DIAGNOSE ====
echo CD=%CD%
echo.
echo --- where py ---
where py 2>&1
echo --- where python ---
where python 2>&1
echo --- where python3 ---
where python3 2>&1
echo.
echo --- py -3 ---
py -3 -c "import sys; print(sys.version); print(sys.executable)" 2>&1
echo --- python ---
python -c "import sys; print(sys.version); print(sys.executable)" 2>&1
echo.
echo --- imports ---
py -3 -c "import requests,PIL,dotenv,tkinter; print('imports OK')" 2>&1
python -c "import requests,PIL,dotenv,tkinter; print('imports OK')" 2>&1
echo.
echo --- wheels_win ---
dir /b "%~dp0wheels_win" 2>&1
echo.
echo --- start_log.txt ---
if exist "%~dp0start_log.txt" (type "%~dp0start_log.txt") else (echo no log yet)
echo.
pause
endlocal

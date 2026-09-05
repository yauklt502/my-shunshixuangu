@echo off
cd /d %~dp0
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
set PYTHONPATH=%cd%
if "%TDX_HOST%"=="" set TDX_HOST=115.238.90.165:7709
if "%TSP_PORT%"=="" set TSP_PORT=8765
python -m uvicorn backend.app:app --host 127.0.0.1 --port %TSP_PORT%

@echo off
cd /d %~dp0
echo 正在启动 10秒定龙头  http://127.0.0.1:8688
where python >nul 2>nul
if %errorlevel%==0 (
  python launch.py
) else (
  py launch.py
)
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 启动顺势竞价选股...
python -m app --host 127.0.0.1 --port 8787
pause

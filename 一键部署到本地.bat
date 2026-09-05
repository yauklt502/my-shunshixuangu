@echo off
chcp 65001 >nul
setlocal
set "SRC=%~dp0"
set "DST=%USERPROFILE%\三条纪律看板"
echo 将复制到: %DST%
if not exist "%DST%" mkdir "%DST%"
robocopy "%SRC%." "%DST%" /E /XD .git .venv .wrangler web\download /NFL /NDL /NJH /NJS /nc /ns /np >nul
if errorlevel 8 (
  echo 复制失败。
  pause
  exit /b 1
)
cd /d "%DST%"
call "%DST%\start.cmd"

@echo off
setlocal
set "SRC=%~dp0"
set "DST=E:\三条纪律看板"
if not exist E:\ (
  echo E: drive not found, deploying to user folder instead...
  call "%~dp0一键部署到本地.bat"
  exit /b %errorlevel%
)
echo Copy to: %DST%
if not exist "%DST%" mkdir "%DST%"
robocopy "%SRC%." "%DST%" /E /XD .git .venv .wrangler web\download node_modules /NFL /NDL /NJH /NJS /nc /ns /np >nul
if errorlevel 8 (
  echo Copy failed.
  pause
  exit /b 1
)
cd /d "%DST%"
call "%DST%\启动.bat"

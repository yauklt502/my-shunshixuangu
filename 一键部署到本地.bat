@echo off
chcp 65001 >nul
setlocal
set "SRC=%~dp0"
set "DST=%USERPROFILE%\三条纪律看板"

echo 将安装到: %DST%
if exist "%DST%" (
  echo 目标已存在，将覆盖更新文件...
) else (
  mkdir "%DST%"
)

robocopy "%SRC%." "%DST%" /E /XD .git .wrangler node_modules\wrangler web\download /NFL /NDL /NJH /NJS /nc /ns /np >nul
if errorlevel 8 (
  echo 复制失败。
  pause
  exit /b 1
)

cd /d "%DST%"
if not exist "node_modules\iconv-lite" (
  echo 正在安装依赖...
  call npm install --omit=dev
)

echo.
echo 部署完成: %DST%
echo 正在启动...
start "" "http://127.0.0.1:5177/"
node server\index.mjs
pause

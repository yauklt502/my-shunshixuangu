@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "SRC=%~dp0e-drive"
if not exist "%SRC%\index.html" set "SRC=%~dp0E盘一键"

set "DEST=E:\龙头盯盘"
if not exist "E:\" (
  echo 没有检测到 E 盘，改放到桌面。
  set "DEST=%USERPROFILE%\Desktop\龙头盯盘"
)

if not exist "%SRC%\index.html" (
  echo 找不到盯盘文件。请先解压完整压缩包，再点这个文件。
  pause
  exit /b 1
)

if not exist "%DEST%" mkdir "%DEST%"
copy /Y "%SRC%\index.html" "%DEST%\index.html" >nul
copy /Y "%SRC%\start-server.ps1" "%DEST%\start-server.ps1" >nul
copy /Y "%SRC%\open.bat" "%DEST%\open.bat" >nul
copy /Y "%SRC%\open.bat" "%DEST%\打开盯盘.bat" >nul
if exist "%SRC%\使用说明.txt" copy /Y "%SRC%\使用说明.txt" "%DEST%\使用说明.txt" >nul

echo.
echo 已经放到：%DEST%
echo 以后只要双击「打开盯盘.bat」
echo.
start "" "%DEST%\open.bat"
exit /b 0

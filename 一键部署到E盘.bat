@echo off
setlocal EnableExtensions
chcp 65001 >nul
title 部署短线寻龙到 E 盘
set "SRC=%~dp0"
set "DEST=E:\短线寻龙"

echo.
echo  将把本目录复制到： %DEST%
echo.

if not exist E:\ (
  echo 未检测到 E 盘。请插入/挂载 E 盘后重试，或直接把本文件夹拷到任意盘后双击「启动.bat」。
  pause
  exit /b 1
)

if not exist "%DEST%" mkdir "%DEST%"

where robocopy >nul 2>&1
if errorlevel 1 (
  xcopy /E /I /Y "%SRC%*" "%DEST%\"
) else (
  robocopy "%SRC%." "%DEST%" /E /NFL /NDL /NJH /NJS /nc /ns /np /XD .git .cursor node_modules /XF .gitignore
  if errorlevel 8 (
    echo 复制失败。
    pause
    exit /b 1
  )
)

echo 已复制到 %DEST%
echo 正在启动…
echo.
cd /d "%DEST%"
call "%DEST%\启动.bat"

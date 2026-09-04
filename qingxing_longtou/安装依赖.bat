@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 清醒龙头战法 - 安装依赖

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 python。请先安装 Python 3.10+ 并勾选 Add to PATH。
  echo 下载: https://www.python.org/downloads/
  pause
  exit /b 1
)

echo.
echo ===== 使用离线 wheels 安装依赖 =====
python -m pip install --upgrade pip
python -m pip install --no-index --find-links="%~dp0wheels_win" -r "%~dp0requirements.txt"
if errorlevel 1 (
  echo.
  echo [提示] 离线安装失败，尝试联网安装...
  python -m pip install -r "%~dp0requirements.txt"
  if errorlevel 1 (
    echo [错误] 依赖安装失败。请检查 Python 版本（需 3.10~3.13 64位）。
    pause
    exit /b 1
  )
)

if not exist "%~dp0.env" (
  copy /Y "%~dp0.env.example" "%~dp0.env" >nul
  echo 已生成 .env （可按需填写同花顺 Key / 通达信路径）
)

echo.
echo [完成] 依赖已就绪。请双击「启动选股.bat」
pause

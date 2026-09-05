@echo off
chcp 65001 >nul
title 顺势选股 · 停止
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 launcher.py --stop
  goto :done
)
where python >nul 2>nul
if not errorlevel 1 python launcher.py --stop
:done
if /I not "%~1"=="nopause" pause

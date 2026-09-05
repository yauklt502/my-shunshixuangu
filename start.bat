@echo off
cd /d %~dp0
where python >nul 2>nul
if %errorlevel%==0 (
  python launch.py
) else (
  py launch.py
)
pause

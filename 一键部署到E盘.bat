@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

title 顺时选股 - 一键部署到 E 盘

set "TARGET=E:\shunshi-trading"
set "SOURCE=%~dp0"
if "%SOURCE:~-1%"=="\" set "SOURCE=%SOURCE:~0,-1%"

echo.
echo  ============================================
echo    顺时选股交易系统 - 一键部署到 E 盘
echo  ============================================
echo.

:: ---------- 1. 检查 E 盘 ----------
echo [1/6] 检查 E 盘...
if not exist E:\ (
    echo [错误] 未找到 E 盘。请确认 E 盘已挂载后重试。
    pause
    exit /b 1
)
echo       E 盘 OK

:: ---------- 2. 复制文件 ----------
echo [2/6] 复制文件到 %TARGET% ...
if not exist "%TARGET%" mkdir "%TARGET%"

robocopy "%SOURCE%" "%TARGET%" /E ^
    /XD .git .venv __pycache__ .cache data ^
    /XF *.pyc *.pyo deploy.log ^
    /NFL /NDL /NJH /NJS /nc /ns /np >nul

if %ERRORLEVEL% GEQ 8 (
    echo [错误] 文件复制失败，错误码: %ERRORLEVEL%
    pause
    exit /b 1
)
echo       复制完成

:: ---------- 3. 检查 Python ----------
echo [3/6] 检查 Python 环境...
where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未检测到 Python。
        echo        请先安装 Python 3.10+：https://www.python.org/downloads/
        echo        安装时勾选 "Add Python to PATH"
        pause
        exit /b 1
    )
    set "PY=py -3"
) else (
    set "PY=python"
)

for /f "tokens=*" %%v in ('%PY% --version 2^>^&1') do set PYVER=%%v
echo       检测到 !PYVER!

:: ---------- 4. 虚拟环境 + 依赖 ----------
echo [4/6] 创建虚拟环境并安装依赖...
cd /d "%TARGET%"

if not exist ".venv\Scripts\activate.bat" (
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络连接
    pause
    exit /b 1
)
echo       依赖安装完成

:: ---------- 5. 生成启动/停止脚本 ----------
echo [5/6] 生成启动脚本...

(
echo @echo off
echo chcp 65001 ^>nul
echo title 顺时选股交易系统
echo.
echo set "APP_DIR=%%~dp0"
echo cd /d "%%APP_DIR%%"
echo.
echo if not exist ".venv\Scripts\activate.bat" ^(
echo     echo [错误] 未找到虚拟环境，请先运行「一键部署到E盘.bat」
echo     pause
echo     exit /b 1
echo ^)
echo.
echo call .venv\Scripts\activate.bat
echo set DATA_SOURCE=eastmoney
echo.
echo echo 正在启动服务...
echo echo 看板地址: http://localhost:8000
echo echo 按 Ctrl+C 可停止服务
echo echo.
echo start "" /min cmd /c "timeout /t 3 /nobreak ^>nul ^& start http://localhost:8000"
echo python -m src.main --mode api --port 8000
echo pause
) > "%TARGET%\一键启动.bat"

(
echo @echo off
echo chcp 65001 ^>nul
echo title 停止顺时选股服务
echo echo 正在停止 8000 端口服务...
echo for /f "tokens=5" %%%%a in ^('netstat -ano ^^| findstr ":8000 " ^^| findstr "LISTENING"'^) do taskkill /F /PID %%%%a 2^>nul
echo echo 已停止。
echo timeout /t 2 ^>nul
) > "%TARGET%\停止服务.bat"

echo       已生成: 一键启动.bat / 停止服务.bat

:: ---------- 6. 桌面快捷方式 ----------
echo [6/6] 创建桌面快捷方式...

set "DESKTOP=%USERPROFILE%\Desktop"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%DESKTOP%\顺时选股.lnk'); ^
   $s.TargetPath = '%TARGET%\一键启动.bat'; ^
   $s.WorkingDirectory = '%TARGET%'; ^
   $s.IconLocation = 'shell32.dll,13'; ^
   $s.Description = '顺时选股交易系统'; ^
   $s.Save()" 2>nul

if exist "%DESKTOP%\顺时选股.lnk" (
    echo       桌面快捷方式已创建
) else (
    echo       快捷方式创建跳过（可手动双击 E 盘内一键启动.bat）
)

echo.
echo  ============================================
echo    部署成功！
echo  ============================================
echo    安装目录 : %TARGET%
echo    启动方式 : 双击「一键启动.bat」或桌面「顺时选股」
echo    看板地址 : http://localhost:8000
echo    数据端口 : 东方财富实时（右上角可切换）
echo  ============================================
echo.
set /p RUN="是否立即启动？(Y/N): "
if /i "%RUN%"=="Y" (
    start "" "%TARGET%\一键启动.bat"
)
pause
endlocal

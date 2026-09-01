@echo off
REM Install Python deps — skip pip upgrade, use China mirror first.
setlocal
set PIP_DISABLE_PIP_VERSION_CHECK=1
set PIP_DEFAULT_TIMEOUT=120

if not exist ".venv\Scripts\pip.exe" (
    echo [ERROR] venv not found. Run deploy first.
    exit /b 1
)

call ".venv\Scripts\activate.bat"

pip show fastapi >nul 2>&1
if not errorlevel 1 (
    echo       依赖已存在，快速检查更新...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --prefer-binary -q
    if not errorlevel 1 exit /b 0
)

echo       首次安装 numpy/pandas 等，约 1-3 分钟，请勿关闭...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --prefer-binary
if not errorlevel 1 exit /b 0

echo       清华镜像失败，尝试阿里云镜像...
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com --prefer-binary
if not errorlevel 1 exit /b 0

echo       镜像均失败，尝试官方 PyPI（可能较慢）...
pip install -r requirements.txt --prefer-binary
exit /b %ERRORLEVEL%

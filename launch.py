"""一键启动：装依赖、打开 8688、弹出浏览器。"""

from __future__ import annotations

import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from dragon.config import LOCAL_URL, PORT

ROOT = Path(__file__).resolve().parent


def _install() -> None:
    req = ROOT / "requirements.txt"
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", str(req)])


def _wait_up(seconds: float = 20.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{LOCAL_URL}/api/health", timeout=1) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.25)
    return False


def main() -> None:
    _install()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "server:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(PORT),
        ],
        cwd=ROOT,
    )
    try:
        if _wait_up():
            webbrowser.open(LOCAL_URL)
            print(f"已启动  {LOCAL_URL}")
            print(f"截屏    {LOCAL_URL}/api/shot.png")
            print(f"下载程序  {LOCAL_URL}/download.zip")
        else:
            print(f"服务没起来，看控制台报错。端口 {PORT}")
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()

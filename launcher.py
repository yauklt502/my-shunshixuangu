#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""顺势选股 · 一键启动（macOS / Linux；Windows 请双击 一键启动.bat）"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
WEB = ROOT / "web"
VENV = BACKEND / ".venv"
PORT = int(os.environ.get("SSP_PORT") or "5173")
PAGE = f"http://127.0.0.1:{PORT}/"
HEALTH = f"http://127.0.0.1:{PORT}/api/health"
IS_WIN = os.name == "nt"


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")


def which_python() -> list[str]:
    if IS_WIN:
        if shutil.which("python"):
            return ["python"]
        if shutil.which("py"):
            return ["py", "-3"]
    else:
        if shutil.which("python3"):
            return ["python3"]
        if shutil.which("python"):
            return ["python"]
    print("[ERROR] 未找到 Python 3.10+")
    raise SystemExit(1)


def import_ok() -> bool:
    py = venv_python()
    if not py.exists():
        return False
    try:
        subprocess.check_call(
            [str(py), "-c", "import uvicorn,fastapi,httpx"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1.2) as r:
            return 200 <= getattr(r, "status", 200) < 300
    except Exception:
        return False


def kill_port(port: int) -> None:
    if IS_WIN:
        try:
            out = subprocess.check_output(
                f'netstat -ano | findstr ":{port}" | findstr LISTENING',
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            return
        for line in out.splitlines():
            parts = line.split()
            if parts and parts[-1].isdigit():
                subprocess.run(["taskkill", "/F", "/PID", parts[-1]], check=False)
        return
    try:
        out = subprocess.check_output(
            ["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        for pid in out.split():
            if pid.isdigit():
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except Exception:
                    pass
    except Exception:
        pass


def start() -> None:
    print()
    print("========================================")
    print("  顺势选股 · 一键启动")
    print("========================================")
    print()

    if not (BACKEND / "app" / "main.py").exists():
        print("[ERROR] 找不到 backend，请在解压后的目录里运行")
        raise SystemExit(1)
    if not (WEB / "index.html").exists():
        print("[ERROR] 缺少 web/index.html，请重新解压完整 ZIP")
        raise SystemExit(1)

    sys_py = which_python()

    if http_ok(HEALTH):
        print("[4/4] Opening browser ...")
        webbrowser.open(PAGE)
        print(f"  already running: {PAGE}")
        return

    print("[1/4] Creating / checking venv ...")
    if not venv_python().exists():
        subprocess.check_call(sys_py + ["-m", "venv", str(VENV)])

    print("[2/4] Installing dependencies (first run 1-3 min) ...")
    if import_ok():
        print("      already installed, skip.")
    else:
        py = str(venv_python())
        subprocess.check_call([py, "-m", "pip", "install", "-U", "pip"])
        subprocess.check_call([py, "-m", "pip", "install", "-r", str(BACKEND / "requirements.txt")])

    print("[3/4] Starting server ...")
    kill_port(PORT)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    proc = subprocess.Popen(
        [str(venv_python()), "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(PORT)],
        cwd=str(BACKEND),
        env=env,
    )

    print("[4/4] Opening browser ...")
    for _ in range(40):
        if proc.poll() is not None:
            print("[ERROR] 服务启动失败")
            raise SystemExit(1)
        if http_ok(HEALTH) and http_ok(PAGE):
            break
        time.sleep(0.25)
    else:
        print("[ERROR] 服务未在端口 5173 就绪")
        proc.terminate()
        raise SystemExit(1)
    webbrowser.open(PAGE)
    print()
    print(f"  URL: {PAGE}")
    print("  请不要关闭本窗口。按 Ctrl+C 停止。")
    print()
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        kill_port(PORT)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stop", action="store_true")
    args = parser.parse_args()
    if args.stop:
        kill_port(PORT)
        kill_port(8010)
        print("已停止。")
        return
    start()


if __name__ == "__main__":
    main()

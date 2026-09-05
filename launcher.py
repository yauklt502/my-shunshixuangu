#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""顺势选股 · 一键启动

双击后直接打开网页。依赖装在本机用户目录，换文件夹 / 重新解压 ZIP 不会再下载。
不需要 Node.js。
"""
from __future__ import annotations

import argparse
import hashlib
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
RUN = ROOT / ".run"
PORT = int(os.environ.get("SSP_PORT") or os.environ.get("FRONTEND_PORT") or "5173")
PAGE = f"http://127.0.0.1:{PORT}/"
HEALTH = f"http://127.0.0.1:{PORT}/api/health"
LOG = RUN / "server.log"
PID_FILE = RUN / "server.pid"
IS_WIN = os.name == "nt"
APP_NAME = "shunshi-xuangu"


def info(msg: str) -> None:
    print(f"  {msg}", flush=True)


def die(msg: str, code: int = 1) -> None:
    print(f"\n[错误] {msg}", file=sys.stderr)
    raise SystemExit(code)


def http_ok(url: str, timeout: float = 1.2) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= getattr(r, "status", 200) < 300
    except Exception:
        return False


def cache_home() -> Path:
    if IS_WIN:
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / APP_NAME
    xdg = os.environ.get("XDG_CACHE_HOME")
    return Path(xdg) / APP_NAME if xdg else Path.home() / ".cache" / APP_NAME


def which_python() -> list[str]:
    if IS_WIN:
        py = shutil.which("py")
        if py:
            return [py, "-3"]
        for name in ("python", "python3"):
            p = shutil.which(name)
            if p and "WindowsApps" not in p:
                return [p]
    else:
        for name in ("python3", "python"):
            p = shutil.which(name)
            if p:
                return [p]
    die(
        "本机没有 Python。请安装 Python 3.10+（Windows 务必勾选 Add python.exe to PATH）\n"
        "下载: https://www.python.org/downloads/"
    )


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if IS_WIN else "bin/python")


def venv_uvicorn(venv: Path) -> Path:
    return venv / ("Scripts/uvicorn.exe" if IS_WIN else "bin/uvicorn")


def req_hash() -> str:
    return hashlib.sha256((BACKEND / "requirements.txt").read_bytes()).hexdigest()[:16]


def deps_ready(py: Path, stamp: Path) -> bool:
    if not py.exists() or not stamp.exists():
        return False
    try:
        if stamp.read_text(encoding="utf-8").strip() != req_hash():
            return False
    except Exception:
        return False
    try:
        subprocess.check_call(
            [str(py), "-c", "import uvicorn, fastapi, eltdx, httpx"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def _import_ok(py: Path) -> bool:
    if not py.exists():
        return False
    try:
        subprocess.check_call(
            [str(py), "-c", "import uvicorn, fastapi, eltdx, httpx"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def ensure_venv(sys_py: list[str]) -> Path:
    """依赖放用户目录，不跟着 ZIP 走，避免每次解压都重下。"""
    home = cache_home()
    shared = home / "venv"
    stamp = home / "requirements.sha"
    home.mkdir(parents=True, exist_ok=True)

    if deps_ready(venv_python(shared), stamp):
        return shared
    # 本目录里已经装过，直接用，免得再下一遍
    local = BACKEND / ".venv"
    if _import_ok(venv_python(local)):
        return local

    print("  本机第一次（或依赖有更新），正在准备运行环境…")
    print("  只做这一次，以后双击、重新解压都不用再下载。")
    py = venv_python(shared)
    if not py.exists():
        subprocess.check_call(sys_py + ["-m", "venv", str(shared)])
    pip_cache = home / "pip-cache"
    env = os.environ.copy()
    env["PIP_CACHE_DIR"] = str(pip_cache)
    subprocess.check_call([str(py), "-m", "pip", "install", "-U", "pip"], env=env)
    subprocess.check_call(
        [str(py), "-m", "pip", "install", "-r", str(BACKEND / "requirements.txt")],
        env=env,
    )
    stamp.write_text(req_hash(), encoding="utf-8")
    print("  准备完成。")
    return shared


def kill_pid(pid: int) -> None:
    if pid <= 0:
        return
    try:
        if IS_WIN:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            try:
                os.killpg(pid, signal.SIGTERM)
            except Exception:
                os.kill(pid, signal.SIGTERM)
    except Exception:
        pass


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
                subprocess.run(
                    ["taskkill", "/F", "/PID", parts[-1]],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
        return
    try:
        out = subprocess.check_output(
            ["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        for pid in out.split():
            if pid.isdigit():
                kill_pid(int(pid))
    except Exception:
        pass


def stop_all() -> None:
    if PID_FILE.exists():
        try:
            kill_pid(int(PID_FILE.read_text().strip()))
        except Exception:
            pass
        try:
            PID_FILE.unlink()
        except Exception:
            pass
    kill_port(PORT)
    # 兼容旧版双进程
    kill_port(8010)


def tail(path: Path, n: int = 40) -> str:
    if not path.exists():
        return "(无日志)"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:]) if lines else "(空日志)"
    except Exception as e:
        return f"(读日志失败: {e})"


def popen(cmd: list[str], cwd: Path, log: Path, env: dict | None = None) -> subprocess.Popen:
    log.parent.mkdir(parents=True, exist_ok=True)
    lf = open(log, "w", encoding="utf-8", errors="replace")
    merged = os.environ.copy()
    if env:
        merged.update(env)
    kwargs: dict = {"cwd": str(cwd), "stdout": lf, "stderr": subprocess.STDOUT, "env": merged}
    if IS_WIN:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def start() -> None:
    print("\n  顺势选股 · 正在打开…\n", flush=True)

    if not (BACKEND / "app" / "main.py").exists():
        die(f"解压不完整，找不到后端。当前目录: {ROOT}")
    if not (WEB / "index.html").exists():
        die("缺少预构建页面 web/index.html。请重新下载完整 ZIP。")

    # 已经在跑：直接开浏览器，不再装任何东西
    if http_ok(HEALTH) and http_ok(PAGE):
        print(f"  已在运行，打开 {PAGE}")
        webbrowser.open(PAGE)
        print("  关掉本窗口不会停止服务。要停止请运行「一键停止」。")
        return

    sys_py = which_python()
    venv = ensure_venv(sys_py)
    uv = venv_uvicorn(venv)
    if not uv.exists():
        die("运行环境不完整，请删除后重试：\n  " + str(cache_home() / "venv"))

    RUN.mkdir(parents=True, exist_ok=True)
    stop_all()
    time.sleep(0.2)

    server = popen(
        [str(uv), "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=BACKEND,
        log=LOG,
        env={"PYTHONPATH": str(BACKEND)},
    )
    PID_FILE.write_text(str(server.pid), encoding="utf-8")

    for _ in range(40):
        if server.poll() is not None:
            print(tail(LOG))
            die("服务启动失败，请查看上方日志。")
        if http_ok(HEALTH) and http_ok(PAGE):
            break
        time.sleep(0.25)
    else:
        print(tail(LOG))
        stop_all()
        die("服务未就绪。日志: " + str(LOG))

    print(f"  打开 {PAGE}")
    print("  请保持本窗口打开。按 Ctrl+C 停止。")
    print()
    try:
        webbrowser.open(PAGE)
    except Exception:
        info("请手动在浏览器打开上述地址")

    try:
        while True:
            if server.poll() is not None:
                print(tail(LOG))
                die("服务意外退出。")
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        info("正在退出…")
    finally:
        stop_all()


def main() -> None:
    parser = argparse.ArgumentParser(description="顺势选股一键启动")
    parser.add_argument("--stop", action="store_true")
    args = parser.parse_args()
    if args.stop:
        stop_all()
        print("  已停止。")
        return
    start()


if __name__ == "__main__":
    main()

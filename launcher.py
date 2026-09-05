#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""顺势选股 · 跨平台一键启动器

用法:
  python launcher.py          # 启动（前台保持，Ctrl+C 停止）
  python launcher.py --stop   # 仅停止
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
RUN = ROOT / ".run"
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8010"))
FRONTEND_PORT = int(os.environ.get("FRONTEND_PORT", "5173"))
BACKEND_LOG = RUN / "backend.log"
FRONTEND_LOG = RUN / "frontend.log"
BACKEND_PID = RUN / "backend.pid"
FRONTEND_PID = RUN / "frontend.pid"

IS_WIN = os.name == "nt"


def info(msg: str) -> None:
    print(f"[*] {msg}")


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def warn(msg: str) -> None:
    print(f"[!] {msg}")


def die(msg: str, code: int = 1) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    raise SystemExit(code)


def http_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= getattr(r, "status", 200) < 300
    except Exception:
        return False


def which_python() -> str:
    # Prefer already-created venv later; here find a system Python to bootstrap.
    candidates = []
    if IS_WIN:
        candidates.extend(["py", "python", "python3"])
    else:
        candidates.extend(["python3", "python"])
    for c in candidates:
        path = shutil.which(c)
        if path:
            # Avoid Windows Store stub that opens Microsoft Store
            if IS_WIN and "WindowsApps" in path and c != "py":
                continue
            return path
    die(
        "未找到 Python。请安装 Python 3.10+，Windows 安装时务必勾选 Add to PATH。\n"
        "下载: https://www.python.org/downloads/"
    )


def which_npm() -> str:
    npm = shutil.which("npm.cmd" if IS_WIN else "npm") or shutil.which("npm")
    if not npm:
        die(
            "未找到 npm。请安装 Node.js 18+。\n"
            "下载: https://nodejs.org/"
        )
    return npm


def venv_python() -> Path:
    if IS_WIN:
        return BACKEND / ".venv" / "Scripts" / "python.exe"
    return BACKEND / ".venv" / "bin" / "python"


def venv_uvicorn() -> Path:
    if IS_WIN:
        return BACKEND / ".venv" / "Scripts" / "uvicorn.exe"
    return BACKEND / ".venv" / "bin" / "uvicorn"


def ensure_backend_deps(sys_py: str) -> None:
    py = venv_python()
    if not py.exists():
        info("首次创建后端虚拟环境（可能需几分钟）...")
        subprocess.check_call([sys_py, "-m", "venv", str(BACKEND / ".venv")])
    # install/upgrade deps if uvicorn missing
    try:
        subprocess.check_call(
            [str(py), "-c", "import uvicorn, fastapi, eltdx"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        ok("后端依赖已就绪")
        return
    except subprocess.CalledProcessError:
        pass
    info("安装后端依赖...")
    subprocess.check_call([str(py), "-m", "pip", "install", "-U", "pip"])
    subprocess.check_call(
        [str(py), "-m", "pip", "install", "-r", str(BACKEND / "requirements.txt")]
    )
    ok("后端依赖安装完成")


def ensure_frontend_deps(npm: str) -> None:
    marker = FRONTEND / "node_modules" / "vite"
    if marker.exists():
        ok("前端依赖已就绪")
        return
    info("首次 npm install（可能需几分钟）...")
    subprocess.check_call([npm, "install"], cwd=str(FRONTEND), shell=IS_WIN)
    ok("前端依赖安装完成")


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
        pids = set()
        for line in out.splitlines():
            parts = line.split()
            if parts:
                pids.add(parts[-1])
        for pid in pids:
            if pid.isdigit():
                subprocess.run(
                    ["taskkill", "/F", "/PID", pid],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
        return
    # Unix
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
    info("正在停止服务...")
    for pf in (BACKEND_PID, FRONTEND_PID):
        if pf.exists():
            try:
                kill_pid(int(pf.read_text().strip()))
            except Exception:
                pass
            try:
                pf.unlink()
            except Exception:
                pass
    kill_port(BACKEND_PORT)
    kill_port(FRONTEND_PORT)
    ok(f"已停止（端口 {BACKEND_PORT} / {FRONTEND_PORT}）")


def local_bin(name: str) -> Path:
    """Resolve frontend local binary (vite)."""
    if IS_WIN:
        p = FRONTEND / "node_modules" / ".bin" / f"{name}.cmd"
        if p.exists():
            return p
    p = FRONTEND / "node_modules" / ".bin" / name
    return p


def popen(cmd: list[str], cwd: Path, log: Path, env: dict | None = None) -> subprocess.Popen:
    log.parent.mkdir(parents=True, exist_ok=True)
    lf = open(log, "w", encoding="utf-8", errors="replace")
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    kwargs: dict = {
        "cwd": str(cwd),
        "stdout": lf,
        "stderr": subprocess.STDOUT,
        "env": merged_env,
    }
    if IS_WIN:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        # .cmd shims need shell=True on Windows
        if cmd and str(cmd[0]).lower().endswith(".cmd"):
            return subprocess.Popen(subprocess.list2cmdline(cmd), shell=True, **kwargs)
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def tail(path: Path, n: int = 40) -> str:
    if not path.exists():
        return "(无日志)"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:]) if lines else "(空日志)"
    except Exception as e:
        return f"(读日志失败: {e})"


def start() -> None:
    print()
    print("=" * 44)
    print("  顺势选股 · Role Ladder 一键启动")
    print("=" * 44)
    print()

    if not (BACKEND / "app" / "main.py").exists():
        die(f"找不到后端代码，请确认解压完整。当前目录: {ROOT}")
    if not (FRONTEND / "package.json").exists():
        die(f"找不到前端代码，请确认解压完整。当前目录: {ROOT}")

    sys_py = which_python()
    npm = which_npm()
    info(f"Python: {sys_py}")
    info(f"npm: {npm}")

    RUN.mkdir(parents=True, exist_ok=True)
    stop_all()
    time.sleep(0.5)

    ensure_backend_deps(sys_py)
    ensure_frontend_deps(npm)

    uv = venv_uvicorn()
    if not uv.exists():
        die(f"未找到 uvicorn: {uv}，后端依赖可能安装失败")

    info(f"启动后端 http://127.0.0.1:{BACKEND_PORT}")
    backend = popen(
        [str(uv), "app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
        cwd=BACKEND,
        log=BACKEND_LOG,
        env={"PYTHONPATH": str(BACKEND)},
    )
    BACKEND_PID.write_text(str(backend.pid), encoding="utf-8")

    info(f"启动前端 http://127.0.0.1:{FRONTEND_PORT}")
    vite = local_bin("vite")
    if not vite.exists():
        die(f"未找到前端 vite: {vite}，请删除 frontend/node_modules 后重试")
    front_cmd = [
        str(vite),
        "--host",
        "127.0.0.1",
        "--port",
        str(FRONTEND_PORT),
        "--strictPort",
    ]
    frontend = popen(front_cmd, cwd=FRONTEND, log=FRONTEND_LOG)
    FRONTEND_PID.write_text(str(frontend.pid), encoding="utf-8")

    health = f"http://127.0.0.1:{BACKEND_PORT}/api/health"
    page = f"http://127.0.0.1:{FRONTEND_PORT}/"
    info("等待服务就绪（最多 90 秒）...")

    ready = False
    for i in range(90):
        if backend.poll() is not None:
            print(tail(BACKEND_LOG))
            die("后端进程已退出，请根据上方日志排查（常见：端口占用 / 依赖未装全）")
        if frontend.poll() is not None:
            print(tail(FRONTEND_LOG))
            die("前端进程已退出，请根据上方日志排查（常见：Node 版本过低 / 端口占用）")
        if http_ok(health) and http_ok(page):
            ready = True
            break
        time.sleep(1)
        if i in (10, 25, 45, 70):
            info(f"仍在等待... ({i}s)  后端alive={backend.poll() is None} 前端alive={frontend.poll() is None}")

    if not ready:
        print("\n----- 后端日志 -----")
        print(tail(BACKEND_LOG))
        print("\n----- 前端日志 -----")
        print(tail(FRONTEND_LOG))
        stop_all()
        die(
            "服务未就绪，浏览器不会打开。\n"
            f"请把 .run/backend.log 和 .run/frontend.log 发给开发者，或自行查看。\n"
            f"日志目录: {RUN}"
        )

    ok("前后端均已就绪")
    print()
    print("=" * 44)
    print(f"  页面: {page}")
    print(f"  API : {health}")
    print(f"  日志: {RUN}")
    print("=" * 44)
    print()
    print("请保持本窗口打开。按 Ctrl+C 停止全部服务。")
    print()

    try:
        webbrowser.open(page)
    except Exception:
        warn(f"自动打开浏览器失败，请手动访问: {page}")

    try:
        while True:
            if backend.poll() is not None:
                warn("后端意外退出")
                print(tail(BACKEND_LOG))
                break
            if frontend.poll() is not None:
                warn("前端意外退出")
                print(tail(FRONTEND_LOG))
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        info("收到停止信号")
    finally:
        stop_all()


def main() -> None:
    parser = argparse.ArgumentParser(description="顺势选股一键启动")
    parser.add_argument("--stop", action="store_true", help="停止服务")
    args = parser.parse_args()
    if args.stop:
        stop_all()
        return
    start()


if __name__ == "__main__":
    main()

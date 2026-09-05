#!/usr/bin/env python3
"""Pack Windows local zip: Python venv + Node fallback launchers."""
from __future__ import annotations

import os
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "web", "download")
OUT_ZIP = os.path.join(OUT_DIR, "three-discipline-local.zip")
FOLDER = "三条纪律看板"
ARTIFACT = "/opt/cursor/artifacts/three-discipline-local.zip"

ROOT_FILES = [
    "START.bat",
    "启动.bat",
    "启动.cmd",
    "start.cmd",
    "start-node.cmd",
    "deploy-local.bat",
    "deploy-e.bat",
    "一键部署到本地.bat",
    "一键部署到E盘.bat",
    "使用说明.txt",
    "requirements.txt",
    "README.md",
    "package.json",
]
DIRS = ["backend", "web", "server", "src"]
SKIP = {".git", ".venv", ".wrangler", "download", "__pycache__", "node_modules", ".pack-node-modules"}


def add_tree(zf: zipfile.ZipFile, src: str, prefix: str) -> None:
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        rel_dir = os.path.relpath(dirpath, src).replace("\\", "/")
        if rel_dir == "download" or rel_dir.startswith("download/"):
            continue
        for name in filenames:
            if name.endswith(".zip") or name.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, src)
            zf.write(full, os.path.join(prefix, rel).replace("\\", "/"))


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.isfile(OUT_ZIP):
        os.remove(OUT_ZIP)
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ROOT_FILES:
            path = os.path.join(ROOT, name)
            if os.path.isfile(path):
                zf.write(path, os.path.join(FOLDER, name).replace("\\", "/"))
        for d in DIRS:
            p = os.path.join(ROOT, d)
            if os.path.isdir(p):
                add_tree(zf, p, os.path.join(FOLDER, d))
    size = os.path.getsize(OUT_ZIP)
    print("wrote %s (%.1f KB)" % (OUT_ZIP, size / 1024))
    try:
        os.makedirs(os.path.dirname(ARTIFACT), exist_ok=True)
        shutil.copy2(OUT_ZIP, ARTIFACT)
        print("copied", ARTIFACT)
    except Exception as e:
        print("artifact skip:", e)


if __name__ == "__main__":
    main()

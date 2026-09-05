#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pack zero-install Windows zip (no npm install / no venv on launch)."""
from __future__ import annotations

import os
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "web", "download")
OUT_ZIP = os.path.join(OUT_DIR, "three-discipline-local.zip")
FOLDER = "三条纪律看板"
ARTIFACT = "/opt/cursor/artifacts/three-discipline-local.zip"

INCLUDE_ROOT_FILES = [
    "启动.bat",
    "一键部署到本地.bat",
    "一键部署到E盘.bat",
    "使用说明.txt",
    "package.json",
    "README.md",
    "wrangler.toml",
]

INCLUDE_DIRS = ["server", "src", "web"]
SKIP_DIR_NAMES = {".git", ".wrangler", "download", "__pycache__", "node_modules", ".pack-node-modules"}


def add_tree(zf: zipfile.ZipFile, src_dir: str, zip_prefix: str) -> None:
    for dirpath, dirnames, filenames in os.walk(src_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        rel_dir = os.path.relpath(dirpath, src_dir).replace("\\", "/")
        if rel_dir == "download" or rel_dir.startswith("download/"):
            continue
        for name in filenames:
            if name.endswith(".zip"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, src_dir)
            zf.write(full, os.path.join(zip_prefix, rel).replace("\\", "/"))


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.isfile(OUT_ZIP):
        os.remove(OUT_ZIP)
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in INCLUDE_ROOT_FILES:
            path = os.path.join(ROOT, name)
            if os.path.isfile(path):
                zf.write(path, os.path.join(FOLDER, name).replace("\\", "/"))
        for d in INCLUDE_DIRS:
            add_tree(zf, os.path.join(ROOT, d), os.path.join(FOLDER, d))
    size = os.path.getsize(OUT_ZIP)
    print("wrote %s (%.1f KB)" % (OUT_ZIP, size / 1024))
    try:
        os.makedirs(os.path.dirname(ARTIFACT), exist_ok=True)
        shutil.copy2(OUT_ZIP, ARTIFACT)
        print("copied", ARTIFACT)
    except Exception as e:
        print("artifact copy skipped:", e)


if __name__ == "__main__":
    main()

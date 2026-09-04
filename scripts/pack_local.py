#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pack complete local Windows zip into web/download/."""
from __future__ import annotations

import os
import shutil
import subprocess
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
    "package-lock.json",
    "README.md",
    "wrangler.toml",
]

INCLUDE_DIRS = ["server", "src", "web"]
SKIP_DIR_NAMES = {".git", ".wrangler", "download", "__pycache__", "node_modules"}
SKIP_FILE_SUFFIX = {".zip", ".png"}


def should_skip(path: str, name: str) -> bool:
    if name in SKIP_DIR_NAMES:
        return True
    if name.endswith(tuple(SKIP_FILE_SUFFIX)) and "vendor" not in path.replace("\\", "/"):
        # keep vendor/*.js, skip accidental zips/pngs at top of web
        if name.endswith(".zip"):
            return True
    return False


def add_tree(zf: zipfile.ZipFile, src_dir: str, zip_prefix: str) -> None:
    for dirpath, dirnames, filenames in os.walk(src_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        # skip web/download contents to avoid nesting the zip inside itself
        rel_dir = os.path.relpath(dirpath, src_dir)
        if rel_dir.replace("\\", "/").startswith("download"):
            continue
        for name in filenames:
            if name.endswith(".zip"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, src_dir)
            zf.write(full, os.path.join(zip_prefix, rel).replace("\\", "/"))


def ensure_runtime_node_modules() -> None:
    """Install production deps into a staging node_modules for offline-ish first run."""
    staging = os.path.join(ROOT, ".pack-node-modules")
    if os.path.isdir(staging):
        shutil.rmtree(staging)
    os.makedirs(staging, exist_ok=True)
    shutil.copy2(os.path.join(ROOT, "package.json"), os.path.join(staging, "package.json"))
    if os.path.isfile(os.path.join(ROOT, "package-lock.json")):
        shutil.copy2(os.path.join(ROOT, "package-lock.json"), os.path.join(staging, "package-lock.json"))
    subprocess.check_call(["npm", "install", "--omit=dev"], cwd=staging)
    return os.path.join(staging, "node_modules")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    nm = ensure_runtime_node_modules()
    if os.path.isfile(OUT_ZIP):
        os.remove(OUT_ZIP)
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in INCLUDE_ROOT_FILES:
            path = os.path.join(ROOT, name)
            if os.path.isfile(path):
                zf.write(path, os.path.join(FOLDER, name).replace("\\", "/"))
        for d in INCLUDE_DIRS:
            add_tree(zf, os.path.join(ROOT, d), os.path.join(FOLDER, d))
        # bundle production node_modules
        for dirpath, dirnames, filenames in os.walk(nm):
            dirnames[:] = [d for d in dirnames if d not in {".cache"}]
            for name in filenames:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, nm)
                zf.write(full, os.path.join(FOLDER, "node_modules", rel).replace("\\", "/"))
    size = os.path.getsize(OUT_ZIP)
    print("wrote %s (%d bytes / %.1f MB)" % (OUT_ZIP, size, size / 1024 / 1024))
    try:
        os.makedirs(os.path.dirname(ARTIFACT), exist_ok=True)
        shutil.copy2(OUT_ZIP, ARTIFACT)
        print("copied %s" % ARTIFACT)
    except Exception as e:
        print("artifact copy skipped:", e)
    # cleanup staging
    staging = os.path.join(ROOT, ".pack-node-modules")
    if os.path.isdir(staging):
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pack the E-drive portable zip into web/download/."""
from __future__ import annotations

import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "web", "download")
OUT_ZIP = os.path.join(OUT_DIR, "duanxian-xunlong-E.zip")
FOLDER = "短线寻龙"

FILES = [
    "一键部署到E盘.bat",
    "启动.bat",
    "使用说明.txt",
    "serve.py",
    "serve.js",
    "package.json",
]


def add_tree(zf: zipfile.ZipFile, src_dir: str, zip_prefix: str) -> None:
    for dirpath, dirnames, filenames in os.walk(src_dir):
        dirnames[:] = [d for d in dirnames if d not in {".git", "download", "__pycache__"}]
        for name in filenames:
            if name.endswith(".zip"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, src_dir)
            zf.write(full, os.path.join(zip_prefix, rel).replace("\\", "/"))


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in FILES:
            path = os.path.join(ROOT, name)
            if os.path.isfile(path):
                zf.write(path, os.path.join(FOLDER, name).replace("\\", "/"))
        add_tree(zf, os.path.join(ROOT, "web"), os.path.join(FOLDER, "web"))
    size = os.path.getsize(OUT_ZIP)
    print("wrote %s (%d bytes)" % (OUT_ZIP, size))


if __name__ == "__main__":
    main()

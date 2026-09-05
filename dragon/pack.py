"""打包源码 zip，给页面 /download.zip 和一键启动用。"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIR = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".idea", ".vscode", "xgb", "shots"}
SKIP_FILE = {".DS_Store"}
SKIP_SUFFIX = {".pyc", ".pyo", ".log"}


def build_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_DIR for part in path.parts):
                continue
            if path.name in SKIP_FILE or path.suffix in SKIP_SUFFIX:
                continue
            zf.write(path, path.relative_to(ROOT).as_posix())
    return buf.getvalue()

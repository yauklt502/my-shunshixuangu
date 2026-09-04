"""应用配置。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")


def _path(env_key: str, default: Path) -> Path:
    raw = (os.environ.get(env_key) or "").strip()
    if not raw:
        return default
    p = Path(raw).expanduser()
    return p if p.is_absolute() else (ROOT / p)


FUYAO_API_KEY = (os.environ.get("FUYAO_API_KEY") or os.environ.get("API_KEY") or "").strip()
FUYAO_BASE_URL = (os.environ.get("FUYAO_BASE_URL") or "https://fuyao.aicubes.cn").rstrip("/")
TDX_HOME = (os.environ.get("TDX_HOME") or "").strip()
DEFAULT_SOURCE = (os.environ.get("DEFAULT_SOURCE") or "auto").strip().lower()
SCREENSHOT_DIR = _path("SCREENSHOT_DIR", ROOT / "screenshots")

# 策略阈值（可在界面微调）
TOP_BOARDS = 12
LEADERS_PER_BOARD = 3
MIN_BOARD_MEMBERS = 4
MIN_CHANGE_PCT = 3.0

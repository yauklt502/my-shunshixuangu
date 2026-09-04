"""一键截屏：捕获主窗口客户区并保存 PNG。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import ImageGrab

import config

BJ = timezone(timedelta(hours=8))


def beijing_stamp() -> str:
    return datetime.now(BJ).strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path | None = None) -> Path:
    d = path or config.SCREENSHOT_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def grab_window_bbox(left: int, top: int, right: int, bottom: int, filename: str | None = None) -> Path:
    """按屏幕坐标截取矩形区域。"""
    out_dir = ensure_dir()
    name = filename or f"qingxing_longtou_{beijing_stamp()}.png"
    if not name.lower().endswith(".png"):
        name += ".png"
    path = out_dir / name
    # ImageGrab 在部分 Linux 需依赖 X11；无显示时抛错由调用方处理
    img = ImageGrab.grab(bbox=(left, top, right, bottom))
    img.save(path, format="PNG")
    return path


def grab_fullscreen(filename: str | None = None) -> Path:
    out_dir = ensure_dir()
    name = filename or f"qingxing_longtou_full_{beijing_stamp()}.png"
    if not name.lower().endswith(".png"):
        name += ".png"
    path = out_dir / name
    ImageGrab.grab().save(path, format="PNG")
    return path

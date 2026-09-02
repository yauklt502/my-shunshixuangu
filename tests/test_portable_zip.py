"""Portable Sequoia-X zip contains the local-deploy files."""

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "portable" / "sequoia-x.zip"


def test_portable_zip_has_runtime_files():
    assert ZIP_PATH.is_file()
    with zipfile.ZipFile(ZIP_PATH) as z:
        names = set(z.namelist())
        html = z.read("Sequoia-X/web/index.html").decode("utf-8")
        bat = z.read("Sequoia-X/打开Sequoia-X.bat").decode("utf-8")
        serve = z.read("Sequoia-X/serve_web.py").decode("utf-8")
        note = z.read("Sequoia-X/使用说明.txt").decode("utf-8")
    assert "Sequoia-X/serve_web.py" in names
    assert "Sequoia-X/web/index.html" in names
    assert "Sequoia-X/打开Sequoia-X.bat" in names
    assert "海龟突破" in html
    assert "主板稳健少" not in html
    assert "9801" in bat
    assert "PORT = 9801" in serve
    assert "不要解压进" in note
    assert "端口 9801" in html

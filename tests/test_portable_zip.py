"""Portable zips: Sequoia-X on 9801, 顺势选股 restore overwrites 8787."""

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_portable_zip_has_runtime_files():
    path = ROOT / "portable" / "sequoia-x.zip"
    assert path.is_file()
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        html = z.read("Sequoia-X/web/index.html").decode("utf-8")
        bat = z.read("Sequoia-X/打开Sequoia-X.bat").decode("utf-8")
        serve = z.read("Sequoia-X/serve_web.py").decode("utf-8")
        note = z.read("Sequoia-X/使用说明.txt").decode("utf-8")
    assert "Sequoia-X/serve_web.py" in names
    assert "Sequoia-X/打开Sequoia-X.bat" in names
    assert not any(n.endswith("打开选股.bat") for n in names)
    assert "海龟突破" in html
    assert "主板稳健少" not in html
    assert "9801" in bat
    assert "PORT = 9801" in serve
    assert "不要解压进" in note
    assert "端口 9801" in html


def test_restore_zip_is_flat_overwrite_pack():
    path = ROOT / "portable" / "shunshi-xuangu-restore.zip"
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        html = z.read("web/index.html").decode("utf-8")
        bat = z.read("打开选股.bat").decode("utf-8")
        serve = z.read("serve_web.py").decode("utf-8")
    assert "打开选股.bat" in names
    assert "serve_web.py" in names
    assert "web/index.html" in names
    assert "顺势选股/打开选股.bat" not in names
    assert "顺势选股" in html
    assert "主板稳健少" in html
    assert "Sequoia-X" not in html.replace("不是 Sequoia-X", "")
    assert "8787" in bat
    assert "Stop-Process" in bat or "taskkill" in bat
    assert "allow_reuse_address = False" in serve
    assert "here.parent / \"web\"" not in serve

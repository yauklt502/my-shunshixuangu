"""The web UI exposes Sequoia-X's first four screeners, not PR #19's four."""

from pathlib import Path

HTML = Path(__file__).resolve().parents[1] / "web" / "index.html"


def test_page_is_named_sequoia_x():
    text = HTML.read_text(encoding="utf-8")
    assert "Sequoia-X" in text
    assert "顺势选股 · 四套合一" not in text


def test_four_sequoia_strategies_present():
    text = HTML.read_text(encoding="utf-8")
    for name in ("海龟突破", "均线放量", "高窄旗形", "涨停洗盘"):
        assert name in text
    for fn in ("screenTurtle", "screenMaVolume", "screenFlag", "screenShake"):
        assert f"function {fn}" in text


def test_old_pr19_strategies_removed():
    text = HTML.read_text(encoding="utf-8")
    for name in ("主板稳健少", "创业板放宽", "主板妖龙", "龙头盯盘"):
        assert name not in text
    for fn in ("screenMain", "screenCyb", "screenYao"):
        assert f"function {fn}" not in text


def test_scan_controls_and_proxy_unchanged():
    text = HTML.read_text(encoding="utf-8")
    assert "扫描主板" in text
    assert "扫描创业板" in text
    assert "同花顺+腾讯" in text
    assert "/api/quote" in text
    assert "/api/ths/kline" in text
    assert "html2canvas" in text

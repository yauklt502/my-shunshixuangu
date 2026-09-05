"""把当日定龙结果画成一张复盘图，页面截屏和 /api/shot.png 共用。"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from dragon.config import PORT

FONTS = [
    Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    Path("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"),
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/msyh.ttf"),
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
]

BG = (11, 16, 32)
PANEL = (20, 27, 46)
LINE = (36, 48, 73)
TEXT = (232, 237, 247)
MUTED = (139, 151, 179)
GOLD = (240, 180, 41)
CYAN = (62, 224, 198)
GREEN = (61, 214, 140)
RED = (255, 93, 115)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONTS:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size, index=0)
            except OSError:
                continue
    return ImageFont.load_default()


def _len(font: ImageFont.ImageFont, text: str) -> float:
    if hasattr(font, "getlength"):
        return font.getlength(text)
    box = font.getbbox(text)
    return float(box[2] - box[0])


def _wrap(font: ImageFont.ImageFont, text: str, max_w: int) -> list[str]:
    lines: list[str] = []
    for para in (text or "").splitlines() or [""]:
        cur = ""
        for ch in para:
            if _len(font, cur + ch) <= max_w:
                cur += ch
            else:
                if cur:
                    lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    return lines or [""]


def _stock_line(p: dict | None, empty: str) -> str:
    if not p:
        return empty
    pop = p.get("pop_rank")
    return (
        f"{p.get('name')}  {p.get('boards')}板  {p.get('theme')}  "
        f"换手{p.get('turnover')}%  人气{pop if pop else '-'}"
    )


def render_png(snap: dict[str, Any]) -> tuple[bytes, str]:
    w, h = 1400, 920
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    title_f = _font(36)
    name_f = _font(48)
    body_f = _font(22)
    small_f = _font(18)
    tag_f = _font(20)

    date = str(snap.get("date") or "")
    mode = str(snap.get("mode") or "")
    watch = snap.get("watch") or {}
    hat = str(snap.get("watch_hat") or "")
    ml = snap.get("mainline") or {}
    picks = snap.get("picks") or {}

    d.text((40, 28), "10秒定龙头", font=title_f, fill=GOLD)
    d.text((280, 40), f"{date}  {mode}  涨停{(snap.get('stats') or {}).get('zt', '-')}只", font=body_f, fill=MUTED)

    d.rounded_rectangle((40, 90, w - 40, 320), radius=16, fill=PANEL, outline=(61, 77, 40), width=2)
    if watch:
        d.text((64, 110), f"盯1只 · {hat}", font=small_f, fill=MUTED)
        d.text((64, 142), f"{watch.get('name', '')}", font=name_f, fill=TEXT)
        meta = (
            f"{watch.get('code')}  {watch.get('boards')}板  {watch.get('theme')}  "
            f"人气{watch.get('pop_rank') or '-'}  换手{watch.get('turnover')}%  "
            f"成交{watch.get('amount_yi')}亿  炸{watch.get('open_count')}  首封{watch.get('first_seal')}"
        )
        d.text((64, 210), meta, font=body_f, fill=CYAN)
        reason = str(snap.get("reason") or watch.get("why") or "")
        y = 250
        for line in _wrap(small_f, reason, w - 140)[:3]:
            d.text((64, y), line, font=small_f, fill=TEXT)
            y += 26
    else:
        d.text((64, 150), "今日无龙", font=name_f, fill=TEXT)
        d.text((64, 220), str(snap.get("reason") or ""), font=body_f, fill=MUTED)

    cards = [
        (40, "火车头", picks.get("locomotive"), "主线里最早封的能买的板"),
        (480, "情绪龙头", picks.get("sentiment"), "今天情绪围着谁转"),
        (920, "空间高标", picks.get("height"), "全市场非一字最高板"),
    ]
    watch_code = watch.get("code")
    for x, title, stock, hint in cards:
        on = bool(stock and stock.get("code") == watch_code)
        d.rounded_rectangle((x, 344, x + 420, 500), radius=14, fill=PANEL, outline=GOLD if on else LINE, width=2)
        label = title + (" · 盯" if on else "")
        d.text((x + 20, 360), label, font=tag_f, fill=GOLD if on else CYAN)
        d.text((x + 20, 392), hint, font=small_f, fill=MUTED)
        for i, line in enumerate(_wrap(body_f, _stock_line(stock, "无"), 370)[:3]):
            d.text((x + 20, 424 + i * 26), line, font=body_f, fill=TEXT)

    d.rounded_rectangle((40, 520, w - 40, 780), radius=14, fill=PANEL, outline=LINE, width=1)
    d.text((64, 536), "6 步", font=tag_f, fill=MUTED)
    y = 572
    for st in (snap.get("steps") or [])[:6]:
        ok = bool(st.get("pass"))
        mark = "过" if ok else "否"
        color = GREEN if ok else RED
        d.text((64, y), f"{st.get('step')} {mark}", font=body_f, fill=color)
        detail = f"{st.get('title')}  {st.get('detail') or ''}"
        d.text((150, y), _wrap(small_f, detail, 1120)[0], font=small_f, fill=TEXT)
        y += 32

    ml_txt = "今天没有主线"
    if ml:
        ml_txt = f"主线 {ml.get('theme')}  涨停{ml.get('count')}只  成交{ml.get('amount_yi')}亿  最高{ml.get('max_boards')}板"
    d.text((40, 804), ml_txt, font=body_f, fill=CYAN)
    action = str(snap.get("action") or "")
    d.text((40, 844), _wrap(small_f, action, 1100)[0], font=small_f, fill=GOLD)
    d.text((40, 880), f"本地 {PORT}  ·  先定板块，三路对照，盯一只", font=small_f, fill=MUTED)

    buf = BytesIO()
    img.save(buf, format="PNG")
    name = watch.get("name") or "无龙"
    code = watch.get("code") or "none"
    fname = f"dinglong-{date or 'live'}-{code}-{name}.png"
    return buf.getvalue(), fname


def save_png(snap: dict[str, Any], dest: Path | None = None) -> Path:
    raw, fname = render_png(snap)
    out = dest or (Path(__file__).resolve().parent.parent / "data" / "shots" / fname)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    return out

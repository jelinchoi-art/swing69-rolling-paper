from __future__ import annotations
from io import BytesIO
from pathlib import Path
from typing import Any
import math
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3
from reportlab.lib.utils import ImageReader

W, H = 3508, 4961  # A3 portrait at 300 dpi
DPI = 300
PT_TO_PX = DPI / 72
MIN_FONT_PT = 15.0
MAX_FONT_PT = 20.0

ROOT = Path(__file__).resolve().parent
FRONT_BG = ROOT / "assets" / "front_bg.png"
BACK_BG = ROOT / "assets" / "back_bg.png"

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
    "/usr/share/fonts/truetype/unfonts-core/UnDotum.ttf",
]
BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumBarunGothicBold.ttf",
    "/usr/share/fonts/truetype/unfonts-core/UnDotumBold.ttf",
]


def _font_path(bold: bool = False) -> str:
    for p in (BOLD_CANDIDATES if bold else FONT_CANDIDATES):
        if Path(p).exists():
            return p
    raise FileNotFoundError("Korean font not found. On Streamlit Cloud, keep packages.txt with fonts-nanum.")


def font(pt: float, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_font_path(bold), max(10, int(pt * PT_TO_PX)))


def _text_width(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> int:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    text = text.replace("\r", "").strip()
    if not text:
        return [""]
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if paragraph == "":
            lines.append("")
            continue
        current = ""
        for ch in paragraph:
            trial = current + ch
            if current and _text_width(draw, trial, fnt) > max_width:
                lines.append(current.rstrip())
                current = ch.lstrip()
            else:
                current = trial
        if current:
            lines.append(current.rstrip())
    return lines or [""]


def estimate_card_height(message: dict[str, Any], width: int, pt: float | None = None) -> int:
    tmp = Image.new("RGB", (50, 50), "white")
    d = ImageDraw.Draw(tmp)
    pt = float(pt or message.get("font_pt") or 17.0)
    body_font = font(pt)
    name_font = font(min(pt + 2.0, 21), bold=True)
    pad = 30
    body_w = max(100, width - pad * 2)
    lines = wrap_text(d, message.get("message", ""), body_font, body_w)
    name_h = d.textbbox((0, 0), "가", font=name_font)[3]
    line_h = int(d.textbbox((0, 0), "가", font=body_font)[3] * 1.24)
    return int(pad + name_h + 24 + len(lines) * line_h + pad)


def _pack_page(msgs: list[dict[str, Any]], page: int) -> list[dict[str, Any]]:
    packed: list[dict[str, Any]] = []

    # Each bin is an independent vertical stack. The back page reserves the
    # central upper area for the supplied Seoho & Yujin photo, while still
    # using the left/right sides and most of the lower page for messages.
    if page == 1:
        gap = 34
        bins = [
            {"x": 85, "y": 2040, "top": 2040, "w": 930, "bottom": 3040},
            {"x": W - 85 - 930, "y": 1840, "top": 1840, "w": 930, "bottom": 3040},
        ]
        lower_margin = 95
        lower_gap = 34
        lower_cols = 4
        lower_top, lower_bottom = 3210, 4785
        lower_w = (W - 2 * lower_margin - lower_gap * (lower_cols - 1)) // lower_cols
        bins += [
            {"x": lower_margin + i * (lower_w + lower_gap), "y": lower_top, "top": lower_top, "w": lower_w, "bottom": lower_bottom}
            for i in range(lower_cols)
        ]
    else:
        gap = 34
        bins = [
            {"x": 95, "y": 560, "top": 560, "w": 1035, "bottom": 1940},
            {"x": W - 95 - 1035, "y": 560, "top": 560, "w": 1035, "bottom": 1940},
        ]
        lower_margin = 95
        lower_gap = 34
        lower_cols = 4
        lower_top, lower_bottom = 2010, 4785
        lower_w = (W - 2 * lower_margin - lower_gap * (lower_cols - 1)) // lower_cols
        bins += [
            {"x": lower_margin + i * (lower_w + lower_gap), "y": lower_top, "top": lower_top, "w": lower_w, "bottom": lower_bottom}
            for i in range(lower_cols)
        ]

    for m in msgs:
        mm = dict(m)
        manual = all(mm.get(k) is not None for k in ("page", "x", "y", "w"))
        if manual and int(mm["page"]) == page:
            width = int(mm["w"])
            height = int(mm.get("h") or estimate_card_height(mm, width, mm.get("font_pt")))
            mm["_rect"] = (int(mm["x"]), int(mm["y"]), width, height)
            mm["_manual"] = True
            packed.append(mm)
            continue
        if manual and int(mm["page"]) != page:
            continue

        candidates = []
        for idx, b in enumerate(bins):
            pt = float(mm.get("font_pt") or 15.5)
            h = estimate_card_height(mm, b["w"], pt)
            while b["y"] + h > b["bottom"] and pt > MIN_FONT_PT:
                pt = round(max(MIN_FONT_PT, pt - 0.5), 1)
                h = estimate_card_height(mm, b["w"], pt)
            overflow = max(0, b["y"] + h - b["bottom"])
            fill_ratio = (b["y"] - b["top"]) / max(1, (b["bottom"] - b["top"]))
            candidates.append((overflow > 0, overflow, fill_ratio, idx, pt, h))

        # Prefer a bin that fits; among those, pick the least-filled stack.
        fitting = [c for c in candidates if not c[0]]
        if fitting:
            _, _, _, chosen, pt, h = min(fitting, key=lambda c: (c[2], c[1]))
        else:
            # Never let a full upper-side bin spill into the lower message area.
            # If the page is genuinely full, overflow only at the bottom stacks
            # so collisions stay predictable and visible to the admin.
            pool = candidates if page == 1 else [c for c in candidates if c[3] >= 2]
            _, _, _, chosen, pt, h = min(pool, key=lambda c: (c[1], c[2]))
        b = bins[chosen]
        mm["_rect"] = (b["x"], b["y"], b["w"], h)
        mm["_manual"] = False
        mm["_auto_font_pt"] = pt
        mm["_overflow"] = b["y"] + h > b["bottom"]
        b["y"] += h + gap
        packed.append(mm)
    return packed


def compute_layout(messages: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    visible = [m for m in messages if not m.get("is_hidden")]
    # Preserve manual page assignments; auto items are split 12/front, remainder/back.
    manual_ids = {m["id"] for m in visible if m.get("page") in (1, 2) and m.get("x") is not None}
    autos = [m for m in visible if m["id"] not in manual_ids]
    front_auto, back_auto = autos[:16], autos[16:]
    p1_src = [m for m in visible if m.get("page") == 1 and m["id"] in manual_ids] + front_auto
    p2_src = [m for m in visible if m.get("page") == 2 and m["id"] in manual_ids] + back_auto
    return {1: _pack_page(p1_src, 1), 2: _pack_page(p2_src, 2)}


def find_overlaps(layout: dict[int, list[dict[str, Any]]]) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    for page, items in layout.items():
        for i in range(len(items)):
            ax, ay, aw, ah = items[i]["_rect"]
            for j in range(i + 1, len(items)):
                bx, by, bw, bh = items[j]["_rect"]
                if ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by:
                    hits.append((page, items[i]["id"], items[j]["id"]))
    return hits


def _draw_card(img: Image.Image, m: dict[str, Any], debug_collision: bool = False) -> None:
    draw = ImageDraw.Draw(img, "RGBA")
    x, y, w, h = m["_rect"]
    pt = float(m.get("font_pt") or m.get("_auto_font_pt") or 17.0)
    pt = max(MIN_FONT_PT, min(MAX_FONT_PT, pt))
    body_font = font(pt)
    name_font = font(min(pt + 2, 21), bold=True)
    pad = 30

    # warm paper card with subtle border/shadow
    draw.rounded_rectangle((x+8, y+10, x+w+8, y+h+10), radius=28, fill=(87, 62, 42, 25))
    draw.rounded_rectangle((x, y, x+w, y+h), radius=28, fill=(255, 252, 241, 235), outline=(198, 171, 132, 155), width=3)

    icon = (m.get("icon") or "🍁")[:2]
    nickname = (m.get("nickname") or "").strip()
    header = f"{icon} {nickname}"
    draw.text((x+pad, y+pad), header, font=name_font, fill=(78, 48, 35, 255))
    name_box = draw.textbbox((0,0), "가", font=name_font)
    ty = y + pad + (name_box[3] - name_box[1]) + 24
    max_w = w - pad * 2
    lines = wrap_text(draw, m.get("message", ""), body_font, max_w)
    line_h = int(draw.textbbox((0, 0), "가", font=body_font)[3] * 1.24)
    for line in lines:
        draw.text((x+pad, ty), line, font=body_font, fill=(62, 54, 48, 255))
        ty += line_h

    if m.get("_overflow"):
        draw.rounded_rectangle((x, y, x+w, y+h), radius=28, outline=(210, 35, 35, 255), width=10)


def render_pages(messages: list[dict[str, Any]]) -> tuple[Image.Image, Image.Image, dict[int, list[dict[str, Any]]]]:
    layout = compute_layout(messages)
    front = Image.open(FRONT_BG).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    back = Image.open(BACK_BG).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    for m in layout[1]:
        _draw_card(front, m)
    for m in layout[2]:
        _draw_card(back, m)
    return front, back, layout


def preview_bytes(img: Image.Image, max_width: int = 1100) -> bytes:
    scale = max_width / img.width
    small = img.resize((max_width, int(img.height * scale)), Image.Resampling.LANCZOS)
    out = BytesIO()
    small.save(out, format="JPEG", quality=88, optimize=True)
    return out.getvalue()


def png_bytes(img: Image.Image) -> bytes:
    out = BytesIO()
    img.save(out, format="PNG", dpi=(DPI, DPI))
    return out.getvalue()


def make_a3_pdf(front: Image.Image, back: Image.Image) -> bytes:
    out = BytesIO()
    c = canvas.Canvas(out, pagesize=A3)
    page_w, page_h = A3
    for image in (front, back):
        buf = BytesIO()
        image.save(buf, format="JPEG", quality=95, dpi=(DPI, DPI), optimize=True)
        buf.seek(0)
        c.drawImage(ImageReader(buf), 0, 0, width=page_w, height=page_h, preserveAspectRatio=True, mask='auto')
        c.showPage()
    c.save()
    return out.getvalue()

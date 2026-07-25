"""Reusable layout blocks composed into slides by the composer.

All blocks draw onto a shared canvas and follow an 8px-derived spacing
rhythm scaled from the canvas size.
"""

from __future__ import annotations

import re

from PIL import Image, ImageDraw, ImageFilter

from ..models import BrandKit, TimelineEvent
from .icons import draw_icon
from .layout import fit_text, load_font
from .theme import Theme

_NUM = re.compile(
    r"(?:[£$€]\s?)?\d[\d,.]*(?:%|\s?(?:million|billion|bn|m|k)\b)?", re.I
)


def grid(size: tuple[int, int]) -> int:
    """Base spacing unit: an 8px system scaled to the canvas."""
    return max(8, round(min(size) / 135))


def shadow_card(
    canvas: Image.Image, rect: tuple[int, int, int, int], theme: Theme,
    radius: int = 22,
) -> None:
    """Surface card with a soft drop shadow, subtle border and accent bar."""
    x0, y0, x1, y1 = rect
    pad = radius * 2
    shadow = Image.new("RGBA", (x1 - x0 + pad * 2, y1 - y0 + pad * 2), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        (pad, pad + 6, shadow.width - pad, shadow.height - pad + 6),
        radius=radius, fill=(0, 0, 0, 110),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    canvas.paste(shadow, (x0 - pad, y0 - pad), shadow)

    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(rect, radius=radius, fill=theme.surface,
                           outline=theme.border, width=1)


def chip(
    canvas: Image.Image, x: int, y: int, text: str, theme: Theme,
    brand: BrandKit, px: int,
) -> int:
    """Category label chip. Returns the width consumed."""
    draw = ImageDraw.Draw(canvas)
    font = load_font(brand, px)
    text = text.upper()
    tw = draw.textlength(text, font=font)
    pad_x, pad_y = round(px * 0.8), round(px * 0.45)
    w, h = round(tw + 2 * pad_x), px + 2 * pad_y
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=theme.accent)
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=theme.accent_text)
    return w


def kicker(
    canvas: Image.Image, x: int, y: int, text: str, theme: Theme,
    brand: BrandKit, px: int, icon: str | None = None,
) -> int:
    """Small accent section label with optional icon. Returns height consumed."""
    draw = ImageDraw.Draw(canvas)
    font = load_font(brand, px)
    tx = x
    if icon:
        s = round(px * 1.15)
        draw_icon(draw, icon, x, y + (px - s) // 2 + 1, s, theme.accent)
        tx += s + round(px * 0.6)
    draw.text((tx, y), " ".join(text.upper()), font=font, fill=theme.accent)
    return px


def page_counter(
    canvas: Image.Image, index: int, total: int, theme: Theme,
    brand: BrandKit, margin: int,
) -> None:
    draw = ImageDraw.Draw(canvas)
    px = max(16, canvas.height // 60)
    font = load_font(brand, px, bold=False)
    text = f"{index:02d} — {total:02d}"
    tw = draw.textlength(text, font=font)
    draw.text((canvas.width - margin - tw, margin), text, font=font, fill=theme.muted)


def footer(
    canvas: Image.Image, theme: Theme, brand: BrandKit, margin: int,
    credit: str | None = None, meta: str | None = None,
) -> None:
    """Subtle source footer: brand · credit · metadata in one quiet line."""
    draw = ImageDraw.Draw(canvas)
    px = max(16, canvas.height // 58)
    font = load_font(brand, px, bold=False)
    y = canvas.height - margin - px
    parts = [p for p in (brand.footer or brand.name, credit, meta) if p]
    if parts:
        draw.text((margin, y), "  ·  ".join(parts), font=font, fill=theme.muted)


def watermark_icon(canvas: Image.Image, kind: str, theme: Theme) -> None:
    """Oversized low-opacity category icon as a visual anchor on text slides."""
    w, h = canvas.size
    s = round(w * 0.42)
    layer = Image.new("RGBA", (s + 20, s + 20), (0, 0, 0, 0))
    draw_icon(ImageDraw.Draw(layer), kind, 10, 10, s, theme.accent,
              width=max(3, s // 28))
    layer.putalpha(layer.getchannel("A").point(lambda a: a * 22 // 255))
    canvas.paste(layer, (w - s - round(w * 0.02), h - s - round(h * 0.06)), layer)


def stat_card(
    canvas: Image.Image, rect: tuple[int, int, int, int], fact: str,
    theme: Theme, brand: BrandKit,
) -> None:
    """Card with the fact's leading figure oversized and the context below.

    A fact with no digits gets a plain highlight treatment instead of a
    fabricated placeholder figure — a bold sans em-dash at display size
    reads as a decorative bar, not as "no number available".
    """
    shadow_card(canvas, rect, theme)
    draw = ImageDraw.Draw(canvas)
    x0, y0, x1, y1 = rect
    g = grid(canvas.size)
    pad = g * 3
    inner_w = x1 - x0 - 2 * pad

    match = _NUM.search(fact)
    if match is None:
        _highlight_card(canvas, draw, rect, fact, theme, brand, pad, inner_w, g)
        return

    draw.rectangle((x0 + pad, y0 + pad, x0 + pad + g * 5, y0 + pad + max(4, g // 2)),
                   fill=theme.accent)
    number = match.group(0)
    num_font, num_lines = fit_text(
        draw, number, brand, round((y1 - y0) * 0.3), inner_w, max_lines=1
    )
    ny = y0 + pad + g * 2
    draw.text((x0 + pad, ny), num_lines[0], font=num_font, fill=theme.accent)

    cap_font, cap_lines = fit_text(
        draw, fact, brand, max(18, canvas.height // 46), inner_w,
        max_lines=3, bold=False,
    )
    cy = ny + round(num_font.size * 1.25)
    for line in cap_lines:
        draw.text((x0 + pad, cy), line, font=cap_font, fill=theme.text)
        cy += round(cap_font.size * 1.4)


def _highlight_card(
    canvas: Image.Image, draw: ImageDraw.ImageDraw,
    rect: tuple[int, int, int, int], fact: str, theme: Theme, brand: BrandKit,
    pad: int, inner_w: int, g: int,
) -> None:
    """Fallback for a fact with no leading number: an accent bullet and a
    vertically centred, larger-than-usual line of body text."""
    x0, y0, x1, y1 = rect
    r = g
    cy_bullet = y0 + pad + r
    draw.ellipse((x0 + pad, cy_bullet - r, x0 + pad + 2 * r, cy_bullet + r),
                 fill=theme.accent)

    cap_font, cap_lines = fit_text(
        draw, fact, brand, max(22, canvas.height // 38), inner_w,
        max_lines=4, bold=False,
    )
    total_h = len(cap_lines) * round(cap_font.size * 1.4)
    cy = (y0 + y1) // 2 - total_h // 2 + round(g * 1.5)
    for line in cap_lines:
        draw.text((x0 + pad, cy), line, font=cap_font, fill=theme.text)
        cy += round(cap_font.size * 1.4)


def timeline_block(
    canvas: Image.Image, x: int, y: int, w: int, h: int,
    events: list[TimelineEvent], theme: Theme, brand: BrandKit,
) -> None:
    """Vertical timeline: accent spine, dots, bold moments, quiet detail."""
    draw = ImageDraw.Draw(canvas)
    g = grid(canvas.size)
    n = len(events)
    if not n:
        return
    row_h = h // n
    spine_x = x + g
    draw.line((spine_x, y + g, spine_x, y + h - row_h + g * 2), fill=theme.border,
              width=max(3, g // 3))

    when_font = load_font(brand, max(20, canvas.height // 42))
    what_font = load_font(brand, max(18, canvas.height // 50), bold=False)
    text_x = spine_x + g * 4
    for i, event in enumerate(events):
        ey = y + i * row_h + g
        r = round(g * 1.1)
        draw.ellipse((spine_x - r, ey - r + g, spine_x + r, ey + r + g),
                     fill=theme.accent)
        draw.text((text_x, ey), event.when.upper(), font=when_font,
                  fill=theme.accent)
        _, lines = fit_text(draw, event.what, brand, what_font.size,
                            x + w - text_x, max_lines=2, bold=False)
        wy = ey + round(when_font.size * 1.5)
        for line in lines:
            draw.text((text_x, wy), line, font=what_font, fill=theme.text)
            wy += round(what_font.size * 1.4)

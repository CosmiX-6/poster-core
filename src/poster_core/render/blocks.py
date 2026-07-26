"""Reusable layout blocks composed into slides by the composer.

All blocks draw onto a shared canvas and follow an 8px-derived spacing
rhythm scaled from the canvas size.
"""

from __future__ import annotations

import re

from PIL import Image, ImageDraw, ImageFilter

from ..models import BrandKit, ComparisonPair, MoneyFlowStep, TimelineEvent
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


def progress_bar(canvas: Image.Image, index: int, total: int, theme: Theme) -> None:
    """Thin track across the very top edge, filled up to the current slide —
    a documentary-style "how much of this story is left" cue."""
    w, h = canvas.size
    thickness = max(3, h // 300)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, w, thickness), fill=theme.border)
    if total > 0:
        filled = round(w * index / total)
        draw.rectangle((0, 0, filled, thickness), fill=theme.accent)


def transition_hook(
    canvas: Image.Image, text: str, theme: Theme, brand: BrandKit, margin: int,
) -> None:
    """Swipe-bait line near the bottom of a slide, cueing the next one."""
    draw = ImageDraw.Draw(canvas)
    px = max(18, canvas.height // 46)
    max_w = canvas.width - 2 * margin - round(px * 1.6)
    font, lines = fit_text(draw, text, brand, px, max_w, max_lines=1)
    y = canvas.height - margin - round(font.size * 2.7)
    draw.text((margin, y), lines[0], font=font, fill=theme.accent)
    tw = draw.textlength(lines[0], font=font)
    draw.text((margin + tw + round(font.size * 0.6), y), "→", font=font, fill=theme.accent)


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
    # A genuine number never legitimately ends the match on a bare "." or
    # ",": a real decimal like "3.5" already has a digit after the dot
    # inside the match, so this only ever strips a trailing sentence mark
    # (e.g. "...before 2029." picking up the full stop).
    number = match.group(0).rstrip(".,")
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


def evidence_frame(
    canvas: Image.Image, rect: tuple[int, int, int, int], theme: Theme,
) -> None:
    """A case-file card: sharp corners, bracket ticks like a pinned exhibit
    — visually distinct from the rounded, left-accented prose card."""
    x0, y0, x1, y1 = rect
    g = grid(canvas.size)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle(rect, fill=theme.surface, outline=theme.border, width=1)
    tick = g * 3
    for cx, cy, dx, dy in (
        (x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1),
    ):
        draw.line((cx, cy, cx + dx * tick, cy), fill=theme.accent, width=3)
        draw.line((cx, cy, cx, cy + dy * tick), fill=theme.accent, width=3)


def money_flow_block(
    canvas: Image.Image, x: int, y: int, w: int, h: int,
    steps: list[MoneyFlowStep], theme: Theme, brand: BrandKit,
) -> None:
    """A vertical money trail: boxed actors linked by arrows labelled with
    the amount that moved between them."""
    draw = ImageDraw.Draw(canvas)
    g = grid(canvas.size)
    n = len(steps)
    if not n:
        return
    node_h = min(round(h * 0.24), (h - g * 8 * (n - 1)) // max(n, 1))
    node_h = max(node_h, round(canvas.height * 0.09))
    gap = g * 8 if n > 1 else 0

    name_font = load_font(brand, max(20, canvas.height // 40))
    detail_font = load_font(brand, max(16, canvas.height // 58), bold=False)
    amount_font = load_font(brand, max(20, canvas.height // 38))

    cy = y
    for i, step in enumerate(steps):
        rect = (x, cy, x + w, cy + node_h)
        draw.rounded_rectangle(rect, radius=16, fill=theme.surface,
                               outline=theme.border, width=1)
        draw.rectangle((x, cy, x + max(4, g // 2), cy + node_h), fill=theme.accent)
        tx = x + g * 4
        inner_w = w - g * 5
        name_font_fit, lines = fit_text(draw, step.actor, brand, name_font.size,
                                        inner_w, max_lines=2)
        block_h = len(lines) * round(name_font_fit.size * 1.2)
        detail_h = round(detail_font.size * 1.3) if step.detail else 0
        ty = cy + (node_h - block_h - detail_h) // 2
        for line in lines:
            draw.text((tx, ty), line, font=name_font_fit, fill=theme.text)
            ty += round(name_font_fit.size * 1.2)
        if step.detail:
            draw.text((tx, ty), step.detail, font=detail_font, fill=theme.muted)

        cy += node_h
        if i < n - 1:
            ax = x + w // 2
            draw.line((ax, cy + g, ax, cy + gap - g), fill=theme.accent,
                      width=max(3, g // 3))
            arrow_w = g * 2
            tip_y = cy + gap - g
            draw.polygon(
                [(ax - arrow_w // 2, tip_y - arrow_w), (ax + arrow_w // 2, tip_y - arrow_w),
                 (ax, tip_y)],
                fill=theme.accent,
            )
            next_amount = steps[i + 1].amount
            if next_amount:
                amt_font, amt_lines = fit_text(
                    draw, next_amount, brand, amount_font.size,
                    w - (ax - x) - g * 3, max_lines=1,
                )
                draw.text((ax + g * 2, cy + gap // 2 - amt_font.size // 2),
                          amt_lines[0], font=amt_font, fill=theme.accent)
            cy += gap


def comparison_block(
    canvas: Image.Image, x: int, y: int, w: int,
    comparison: ComparisonPair, theme: Theme, brand: BrandKit,
) -> None:
    """Before/after: two cards split by a VS badge, values colour-coded.

    Card height is sized to content rather than stretched to fill whatever
    space the caller has available, and both values share one font size
    (the larger shrunk to match) so the comparison reads as one scale.
    """
    g = grid(canvas.size)
    draw = ImageDraw.Draw(canvas)
    col_gap = g * 4
    col_w = (w - col_gap) // 2
    mid = x + w // 2

    label_font = load_font(brand, max(16, canvas.height // 52), bold=False)
    value_px = round(canvas.height * 0.1)
    inner_w = col_w - g * 4

    font_a, lines_a = fit_text(draw, comparison.value_a, brand, value_px,
                               inner_w, max_lines=2)
    font_b, lines_b = fit_text(draw, comparison.value_b, brand, value_px,
                               inner_w, max_lines=2)
    shared_size = min(font_a.size, font_b.size)
    if font_a.size != shared_size:
        font_a, lines_a = fit_text(draw, comparison.value_a, brand, shared_size,
                                   inner_w, max_lines=2, min_scale=1.0)
    if font_b.size != shared_size:
        font_b, lines_b = fit_text(draw, comparison.value_b, brand, shared_size,
                                   inner_w, max_lines=2, min_scale=1.0)

    pad_top = g * 3
    card_h = pad_top + round(label_font.size * 1.8) + \
        max(len(lines_a), len(lines_b)) * round(shared_size * 1.15) + g * 3

    columns = (
        (x, comparison.label_a, lines_a, font_a, theme.muted),
        (mid + col_gap // 2, comparison.label_b, lines_b, font_b, theme.accent),
    )
    for cx0, label, lines, font, color in columns:
        draw.rounded_rectangle((cx0, y, cx0 + col_w, y + card_h), radius=20,
                               fill=theme.surface, outline=theme.border, width=1)
        draw.text((cx0 + g * 2, y + g * 3), label.upper(), font=label_font,
                  fill=theme.muted)
        vy = y + pad_top + round(label_font.size * 1.8)
        for line in lines:
            draw.text((cx0 + g * 2, vy), line, font=font, fill=color)
            vy += round(shared_size * 1.15)

    r = g * 3
    cy = y + card_h // 2
    draw.ellipse((mid - r, cy - r, mid + r, cy + r), fill=theme.background,
                 outline=theme.accent, width=2)
    vs_font = load_font(brand, max(16, round(r * 0.9)))
    tw = draw.textlength("VS", font=vs_font)
    draw.text((mid - tw / 2, cy - vs_font.size / 1.7), "VS", font=vs_font,
              fill=theme.accent)

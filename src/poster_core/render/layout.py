"""Pillow-based composition of final assets."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from ..errors import RenderError
from ..models import AssetPlan, BrandKit, SourcedImage

_FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]
_FONT_CANDIDATES_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def load_font(brand: BrandKit, size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = ([brand.font_path] if brand.font_path else []) + (
        _FONT_CANDIDATES_BOLD if bold else _FONT_CANDIDATES_REGULAR
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    brand: BrandKit,
    base_px: int,
    max_width: int,
    max_lines: int,
    bold: bool = True,
    min_scale: float = 0.7,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Wrap text into at most `max_lines`, shrinking the font down to
    `min_scale` of `base_px` before resorting to a visible ellipsis.

    Guarantees no silent word drops: the result is either the complete text
    or a rendering that ends in an ellipsis.
    """
    min_px = max(1, round(base_px * min_scale))
    px = base_px
    while True:
        font = load_font(brand, px, bold)
        lines = wrap_text(draw, text, font, max_width)
        if len(lines) <= max_lines or px <= min_px:
            break
        px = max(min_px, px - max(2, px // 12))
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1] + "…"
        while draw.textlength(last, font=font) > max_width and " " in last[:-1]:
            last = last[:-1].rsplit(" ", 1)[0] + "…"
        lines[-1] = last
    return font, lines


def cover_crop(data: bytes, size: tuple[int, int]) -> Image.Image:
    """Open image bytes and scale/crop to fill `size` exactly."""
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc:
        raise RenderError(f"Could not open sourced image: {exc}") from exc
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)))
    left = (img.width - tw) // 2
    top = (img.height - th) // 2
    return img.crop((left, top, left + tw, top + th))


def _gradient_overlay(img: Image.Image, strength: float = 0.92) -> None:
    """Darken the lower part of the image so text stays legible."""
    w, h = img.size
    overlay = Image.new("L", (1, h), 0)
    start = int(h * 0.42)
    for y in range(start, h):
        alpha = int(255 * strength * ((y - start) / (h - start)) ** 1.4)
        overlay.putpixel((0, y), alpha)
    black = Image.new("RGB", (w, h), "#000000")
    img.paste(black, (0, 0), overlay.resize((w, h)))


def _footer(draw: ImageDraw.ImageDraw, img: Image.Image, brand: BrandKit,
            credit: str | None, margin: int) -> None:
    small = load_font(brand, max(18, img.height // 54), bold=False)
    y = img.height - margin // 2 - small.size
    parts = [p for p in [brand.footer or brand.name, credit] if p]
    if parts:
        draw.text((margin, y), "  ·  ".join(parts), font=small, fill="#C8C8C8")


def render_cover(
    plan: AssetPlan,
    image: SourcedImage,
    brand: BrandKit,
    size: tuple[int, int],
    big_text: bool = False,
) -> Image.Image:
    if not image.data:
        raise RenderError("Cover requires a sourced image")
    img = cover_crop(image.data, size)
    _gradient_overlay(img)
    draw = ImageDraw.Draw(img)
    w, h = size
    margin = round(w * 0.07)
    max_text_width = w - 2 * margin

    headline_px = round(h * (0.085 if big_text else 0.058))
    headline_font, lines = fit_text(
        draw, plan.headline, brand, headline_px, max_text_width, max_lines=3
    )

    sub_font, sub_lines = None, []
    if plan.subheadline and not big_text:
        sub_font, sub_lines = fit_text(
            draw, plan.subheadline, brand, round(headline_px * 0.5),
            max_text_width, max_lines=3, bold=False,
        )

    line_h = round(headline_font.size * 1.18)
    sub_h = round(sub_font.size * 1.3) if sub_font else 0
    block_h = len(lines) * line_h + (len(sub_lines) * sub_h + 12 if sub_lines else 0)
    y = h - margin - block_h - round(h * 0.035)

    # Accent bar above the headline block.
    draw.rectangle(
        (margin, y - 26, margin + round(w * 0.12), y - 26 + max(6, h // 160)),
        fill=brand.accent_color,
    )
    for line in lines:
        draw.text((margin, y), line, font=headline_font, fill=brand.text_color)
        y += line_h
    if sub_lines:
        y += 12
        for line in sub_lines:
            draw.text((margin, y), line, font=sub_font, fill="#E6E6E6")
            y += sub_h

    _footer(draw, img, brand, image.credit, margin)
    return img


def render_text_slide(
    heading: str,
    body: str | None,
    index: int,
    total: int,
    brand: BrandKit,
    size: tuple[int, int],
) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, brand.background_color)
    draw = ImageDraw.Draw(img)
    margin = round(w * 0.09)

    counter_font = load_font(brand, round(h * 0.032), bold=False)
    draw.text((margin, margin), f"{index:02d} / {total:02d}",
              font=counter_font, fill=brand.accent_color)

    heading_font, heading_lines = fit_text(
        draw, heading, brand, round(h * 0.055), w - 2 * margin, max_lines=3
    )
    y = round(h * 0.3)
    for line in heading_lines:
        draw.text((margin, y), line, font=heading_font, fill=brand.text_color)
        y += round(heading_font.size * 1.2)

    if body:
        y += round(h * 0.03)
        body_font, body_lines = fit_text(
            draw, body, brand, round(h * 0.032), w - 2 * margin,
            max_lines=6, bold=False,
        )
        for line in body_lines:
            draw.text((margin, y), line, font=body_font, fill="#D0D4DA")
            y += round(body_font.size * 1.45)

    _footer(draw, img, brand, None, margin)
    return img


def render_infographic(
    plan: AssetPlan, brand: BrandKit, size: tuple[int, int]
) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, brand.background_color)
    draw = ImageDraw.Draw(img)
    margin = round(w * 0.08)

    heading_font, heading_lines = fit_text(
        draw, plan.headline, brand, round(h * 0.05), w - 2 * margin, max_lines=3
    )
    y = margin
    for line in heading_lines:
        draw.text((margin, y), line, font=heading_font, fill=brand.text_color)
        y += round(heading_font.size * 1.2)
    y += round(h * 0.02)
    draw.rectangle((margin, y, margin + round(w * 0.14), y + max(6, h // 160)),
                   fill=brand.accent_color)
    y += round(h * 0.05)

    facts = plan.facts[:5]
    fact_font = load_font(brand, round(h * 0.028), bold=False)
    num_font = load_font(brand, round(h * 0.034))
    row_gap = round(h * 0.02)
    available = h - y - margin
    row_h = min(round(h * 0.14), (available - row_gap * (len(facts) - 1)) // max(len(facts), 1))
    for i, fact in enumerate(facts, start=1):
        draw.rounded_rectangle(
            (margin, y, w - margin, y + row_h), radius=18, fill="#1C222B"
        )
        draw.text((margin + 28, y + row_h // 2 - num_font.size // 2),
                  f"{i}", font=num_font, fill=brand.accent_color)
        text_x = margin + 28 + round(w * 0.06)
        row_font, lines = fit_text(
            draw, fact, brand, fact_font.size, w - margin - text_x - 24,
            max_lines=3, bold=False,
        )
        text_h = len(lines) * round(row_font.size * 1.35)
        ty = y + (row_h - text_h) // 2
        for line in lines:
            draw.text((text_x, ty), line, font=row_font, fill=brand.text_color)
            ty += round(row_font.size * 1.35)
        y += row_h + row_gap

    _footer(draw, img, brand, None, margin)
    return img

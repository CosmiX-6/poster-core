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
    headline_font = load_font(brand, headline_px)
    lines = wrap_text(draw, plan.headline, headline_font, max_text_width)[:3]

    sub_font = load_font(brand, round(headline_px * 0.5), bold=False)
    sub_lines = (
        wrap_text(draw, plan.subheadline, sub_font, max_text_width)[:2]
        if plan.subheadline and not big_text
        else []
    )

    line_h = round(headline_px * 1.18)
    sub_h = round(headline_px * 0.5 * 1.3)
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

    heading_font = load_font(brand, round(h * 0.055))
    y = round(h * 0.3)
    for line in wrap_text(draw, heading, heading_font, w - 2 * margin)[:3]:
        draw.text((margin, y), line, font=heading_font, fill=brand.text_color)
        y += round(h * 0.055 * 1.2)

    if body:
        y += round(h * 0.03)
        body_font = load_font(brand, round(h * 0.032), bold=False)
        for line in wrap_text(draw, body, body_font, w - 2 * margin)[:6]:
            draw.text((margin, y), line, font=body_font, fill="#D0D4DA")
            y += round(h * 0.032 * 1.45)

    _footer(draw, img, brand, None, margin)
    return img


def render_infographic(
    plan: AssetPlan, brand: BrandKit, size: tuple[int, int]
) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, brand.background_color)
    draw = ImageDraw.Draw(img)
    margin = round(w * 0.08)

    heading_font = load_font(brand, round(h * 0.05))
    y = margin
    for line in wrap_text(draw, plan.headline, heading_font, w - 2 * margin)[:3]:
        draw.text((margin, y), line, font=heading_font, fill=brand.text_color)
        y += round(h * 0.05 * 1.2)
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
        lines = wrap_text(draw, fact, fact_font, w - margin - text_x - 24)[:3]
        text_h = len(lines) * round(fact_font.size * 1.35)
        ty = y + (row_h - text_h) // 2
        for line in lines:
            draw.text((text_x, ty), line, font=fact_font, fill=brand.text_color)
            ty += round(fact_font.size * 1.35)
        y += row_h + row_gap

    _footer(draw, img, brand, None, margin)
    return img

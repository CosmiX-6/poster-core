"""Shared typography and image utilities used by blocks and the composer."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from ..errors import RenderError
from ..models import BrandKit

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

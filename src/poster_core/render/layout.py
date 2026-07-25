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

    Guarantees no silent overflow: the result either fits `max_width` on
    every line, or is truncated with a visible ellipsis. This matters for
    unbreakable single-word tokens (e.g. "£250,000") which `wrap_text`
    cannot split onto extra lines — without checking rendered width here,
    such a token would sail past `max_width` at the base font size.
    """
    min_px = max(1, round(base_px * min_scale))
    px = base_px
    while True:
        font = load_font(brand, px, bold)
        lines = wrap_text(draw, text, font, max_width)
        fits = len(lines) <= max_lines and all(
            draw.textlength(line, font=font) <= max_width for line in lines
        )
        if fits or px <= min_px:
            break
        px = max(min_px, px - max(2, px // 12))

    dropped_lines = len(lines) > max_lines  # content beyond max_lines was cut
    lines = lines[:max_lines]
    lines = [
        _ellipsize(draw, line, font, max_width, force=dropped_lines and i == len(lines) - 1)
        for i, line in enumerate(lines)
    ]
    return font, lines


def _ellipsize(
    draw: ImageDraw.ImageDraw, line: str, font: ImageFont.FreeTypeFont,
    max_width: int, force: bool = False,
) -> str:
    """Shrink a single line to fit `max_width`, ending in an ellipsis if cut.

    `force` marks a line whose *own* width already fits but which still
    needs a visible ellipsis because further lines were dropped elsewhere
    (a `max_lines` cut, not a width overflow) — otherwise that truncation
    would be silent. Prefers cutting at a word boundary but falls back to a
    character cut so even a single unbreakable token (a number, a long
    token with no spaces) is guaranteed to fit rather than overflow.
    """
    if draw.textlength(line, font=font) <= max_width and not force:
        return line
    truncated = line
    while truncated and draw.textlength(truncated + "…", font=font) > max_width:
        truncated = truncated[:-1]
        if " " in truncated:
            word_cut = truncated.rsplit(" ", 1)[0]
            if draw.textlength(word_cut + "…", font=font) <= max_width:
                return word_cut + "…"
    return (truncated + "…") if truncated else "…"


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

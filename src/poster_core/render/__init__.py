"""Editorial rendering: semantic themes, layout blocks and the composer."""

from . import blocks
from .composer import render_cover, render_deck, render_infographic
from .layout import cover_crop, fit_text, load_font, wrap_text
from .theme import CATEGORY_THEMES, Theme, resolve_theme

watermark_logo = blocks.watermark_logo

__all__ = [
    "render_cover",
    "render_deck",
    "render_infographic",
    "resolve_theme",
    "Theme",
    "CATEGORY_THEMES",
    "cover_crop",
    "fit_text",
    "load_font",
    "wrap_text",
    "watermark_logo",
]

"""Semantic colour system: each story category gets its own layout language."""

from __future__ import annotations

from pydantic import BaseModel

from ..models import BrandKit, StoryCategory

_DEFAULT_ACCENT = BrandKit().accent_color


class Theme(BaseModel):
    label: str            # category chip text, e.g. "INVESTIGATION"
    background: str
    accent: str
    accent_text: str = "#0B0C0E"  # text drawn on top of the accent colour
    text: str = "#F4F5F7"
    icon: str = "chart"   # contextual icon kind for this category

    @property
    def surface(self) -> str:
        return _lighten(self.background, 0.07)

    @property
    def border(self) -> str:
        return _lighten(self.background, 0.16)

    @property
    def muted(self) -> str:
        return _lighten(self.background, 0.55)


CATEGORY_THEMES: dict[StoryCategory, Theme] = {
    StoryCategory.GENERAL: Theme(
        label="NEWS", background="#14161B", accent="#E4572E", icon="pin"
    ),
    StoryCategory.BREAKING: Theme(
        label="BREAKING", background="#160E0F", accent="#EF4444",
        accent_text="#FFFFFF", icon="alert",
    ),
    StoryCategory.INVESTIGATION: Theme(
        label="INVESTIGATION", background="#17181A", accent="#F59E0B",
        icon="magnify",
    ),
    StoryCategory.POLITICS: Theme(
        label="POLITICS", background="#1B1C21", accent="#E0433D",
        accent_text="#FFFFFF", icon="building",
    ),
    StoryCategory.TECHNOLOGY: Theme(
        label="TECHNOLOGY", background="#0D1726", accent="#38BDF8", icon="chip"
    ),
    StoryCategory.AI: Theme(
        label="AI", background="#131022", accent="#8B5CF6",
        accent_text="#FFFFFF", icon="chip",
    ),
    StoryCategory.FINANCE: Theme(
        label="FINANCE", background="#0F1915", accent="#34D399", icon="chart"
    ),
    StoryCategory.BUSINESS: Theme(
        label="BUSINESS", background="#111A1E", accent="#2DD4BF", icon="building"
    ),
    StoryCategory.SPORTS: Theme(
        label="SPORTS", background="#1A1410", accent="#FB923C", icon="ball"
    ),
    StoryCategory.SCIENCE: Theme(
        label="SCIENCE", background="#14111E", accent="#A78BFA", icon="flask"
    ),
    StoryCategory.HEALTH: Theme(
        label="HEALTH", background="#0F1720", accent="#60A5FA", icon="heart"
    ),
    StoryCategory.DISASTER: Theme(
        label="DISASTER", background="#1A1112", accent="#F43F5E",
        accent_text="#FFFFFF", icon="alert",
    ),
    StoryCategory.PRODUCT_LAUNCH: Theme(
        label="LAUNCH", background="#101820", accent="#22D3EE", icon="box"
    ),
}


def resolve_theme(category: StoryCategory, brand: BrandKit) -> Theme:
    """Semantic theme for the category; an explicitly customised brand accent
    (anything other than the BrandKit default) wins over the category accent."""
    theme = CATEGORY_THEMES.get(category, CATEGORY_THEMES[StoryCategory.GENERAL])
    if brand.accent_color != _DEFAULT_ACCENT:
        theme = theme.model_copy(
            update={"accent": brand.accent_color, "accent_text": "#FFFFFF"}
        )
    return theme


def _lighten(hex_color: str, amount: float) -> str:
    """Blend a hex colour towards white by `amount` (0..1)."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    r, g, b = (round(c + (255 - c) * amount) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"

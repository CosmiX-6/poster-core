"""Slide composition: turns asset plans into finished editorial layouts.

Layouts are composed from blocks per story — a politics investigation, a
stats-heavy finance story and a product launch each get their own visual
language via the semantic theme and the deck the planner built.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from ..errors import RenderError
from ..models import AssetPlan, BrandKit, DeckSlide, SlideKind, SourcedImage
from . import blocks
from .layout import cover_crop, fit_text, load_font
from .theme import Theme, resolve_theme
from .treatments import scrim, treat_hero


def render_cover(
    plan: AssetPlan,
    image: SourcedImage | None,
    brand: BrandKit,
    size: tuple[int, int],
    big_text: bool = False,
) -> Image.Image:
    theme = resolve_theme(plan.category, brand)
    hero = DeckSlide(kind=SlideKind.HERO, heading=plan.headline,
                     body=None if big_text else plan.subheadline)
    return _render_hero(hero, plan, image, brand, theme, size, big_text=big_text)


def render_deck(
    plan: AssetPlan,
    image: SourcedImage | None,
    brand: BrandKit,
) -> list[Image.Image]:
    theme = resolve_theme(plan.category, brand)
    size = plan.size
    pages: list[Image.Image] = []
    total = len(plan.slides)
    for i, slide in enumerate(plan.slides, start=1):
        if slide.kind is SlideKind.HERO:
            page = _render_hero(slide, plan, image, brand, theme, size)
        elif slide.kind is SlideKind.TIMELINE:
            page = _render_timeline(slide, brand, theme, size)
        elif slide.kind is SlideKind.STATS:
            page = _render_stats(slide, brand, theme, size)
        elif slide.kind is SlideKind.QUOTE:
            page = _render_quote(slide, brand, theme, size)
        else:
            page = _render_text(slide, brand, theme, size)
        if i > 1:
            blocks.page_counter(page, i, total, theme, brand, _margin(size))
        pages.append(page)
    return pages


def render_infographic(
    plan: AssetPlan, brand: BrandKit, size: tuple[int, int]
) -> Image.Image:
    theme = resolve_theme(plan.category, brand)
    canvas, margin, g = _canvas(theme, size)
    draw = ImageDraw.Draw(canvas)
    w, h = size

    blocks.chip(canvas, margin, margin, theme.label, theme, brand,
                max(16, h // 56))
    y = margin + g * 8
    head_font, head_lines = fit_text(
        draw, plan.headline, brand, round(h * 0.05), w - 2 * margin, max_lines=3
    )
    for line in head_lines:
        draw.text((margin, y), line, font=head_font, fill=theme.text,
                  stroke_width=1, stroke_fill=theme.text)
        y += round(head_font.size * 1.2)
    y += g * 4

    facts = plan.facts[:5]
    if facts:
        gap = g * 3
        card_h = min(round(h * 0.15),
                     (h - y - margin - g * 6 - gap * (len(facts) - 1)) // len(facts))
        for fact in facts:
            blocks.stat_card(canvas, (margin, y, w - margin, y + card_h),
                             fact, theme, brand)
            y += card_h + gap

    blocks.footer(canvas, theme, brand, margin, meta=_meta_line(plan))
    return canvas


# -- slide renderers ---------------------------------------------------------


def _render_hero(
    slide: DeckSlide,
    plan: AssetPlan,
    image: SourcedImage | None,
    brand: BrandKit,
    theme: Theme,
    size: tuple[int, int],
    big_text: bool = False,
) -> Image.Image:
    w, h = size
    margin, g = _margin(size), blocks.grid(size)
    credit = None
    if image and image.data:
        try:
            canvas = treat_hero(cover_crop(image.data, size))
        except RenderError:
            canvas = None
        else:
            canvas = scrim(canvas, start=0.38, strength=0.94)
            credit = image.credit
    else:
        canvas = None
    if canvas is None:
        canvas, _, _ = _canvas(theme, size)
        blocks.watermark_icon(canvas, theme.icon, theme)

    draw = ImageDraw.Draw(canvas)
    blocks.chip(canvas, margin, margin, theme.label, theme, brand,
                max(16, h // 56))

    headline_px = round(h * (0.085 if big_text else 0.06))
    head_font, head_lines = fit_text(
        draw, slide.heading or plan.headline, brand, headline_px,
        w - 2 * margin, max_lines=4 if big_text else 3,
    )
    sub_font, sub_lines = None, []
    if slide.body:
        sub_font, sub_lines = fit_text(
            draw, slide.body, brand, round(headline_px * 0.46),
            w - 2 * margin, max_lines=3, bold=False,
        )

    line_h = round(head_font.size * 1.16)
    sub_h = round(sub_font.size * 1.4) if sub_font else 0
    block_h = len(head_lines) * line_h + (len(sub_lines) * sub_h + g * 2
                                          if sub_lines else 0)
    y = h - margin - g * 4 - block_h

    draw.rectangle((margin, y - g * 3, margin + g * 12, y - g * 3 + max(5, g // 2)),
                   fill=theme.accent)
    for line in head_lines:
        draw.text((margin, y), line, font=head_font, fill=theme.text,
                  stroke_width=2, stroke_fill=theme.text)
        y += line_h
    if sub_lines:
        y += g * 2
        for line in sub_lines:
            draw.text((margin, y), line, font=sub_font, fill=theme.muted)
            y += sub_h

    blocks.footer(canvas, theme, brand, margin, credit=credit,
                  meta=_meta_line(plan))
    return canvas


def _render_text(
    slide: DeckSlide, brand: BrandKit, theme: Theme, size: tuple[int, int]
) -> Image.Image:
    canvas, margin, g = _canvas(theme, size)
    blocks.watermark_icon(canvas, theme.icon, theme)
    draw = ImageDraw.Draw(canvas)
    w, h = size

    y = round(h * 0.3)
    hx = margin + g * 3  # text indent, clear of the accent rule
    if slide.kicker:
        blocks.kicker(canvas, margin, y, slide.kicker, theme, brand,
                      max(18, h // 52), icon=theme.icon)
        y += round(h // 52 * 2.6)
    if slide.heading:
        head_font, head_lines = fit_text(
            draw, slide.heading, brand, round(h * 0.05), w - hx - margin,
            max_lines=3,
        )
        bar_h = round(head_font.size * 1.2 * len(head_lines))
        draw.rectangle((margin, y, margin + max(5, g // 2), y + bar_h),
                       fill=theme.accent)
        for line in head_lines:
            draw.text((hx, y), line, font=head_font, fill=theme.text,
                      stroke_width=1, stroke_fill=theme.text)
            y += round(head_font.size * 1.2)
        y += g * 3
    if slide.body:
        body_font, body_lines = fit_text(
            draw, slide.body, brand, max(22, round(h * 0.03)),
            w - hx - margin, max_lines=7, bold=False,
        )
        for line in body_lines:
            draw.text((hx, y), line, font=body_font, fill=theme.text)
            y += round(body_font.size * 1.55)

    blocks.footer(canvas, theme, brand, margin)
    return canvas


def _render_timeline(
    slide: DeckSlide, brand: BrandKit, theme: Theme, size: tuple[int, int]
) -> Image.Image:
    canvas, margin, g = _canvas(theme, size)
    w, h = size
    y = round(h * 0.14)
    blocks.kicker(canvas, margin, y, slide.kicker or "TIMELINE", theme, brand,
                  max(18, h // 52), icon="clock")
    y += round(h // 52 * 3.2)
    blocks.timeline_block(canvas, margin, y, w - 2 * margin,
                          h - y - _margin(size) - g * 6, slide.timeline,
                          theme, brand)
    blocks.footer(canvas, theme, brand, margin)
    return canvas


def _render_stats(
    slide: DeckSlide, brand: BrandKit, theme: Theme, size: tuple[int, int]
) -> Image.Image:
    canvas, margin, g = _canvas(theme, size)
    w, h = size
    y = round(h * 0.14)
    blocks.kicker(canvas, margin, y, slide.kicker or "KEY NUMBERS", theme, brand,
                  max(18, h // 52), icon="chart")
    y += round(h // 52 * 3.2)

    facts = slide.facts[:4]
    gap = g * 3
    cols = 1 if len(facts) <= 2 else 2
    rows = -(-len(facts) // cols)
    card_w = (w - 2 * margin - gap * (cols - 1)) // cols
    card_h = min(round(h * 0.24),
                 (h - y - margin - g * 6 - gap * (rows - 1)) // rows)
    for i, fact in enumerate(facts):
        cx = margin + (i % cols) * (card_w + gap)
        cy = y + (i // cols) * (card_h + gap)
        blocks.stat_card(canvas, (cx, cy, cx + card_w, cy + card_h),
                         fact, theme, brand)

    blocks.footer(canvas, theme, brand, margin)
    return canvas


def _render_quote(
    slide: DeckSlide, brand: BrandKit, theme: Theme, size: tuple[int, int]
) -> Image.Image:
    canvas, margin, g = _canvas(theme, size)
    draw = ImageDraw.Draw(canvas)
    w, h = size
    quote = slide.quote
    if quote is None:
        return canvas

    from .icons import draw_icon

    s = round(h * 0.05)
    draw_icon(draw, "quote", margin, round(h * 0.22), s, theme.accent)

    y = round(h * 0.22) + s + g * 4
    q_font, q_lines = fit_text(
        draw, f"“{quote.text}”", brand, round(h * 0.042),
        w - 2 * margin, max_lines=7,
    )
    for line in q_lines:
        draw.text((margin, y), line, font=q_font, fill=theme.text)
        y += round(q_font.size * 1.45)
    if quote.attribution:
        y += g * 3
        a_font = load_font(brand, max(20, round(h * 0.024)), bold=False)
        draw.text((margin, y), f"— {quote.attribution}", font=a_font,
                  fill=theme.accent)

    blocks.footer(canvas, theme, brand, margin)
    return canvas


# -- helpers -----------------------------------------------------------------


def _margin(size: tuple[int, int]) -> int:
    return round(size[0] * 0.08)


def _canvas(theme: Theme, size: tuple[int, int]) -> tuple[Image.Image, int, int]:
    return (Image.new("RGB", size, theme.background), _margin(size),
            blocks.grid(size))


def _meta_line(plan: AssetPlan) -> str | None:
    parts = []
    if plan.source_name:
        parts.append(f"Source: {plan.source_name}")
    if plan.reading_minutes:
        parts.append(f"{plan.reading_minutes} min read")
    return "  ·  ".join(parts) if parts else None

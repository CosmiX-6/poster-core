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

# Typographic ratios, expressed as a fraction of the fixed 1920px reference
# canvas height, matching the design system's px table.
_HEADLINE_PX_RATIO = 0.042       # spec: 72-84px headline
_BODY_PX_RATIO = 0.01875         # spec: 34-38px body/dek
_SECTION_LABEL_DIVISOR = 87      # spec: 22px chip/kicker text
_PROGRESS_COUNTER_DIVISOR = 96   # spec: 20px progress counter
_CTA_TEXT_PX_RATIO = 0.015       # spec: 28-30px CTA/link text

# Safe zones, expressed relative to the fixed 1080x1920 reference canvas.
# Top clearance applies to every slide's first content element; bottom/right
# apply only to the cover frame (poster-core's SlideKind.HERO renderer,
# confirmed the sole in-grid preview image), which Instagram's feed UI
# overlays even though it's not an issue once a viewer is inside full-screen
# playback.
_TOP_SAFE_ZONE_RATIO = 180 / 1920
_COVER_BOTTOM_SAFE_ZONE_RATIO = 320 / 1920
_COVER_RIGHT_SAFE_ZONE_RATIO = 100 / 1080

# Reserved action color -- never theme.accent, so a CTA slide's color never
# collides with whatever category chip/accent-bar color is in play.
_CTA_ACCENT = "#22D3EE"


def _top_safe_zone(size: tuple[int, int]) -> int:
    return round(size[1] * _TOP_SAFE_ZONE_RATIO)


def _cover_bottom_safe_zone(size: tuple[int, int]) -> int:
    return round(size[1] * _COVER_BOTTOM_SAFE_ZONE_RATIO)


def _cover_right_safe_zone(size: tuple[int, int]) -> int:
    return round(size[0] * _COVER_RIGHT_SAFE_ZONE_RATIO)


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
    margin = _margin(size)
    pages: list[Image.Image] = []
    total = len(plan.slides)
    for i, slide in enumerate(plan.slides, start=1):
        if slide.kind is SlideKind.HOOK:
            page = _render_hook(slide, plan, image, brand, theme, size)
        elif slide.kind is SlideKind.HERO:
            page = _render_hero(slide, plan, image, brand, theme, size)
        elif slide.kind is SlideKind.EVIDENCE:
            page = _render_evidence(slide, brand, theme, size)
        elif slide.kind is SlideKind.MONEY_FLOW:
            page = _render_money_flow(slide, brand, theme, size)
        elif slide.kind is SlideKind.TIMELINE:
            page = _render_timeline(slide, brand, theme, size)
        elif slide.kind is SlideKind.STATS:
            page = _render_stats(slide, brand, theme, size)
        elif slide.kind is SlideKind.COMPARISON:
            page = _render_comparison(slide, brand, theme, size)
        elif slide.kind is SlideKind.QUOTE:
            page = _render_quote(slide, brand, theme, size)
        elif slide.kind is SlideKind.CONCLUSION:
            page = _render_conclusion(slide, plan, image, brand, theme, size)
        elif slide.kind is SlideKind.CTA:
            page = _render_cta(slide, brand, theme, size)
        else:
            page = _render_text(slide, brand, theme, size)

        blocks.progress_bar(page, i, total, theme)
        blocks.page_counter(page, i, total, theme, brand, margin)
        if slide.transition:
            blocks.transition_hook(page, slide.transition, theme, brand, margin)
        blocks.watermark_logo(page, brand, size)
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
    blocks.watermark_logo(canvas, brand, size)
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
    # The cover-only safe zones (bottom clearance for IG's feed UI, tighter
    # right margin for the like/comment/share icon rail) only apply to the
    # true cover frame -- the standalone COVER asset, big_text=False. The
    # oversized big_text/THUMBNAIL path is a different, narrower design
    # context outside this spec's slide arc, so it keeps its original,
    # bottom-anchored, full-width layout.
    right_margin = margin if big_text else max(margin, _cover_right_safe_zone(size))
    credit = None
    if image and image.data:
        try:
            canvas = treat_hero(cover_crop(image.data, size))
        except RenderError:
            canvas = None
        else:
            canvas = scrim(canvas)
            credit = image.credit
    else:
        canvas = None
    if canvas is None:
        canvas, _, _ = _canvas(theme, size)
        blocks.watermark_icon(canvas, theme.icon, theme)

    draw = ImageDraw.Draw(canvas)
    chip_px = max(16, h // _SECTION_LABEL_DIVISOR)
    chip_y = margin if big_text else max(margin, _top_safe_zone(size) - g * 10)
    blocks.chip(canvas, margin, chip_y, theme.label, theme, brand, chip_px)

    headline_px = round(h * (0.085 if big_text else _HEADLINE_PX_RATIO))
    head_font, head_lines = fit_text(
        draw, slide.heading or plan.headline, brand, headline_px,
        w - margin - right_margin, max_lines=4 if big_text else 3,
    )
    sub_font, sub_lines = None, []
    if slide.body:
        sub_px = round(headline_px * 0.46) if big_text else round(h * _BODY_PX_RATIO)
        sub_font, sub_lines = fit_text(
            draw, slide.body, brand, sub_px,
            w - margin - right_margin, max_lines=3, bold=False,
        )

    line_h = round(head_font.size * 1.16)
    sub_h = round(sub_font.size * 1.4) if sub_font else 0
    block_h = len(head_lines) * line_h + (len(sub_lines) * sub_h + g * 2
                                          if sub_lines else 0)
    if big_text:
        y = h - margin - g * 4 - block_h
    else:
        # Vertically centered rather than bottom-anchored, so the top of
        # the frame doesn't read as dead space -- clamped so the block
        # never intrudes on the top-180px or bottom-320px safe zones.
        top_bound = max(chip_y + chip_px + g * 6, _top_safe_zone(size))
        bottom_bound = h - _cover_bottom_safe_zone(size)
        y = max(top_bound, min((h - block_h) // 2, bottom_bound - block_h))

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
    blocks.watermark_logo(canvas, brand, size)
    return canvas


def _dramatic_backdrop(
    image: SourcedImage | None, theme: Theme, size: tuple[int, int],
) -> tuple[Image.Image | None, str | None]:
    """Heavily darkened, near full-bleed hero photography for the cold-open
    and closing slides — the two moments meant to feel most cinematic."""
    if not (image and image.data):
        return None, None
    try:
        canvas = treat_hero(cover_crop(image.data, size))
    except RenderError:
        return None, None
    canvas = scrim(canvas)
    return canvas, image.credit


def _render_hook(
    slide: DeckSlide,
    plan: AssetPlan,
    image: SourcedImage | None,
    brand: BrandKit,
    theme: Theme,
    size: tuple[int, int],
) -> Image.Image:
    """Cold open: a category chip for consistency with every other slide,
    then just enough tension to make the first swipe happen. Never repeats
    the headline verbatim."""
    w, h = size
    margin, g = _margin(size), blocks.grid(size)
    canvas, credit = _dramatic_backdrop(image, theme, size)
    if canvas is None:
        canvas, _, _ = _canvas(theme, size)
        blocks.watermark_icon(canvas, theme.icon, theme)

    draw = ImageDraw.Draw(canvas)
    chip_px = max(16, h // _SECTION_LABEL_DIVISOR)
    chip_y = max(margin, _top_safe_zone(size) - g * 10)
    blocks.chip(canvas, margin, chip_y, theme.label, theme, brand, chip_px)

    headline_px = round(h * _HEADLINE_PX_RATIO)
    head_font, head_lines = fit_text(
        draw, slide.heading or plan.headline, brand, headline_px,
        w - 2 * margin, max_lines=5,
    )
    line_h = round(head_font.size * 1.22)
    block_h = len(head_lines) * line_h
    top_bound = max(chip_y + chip_px + g * 6, _top_safe_zone(size))
    y = max(top_bound, (h - block_h) // 2)
    for line in head_lines:
        draw.text((margin, y), line, font=head_font, fill=theme.text,
                  stroke_width=2, stroke_fill=theme.text)
        y += line_h

    cue_font = load_font(brand, max(16, h // 58), bold=False)
    cue = "SWIPE TO UNCOVER THE STORY"
    draw.text((margin, h - margin - cue_font.size), cue, font=cue_font,
              fill=theme.accent)
    if credit:
        tw = draw.textlength(cue, font=cue_font)
        draw.text((margin + tw + round(cue_font.size * 1.2), h - margin - cue_font.size),
                  credit, font=cue_font, fill=theme.muted)
    return canvas


def _render_evidence(
    slide: DeckSlide, brand: BrandKit, theme: Theme, size: tuple[int, int]
) -> Image.Image:
    """Case-file styled chapter: a framed exhibit card instead of the plain
    left-accented prose used by _render_text, so two info slides in a row
    never look identical."""
    canvas, margin, g = _canvas(theme, size)
    blocks.watermark_icon(canvas, theme.icon, theme)
    draw = ImageDraw.Draw(canvas)
    w, h = size

    if slide.kicker:
        blocks.kicker(canvas, margin, max(round(h * 0.08), _top_safe_zone(size)),
                      slide.kicker, theme, brand,
                      max(18, h // _SECTION_LABEL_DIVISOR), icon=theme.icon)

    pad = g * 5
    max_w = w - 2 * margin - 2 * pad

    head_font, head_lines = None, []
    if slide.heading:
        head_font, head_lines = fit_text(draw, slide.heading, brand,
                                         round(h * _HEADLINE_PX_RATIO), max_w, max_lines=3)
    body_font, body_lines = None, []
    if slide.body:
        body_font, body_lines = fit_text(draw, slide.body, brand,
                                         max(20, round(h * _BODY_PX_RATIO)), max_w,
                                         max_lines=7, bold=False)

    # Size the card to its content instead of a fixed screen fraction, so a
    # short fact doesn't leave a slab of dead space inside the frame.
    content_h = pad * 2
    if head_lines:
        content_h += len(head_lines) * round(head_font.size * 1.25) + g * 2
    if body_lines:
        content_h += len(body_lines) * round(body_font.size * 1.5)
    content_h = max(content_h, round(h * 0.16))
    content_h = min(content_h, round(h * 0.55))

    card_top = round(h * 0.18)
    card_rect = (margin, card_top, w - margin, card_top + content_h)
    blocks.evidence_frame(canvas, card_rect, theme)
    blocks.chip(canvas, card_rect[0] + g * 2, card_rect[1] - round(h * 0.028),
                "EVIDENCE", theme, brand, max(14, h // 64))

    tx, ty = card_rect[0] + pad, card_rect[1] + pad
    for line in head_lines:
        draw.text((tx, ty), line, font=head_font, fill=theme.text)
        ty += round(head_font.size * 1.25)
    if head_lines:
        ty += g * 2
    for line in body_lines:
        draw.text((tx, ty), line, font=body_font, fill=theme.muted)
        ty += round(body_font.size * 1.5)

    blocks.footer(canvas, theme, brand, margin)
    return canvas


def _render_money_flow(
    slide: DeckSlide, brand: BrandKit, theme: Theme, size: tuple[int, int]
) -> Image.Image:
    canvas, margin, g = _canvas(theme, size)
    w, h = size
    y = round(h * 0.14)
    blocks.kicker(canvas, margin, y, slide.kicker or "FOLLOW THE MONEY", theme,
                  brand, max(18, h // _SECTION_LABEL_DIVISOR), icon="coin")
    y += round(h // 52 * 3.2)
    blocks.money_flow_block(canvas, margin, y, w - 2 * margin,
                            h - y - _margin(size) - g * 8, slide.money_trail,
                            theme, brand)
    blocks.footer(canvas, theme, brand, margin)
    return canvas


def _render_comparison(
    slide: DeckSlide, brand: BrandKit, theme: Theme, size: tuple[int, int]
) -> Image.Image:
    canvas, margin, g = _canvas(theme, size)
    w, h = size
    if slide.comparison is None:
        return canvas
    y = round(h * 0.14)
    blocks.kicker(canvas, margin, y, slide.kicker or "BEFORE / AFTER", theme,
                  brand, max(18, h // _SECTION_LABEL_DIVISOR), icon="chart")
    y += round(h // 52 * 3.2)
    blocks.comparison_block(canvas, margin, y, w - 2 * margin,
                            slide.comparison, theme, brand)
    blocks.footer(canvas, theme, brand, margin)
    return canvas


def _render_conclusion(
    slide: DeckSlide,
    plan: AssetPlan,
    image: SourcedImage | None,
    brand: BrandKit,
    theme: Theme,
    size: tuple[int, int],
) -> Image.Image:
    """Deliberate close: the same cinematic backdrop treatment as the hook,
    bookending the story, with the closing line as the sole focus."""
    w, h = size
    margin, g = _margin(size), blocks.grid(size)
    canvas, credit = _dramatic_backdrop(image, theme, size)
    if canvas is None:
        canvas, _, _ = _canvas(theme, size)
        blocks.watermark_icon(canvas, theme.icon, theme)

    draw = ImageDraw.Draw(canvas)
    chip_y = max(margin, _top_safe_zone(size) - g * 10)
    blocks.chip(canvas, margin, chip_y, slide.kicker or "WHAT HAPPENS NEXT",
                theme, brand, max(16, h // _SECTION_LABEL_DIVISOR))

    # Functions as this slide's headline (the sole text on it), not a
    # supporting dek, so it takes the headline ratio rather than the body one.
    body_font, body_lines = fit_text(
        draw, slide.body or "", brand, round(h * _HEADLINE_PX_RATIO * 0.88),
        w - 2 * margin, max_lines=6
    )
    line_h = round(body_font.size * 1.3)
    block_h = len(body_lines) * line_h
    top_bound = max(chip_y + max(16, h // _SECTION_LABEL_DIVISOR) + g * 6, _top_safe_zone(size))
    y = max(top_bound, (h - block_h) // 2)
    for line in body_lines:
        draw.text((margin, y), line, font=body_font, fill=theme.text,
                  stroke_width=1, stroke_fill=theme.text)
        y += line_h

    blocks.footer(canvas, theme, brand, margin, credit=credit,
                  meta=_meta_line(plan))
    return canvas


def _render_cta(
    slide: DeckSlide, brand: BrandKit, theme: Theme, size: tuple[int, int]
) -> Image.Image:
    """Closing follow/CTA slide: always the deck's last slide. No chip, no
    category accent -- CTA copy is drawn in the reserved action color
    (_CTA_ACCENT), never theme.accent, so a tappable-feeling prompt always
    reads differently from a category chip or accent bar."""
    canvas, margin, g = _canvas(theme, size)
    draw = ImageDraw.Draw(canvas)
    w, h = size

    head_font, head_lines = fit_text(
        draw, slide.heading or "Follow for more", brand,
        round(h * _HEADLINE_PX_RATIO * 0.8), w - 2 * margin, max_lines=3,
    )
    body_font, body_lines = ([], []) if not slide.body else fit_text(
        draw, slide.body, brand, round(h * _BODY_PX_RATIO), w - 2 * margin,
        max_lines=3, bold=False,
    )

    line_h = round(head_font.size * 1.2)
    body_h = round(body_font.size * 1.4) if body_lines else 0
    block_h = len(head_lines) * line_h + (len(body_lines) * body_h + g * 3 if body_lines else 0)
    y = (h - block_h) // 2
    for line in head_lines:
        tw = draw.textlength(line, font=head_font)
        draw.text(((w - tw) / 2, y), line, font=head_font, fill=_CTA_ACCENT)
        y += line_h
    if body_lines:
        y += g * 3
        for line in body_lines:
            tw = draw.textlength(line, font=body_font)
            draw.text(((w - tw) / 2, y), line, font=body_font, fill=theme.muted)
            y += body_h

    blocks.footer(canvas, theme, brand, margin)
    return canvas


def _render_text(
    slide: DeckSlide, brand: BrandKit, theme: Theme, size: tuple[int, int]
) -> Image.Image:
    canvas, margin, g = _canvas(theme, size)
    blocks.watermark_icon(canvas, theme.icon, theme)
    draw = ImageDraw.Draw(canvas)
    w, h = size

    y = max(round(h * 0.3), _top_safe_zone(size))
    hx = margin + g * 3  # text indent, clear of the accent rule
    if slide.kicker:
        blocks.kicker(canvas, margin, y, slide.kicker, theme, brand,
                      max(18, h // _SECTION_LABEL_DIVISOR), icon=theme.icon)
        y += round(h // 52 * 2.6)
    if slide.heading:
        head_font, head_lines = fit_text(
            draw, slide.heading, brand, round(h * _HEADLINE_PX_RATIO), w - hx - margin,
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
            draw, slide.body, brand, max(22, round(h * _BODY_PX_RATIO)),
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
                  max(18, h // _SECTION_LABEL_DIVISOR), icon="clock")
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
                  max(18, h // _SECTION_LABEL_DIVISOR), icon="chart")
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
    return round(size[0] * (64 / 1080))  # spec: flat 64px outer margin


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

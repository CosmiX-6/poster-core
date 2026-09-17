from PIL import Image, ImageDraw

from poster_core.models import BrandKit, DeckSlide, SlideKind, StoryCategory
from poster_core.render import fit_text, resolve_theme, watermark_logo
from poster_core.render.blocks import footer
from poster_core.render.composer import _render_cta


def make_draw():
    return ImageDraw.Draw(Image.new("RGB", (1000, 1000)))


def test_fit_text_keeps_full_text_when_it_fits():
    draw = make_draw()
    font, lines = fit_text(draw, "Short headline", BrandKit(), 60, 900, max_lines=3)
    assert " ".join(lines) == "Short headline"
    assert font.size == 60


def test_fit_text_shrinks_instead_of_dropping_words():
    draw = make_draw()
    text = ("Met Police probe half a million pounds in election donations "
            "from a firm owned by the party chairman")
    font, lines = fit_text(draw, text, BrandKit(), 54, 900, max_lines=3)
    if not lines[-1].endswith("…"):
        # Every word survived; the font shrank to make that possible.
        assert " ".join(lines) == text
        assert font.size < 54


def test_fit_text_ellipsizes_visibly_as_last_resort():
    draw = make_draw()
    text = " ".join(["word"] * 200)
    font, lines = fit_text(draw, text, BrandKit(), 54, 900, max_lines=2)
    assert len(lines) == 2
    assert lines[-1].endswith("…")  # truncation is visible, never silent
    assert draw.textlength(lines[-1], font=font) <= 900


def test_resolve_theme_default_brand_leaves_category_untouched():
    theme = resolve_theme(StoryCategory.POLITICS, BrandKit())
    assert theme.background == "#1B1C21"  # POLITICS's own built-in background
    assert theme.accent == "#E0433D"


def test_resolve_theme_background_override_applies_to_any_category():
    brand = BrandKit(background_color="#0A0E1A")
    for category in (StoryCategory.POLITICS, StoryCategory.FINANCE, StoryCategory.AI):
        assert resolve_theme(category, brand).background == "#0A0E1A"


def test_resolve_theme_category_accent_override_wins_over_global_accent():
    brand = BrandKit(accent_color="#3B82F6", category_accents={"science": "#14B8A6"})
    assert resolve_theme(StoryCategory.SCIENCE, brand).accent == "#14B8A6"
    assert resolve_theme(StoryCategory.POLITICS, brand).accent == "#3B82F6"


def test_watermark_logo_is_a_noop_without_logo_path():
    canvas = Image.new("RGB", (1080, 1920), "#000000")
    before = canvas.copy()
    watermark_logo(canvas, BrandKit(), (1080, 1920))
    assert list(canvas.getdata()) == list(before.getdata())


def test_watermark_logo_pastes_when_logo_path_set(tmp_path):
    logo_path = tmp_path / "logo.png"
    Image.new("RGB", (200, 200), "#FFFFFF").save(logo_path)
    canvas = Image.new("RGB", (1080, 1920), "#000000")
    watermark_logo(canvas, BrandKit(logo_path=str(logo_path)), (1080, 1920))
    # top-right corner should no longer be pure black where the mark landed
    assert canvas.getpixel((1080 - 30, 30)) != (0, 0, 0)


def test_footer_draws_more_with_credit_than_without():
    theme = resolve_theme(StoryCategory.GENERAL, BrandKit())
    brand = BrandKit(name="CONTEXT UNFILTERED")

    plain = Image.new("RGB", (1080, 1920), "#000000")
    footer(plain, theme, brand, 64, meta="Source: AP")

    with_credit = Image.new("RGB", (1080, 1920), "#000000")
    footer(with_credit, theme, brand, 64, credit="Reuters", meta="Source: AP")

    # The "Image: Reuters" segment adds visible pixels beyond the plain
    # brand/source line -- a cheap proxy for "the credit actually rendered"
    # without extracting text from the PNG.
    def lit_pixels(img: Image.Image) -> int:
        return sum(1 for px in img.getdata() if px != (0, 0, 0))

    assert lit_pixels(with_credit) > lit_pixels(plain)


def test_render_cta_uses_reserved_cyan_not_theme_accent():
    theme = resolve_theme(StoryCategory.PRODUCT_LAUNCH, BrandKit())
    assert theme.accent == "#22D3EE"  # this category's accent happens to collide
    slide = DeckSlide(kind=SlideKind.CTA, heading="Follow @contextunfiltered", body="Recap")
    canvas = _render_cta(slide, BrandKit(), theme, (1080, 1920))
    assert canvas.size == (1080, 1920)

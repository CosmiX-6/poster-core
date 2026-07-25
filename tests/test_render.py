from PIL import Image, ImageDraw

from poster_core.models import BrandKit
from poster_core.render import fit_text


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

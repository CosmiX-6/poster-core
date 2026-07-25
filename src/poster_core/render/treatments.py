"""Image treatments: make photography support the text instead of fighting it."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


def treat_hero(img: Image.Image) -> Image.Image:
    """Editorial hero treatment: gentle contrast/saturation lift, film grain
    and a vignette that pulls the eye towards the centre."""
    img = ImageEnhance.Contrast(img).enhance(1.07)
    img = ImageEnhance.Color(img).enhance(1.05)
    img = _vignette(img, strength=0.38)
    img = _grain(img, opacity=0.045)
    return img


def scrim(img: Image.Image, start: float = 0.4, strength: float = 0.92,
          color: str = "#000000") -> Image.Image:
    """Darken the lower part of the image with a smooth gradient so overlaid
    text stays legible."""
    w, h = img.size
    mask = Image.new("L", (1, h), 0)
    y0 = int(h * start)
    for y in range(y0, h):
        mask.putpixel((0, y), int(255 * strength * ((y - y0) / (h - y0)) ** 1.4))
    overlay = Image.new("RGB", (w, h), color)
    img.paste(overlay, (0, 0), mask.resize((w, h)))
    return img


def _vignette(img: Image.Image, strength: float) -> Image.Image:
    w, h = img.size
    mask = Image.new("L", (w // 4, h // 4), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((-w // 16, -h // 16, w // 4 + w // 16, h // 4 + h // 16),
              fill=int(255 * strength))
    mask = mask.filter(ImageFilter.GaussianBlur(min(w, h) // 24)).resize((w, h))
    black = Image.new("RGB", (w, h), "#000000")
    # Invert: edges darken, centre stays.
    from PIL import ImageOps

    img.paste(black, (0, 0), ImageOps.invert(mask))
    return img


def _grain(img: Image.Image, opacity: float) -> Image.Image:
    w, h = img.size
    noise = Image.effect_noise((w // 2, h // 2), 24).resize((w, h))
    grain = Image.merge("RGB", (noise, noise, noise))
    return Image.blend(img, grain, opacity)

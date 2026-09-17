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


# Bottom-to-top stops as (fraction of height from the bottom, alpha),
# matching the design system's
# linear-gradient(to top, rgba(10,14,26,.95) 0%, rgba(10,14,26,.85) 35%, rgba(10,14,26,0) 65%)
# -- a near-opaque band low in frame, fading out by two-thirds up, so text
# stays legible regardless of what's in the photo rather than relying on a
# generic vignette.
_DEFAULT_SCRIM_STOPS: tuple[tuple[float, float], ...] = ((0.0, 0.95), (0.35, 0.85), (0.65, 0.0))


def scrim(img: Image.Image, color: str = "#0A0E1A",
          stops: tuple[tuple[float, float], ...] = _DEFAULT_SCRIM_STOPS) -> Image.Image:
    """Darken the image with a piecewise-linear gradient (from the bottom
    edge upward) so overlaid text stays legible regardless of the photo."""
    w, h = img.size
    mask = Image.new("L", (1, h), 0)
    for y in range(h):
        frac_from_bottom = (h - 1 - y) / max(h - 1, 1)
        mask.putpixel((0, y), round(255 * _alpha_at(frac_from_bottom, stops)))
    overlay = Image.new("RGB", (w, h), color)
    img.paste(overlay, (0, 0), mask.resize((w, h)))
    return img


def _alpha_at(frac: float, stops: tuple[tuple[float, float], ...]) -> float:
    """Linear interpolation between consecutive (fraction, alpha) stops.
    Below the first stop or above the last, holds that stop's value."""
    if frac <= stops[0][0]:
        return stops[0][1]
    for (f0, a0), (f1, a1) in zip(stops, stops[1:]):
        if frac <= f1:
            t = (frac - f0) / (f1 - f0)
            return a0 + (a1 - a0) * t
    return stops[-1][1]


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

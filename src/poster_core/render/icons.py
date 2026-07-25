"""Minimal line-icon set drawn with Pillow primitives.

Icons are drawn into a bounding box (x, y, s) where s is the side length.
They are deliberately simple geometric marks — closer to an editorial
pictogram than a detailed illustration — so they stay crisp at any size.
"""

from __future__ import annotations

from PIL import ImageDraw


def draw_icon(
    draw: ImageDraw.ImageDraw,
    kind: str,
    x: int,
    y: int,
    s: int,
    color: str,
    width: int | None = None,
) -> None:
    w = width or max(2, s // 10)
    fn = _ICONS.get(kind, _icon_pin)
    fn(draw, x, y, s, color, w)


def _icon_chart(d, x, y, s, c, w):
    bars = [(0.08, 0.5), (0.4, 0.3), (0.72, 0.08)]
    for fx, fy in bars:
        d.rectangle((x + fx * s, y + fy * s, x + fx * s + 0.2 * s, y + s), fill=c)


def _icon_alert(d, x, y, s, c, w):
    d.polygon([(x + s / 2, y), (x + s, y + s), (x, y + s)], outline=c, width=w)
    d.line((x + s / 2, y + 0.35 * s, x + s / 2, y + 0.68 * s), fill=c, width=w)
    r = w * 0.7
    d.ellipse((x + s / 2 - r, y + 0.8 * s - r, x + s / 2 + r, y + 0.8 * s + r), fill=c)


def _icon_magnify(d, x, y, s, c, w):
    r = 0.62 * s
    d.ellipse((x, y, x + r, y + r), outline=c, width=w)
    d.line((x + 0.75 * r, y + 0.75 * r, x + s, y + s), fill=c, width=w + 1)


def _icon_building(d, x, y, s, c, w):
    d.rectangle((x + 0.15 * s, y, x + 0.85 * s, y + s), outline=c, width=w)
    for fy in (0.2, 0.45, 0.7):
        for fx in (0.32, 0.56):
            d.rectangle(
                (x + fx * s, y + fy * s, x + fx * s + 0.12 * s, y + fy * s + 0.12 * s),
                fill=c,
            )


def _icon_chip(d, x, y, s, c, w):
    d.rectangle((x + 0.2 * s, y + 0.2 * s, x + 0.8 * s, y + 0.8 * s), outline=c, width=w)
    d.rectangle((x + 0.4 * s, y + 0.4 * s, x + 0.6 * s, y + 0.6 * s), fill=c)
    for f in (0.3, 0.5, 0.7):
        d.line((x + f * s, y, x + f * s, y + 0.2 * s), fill=c, width=w)
        d.line((x + f * s, y + 0.8 * s, x + f * s, y + s), fill=c, width=w)
        d.line((x, y + f * s, x + 0.2 * s, y + f * s), fill=c, width=w)
        d.line((x + 0.8 * s, y + f * s, x + s, y + f * s), fill=c, width=w)


def _icon_ball(d, x, y, s, c, w):
    d.ellipse((x, y, x + s, y + s), outline=c, width=w)
    d.arc((x - 0.5 * s, y, x + 0.5 * s, y + s), -60, 60, fill=c, width=w)
    d.arc((x + 0.5 * s, y, x + 1.5 * s, y + s), 120, 240, fill=c, width=w)


def _icon_flask(d, x, y, s, c, w):
    d.line((x + 0.35 * s, y, x + 0.35 * s, y + 0.4 * s), fill=c, width=w)
    d.line((x + 0.65 * s, y, x + 0.65 * s, y + 0.4 * s), fill=c, width=w)
    d.polygon(
        [
            (x + 0.35 * s, y + 0.4 * s),
            (x + 0.65 * s, y + 0.4 * s),
            (x + 0.9 * s, y + s),
            (x + 0.1 * s, y + s),
        ],
        outline=c,
        width=w,
    )
    d.polygon(
        [(x + 0.28 * s, y + 0.72 * s), (x + 0.72 * s, y + 0.72 * s),
         (x + 0.82 * s, y + 0.94 * s), (x + 0.18 * s, y + 0.94 * s)],
        fill=c,
    )


def _icon_heart(d, x, y, s, c, w):
    t = 0.28 * s
    d.pieslice((x, y, x + 0.55 * s, y + 0.55 * s), 130, 315, fill=c)
    d.pieslice((x + 0.45 * s, y, x + s, y + 0.55 * s), 225, 50, fill=c)
    d.polygon(
        [(x + 0.06 * s, y + t + 0.12 * s), (x + 0.94 * s, y + t + 0.12 * s),
         (x + s / 2, y + s)],
        fill=c,
    )


def _icon_clock(d, x, y, s, c, w):
    d.ellipse((x, y, x + s, y + s), outline=c, width=w)
    d.line((x + s / 2, y + 0.22 * s, x + s / 2, y + s / 2), fill=c, width=w)
    d.line((x + s / 2, y + s / 2, x + 0.72 * s, y + 0.64 * s), fill=c, width=w)


def _icon_quote(d, x, y, s, c, w):
    for fx in (0.0, 0.55):
        d.pieslice((x + fx * s, y, x + (fx + 0.45) * s, y + 0.9 * s), 90, 270, fill=c)
        d.rectangle(
            (x + (fx + 0.225) * s, y + 0.45 * s, x + (fx + 0.45) * s, y + s), fill=c
        )


def _icon_coin(d, x, y, s, c, w):
    d.ellipse((x, y, x + s, y + s), outline=c, width=w)
    d.ellipse((x + 0.28 * s, y + 0.28 * s, x + 0.72 * s, y + 0.72 * s), outline=c, width=w)


def _icon_pin(d, x, y, s, c, w):
    d.ellipse((x + 0.2 * s, y, x + 0.8 * s, y + 0.6 * s), outline=c, width=w)
    d.polygon(
        [(x + 0.3 * s, y + 0.52 * s), (x + 0.7 * s, y + 0.52 * s), (x + s / 2, y + s)],
        fill=c,
    )


def _icon_calendar(d, x, y, s, c, w):
    d.rectangle((x, y + 0.12 * s, x + s, y + s), outline=c, width=w)
    d.line((x, y + 0.34 * s, x + s, y + 0.34 * s), fill=c, width=w)
    d.line((x + 0.28 * s, y, x + 0.28 * s, y + 0.2 * s), fill=c, width=w)
    d.line((x + 0.72 * s, y, x + 0.72 * s, y + 0.2 * s), fill=c, width=w)
    for fy in (0.5, 0.72):
        for fx in (0.2, 0.45, 0.7):
            d.rectangle(
                (x + fx * s, y + fy * s, x + fx * s + 0.1 * s, y + fy * s + 0.1 * s),
                fill=c,
            )


def _icon_box(d, x, y, s, c, w):
    d.polygon(
        [(x + s / 2, y), (x + s, y + 0.25 * s), (x + s, y + 0.75 * s),
         (x + s / 2, y + s), (x, y + 0.75 * s), (x, y + 0.25 * s)],
        outline=c,
        width=w,
    )
    d.line((x, y + 0.25 * s, x + s / 2, y + 0.5 * s), fill=c, width=w)
    d.line((x + s, y + 0.25 * s, x + s / 2, y + 0.5 * s), fill=c, width=w)
    d.line((x + s / 2, y + 0.5 * s, x + s / 2, y + s), fill=c, width=w)


_ICONS = {
    "chart": _icon_chart,
    "alert": _icon_alert,
    "magnify": _icon_magnify,
    "building": _icon_building,
    "chip": _icon_chip,
    "ball": _icon_ball,
    "flask": _icon_flask,
    "heart": _icon_heart,
    "clock": _icon_clock,
    "quote": _icon_quote,
    "coin": _icon_coin,
    "pin": _icon_pin,
    "calendar": _icon_calendar,
    "box": _icon_box,
}

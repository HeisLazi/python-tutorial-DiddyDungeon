"""A small pixel-art toolkit for the Home sprites (Pillow only).

The first Home sprites were built from rectangles, which looks blocky at the
larger Castlevania scale. This adds shaped, shaded forms:

  rows(y0, y1, left, right, tones)   fill a silhouette described row by row
                                     (left/right are functions of y), cel-shaded
                                     across its width: lit left, shaded right
  line(p, q, c)                      a 1px Bresenham line
  strand(...)                        a tapering, wavy lock of hair (animatable)
  outline()                          a 1px dark outline around every shape

Colours are looked up in a palette dict by name, so a skin is just a palette.
"""

from __future__ import annotations

import math

from PIL import Image


class Canvas:
    def __init__(self, w, h, palette):
        self.w, self.h, self.p = w, h, palette
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.px_ = self.img.load()

    # ── basics ────────────────────────────────────────────────────────────
    def rgba(self, c):
        if c is None:
            return (0, 0, 0, 0)
        if isinstance(c, str):
            r, g, b = self.p[c]
            return (r, g, b, 255)
        return c

    def px(self, x, y, c):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px_[x, y] = self.rgba(c)

    def get(self, x, y):
        return self.px_[x, y] if 0 <= x < self.w and 0 <= y < self.h else (0, 0, 0, 0)

    def rect(self, x0, y0, x1, y1, c):
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.px(x, y, c)

    def hline(self, x0, x1, y, c):
        self.rect(x0, y, x1, y, c)

    def vline(self, x, y0, y1, c):
        self.rect(x, y0, x, y1, c)

    def line(self, p, q, c):
        (x0, y0), (x1, y1) = p, q
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(int(steps) + 1):
            t = i / steps
            self.px(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, c)

    def disc(self, cx, cy, r, c):
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + 0.5:
                    self.px(x, y, c)

    # ── shaped, shaded forms ──────────────────────────────────────────────
    def rows(self, y0, y1, left, right, tones, split=(0.28, 0.72), rim=True, keep=None):
        """Fill rows y0..y1 between left(y) and right(y), cel-shaded across the width.

        tones = (light, mid, dark) palette names. `split` are the shading cut points
        (0 = left edge, 1 = right edge). `rim` lightens the very first pixel of each row.
        `keep` (a set of colours) means only paint over transparent pixels if given
        a falsy value is ignored; used to layer without overwriting.
        """
        light, mid, dark = tones
        for y in range(int(y0), int(y1) + 1):
            xl, xr = left(y), right(y)
            if xr < xl:
                continue
            xl, xr = int(round(xl)), int(round(xr))
            width = max(1, xr - xl)
            for x in range(xl, xr + 1):
                t = (x - xl) / width
                tone = light if t < split[0] else (mid if t < split[1] else dark)
                if rim and x == xl:
                    tone = light
                self.px(x, y, tone)

    def mirror_rows(self, y0, y1, left, right, tones, **kw):
        """rows() plus its mirror image about the centre line."""
        self.rows(y0, y1, left, right, tones, **kw)
        self.rows(y0, y1, lambda y: self.w - 1 - right(y), lambda y: self.w - 1 - left(y), (tones[2], tones[1], tones[0]), **kw)

    def strand(self, x0, y0, length, widths, wave, tones, side=1):
        """A tapering lock of hair from (x0, y0) downward. wave(y_index) is the
        sideways displacement (this is what animates). widths = (top, bottom)."""
        light, mid, dark = tones
        for i in range(length):
            t = i / max(1, length - 1)
            w = widths[0] + (widths[1] - widths[0]) * t
            cx = x0 + wave(i) * side
            xl, xr = int(round(cx - w / 2)), int(round(cx + w / 2))
            for x in range(xl, xr + 1):
                span = max(1, xr - xl)
                tone = light if (x - xl) / span < 0.34 else (mid if (x - xl) / span < 0.72 else dark)
                self.px(x, y0 + i, tone)

    def outline(self, color="line", inner=None):
        out = self.img.copy()
        dst = out.load()
        for y in range(self.h):
            for x in range(self.w):
                if self.px_[x, y][3]:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and self.px_[nx, ny][3]:
                        dst[x, y] = self.rgba(color)
                        break
        self.img = out
        self.px_ = out.load()
        return self


def wave(amp, speed, phase, k=0.5):
    """A sideways wave for hair and cloth: wave(i) -> offset in px for row i."""
    return lambda i: amp * math.sin(phase * speed + i * k) * (i / 10.0 if i < 10 else 1.0)

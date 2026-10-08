#!/usr/bin/env python3
"""Make the link preview card: public/og.png, the image a chat or a feed shows
when someone pastes a link to the site.

A crawler does not run WebGL, so it never sees the hero. This runs the hero
fragment shader again on the CPU - the same rotation, crop, two liquify passes
and hue shift that src/components/hero/renderer.ts does - at the 1200 x 630 the
Open Graph spec asks for, with time and pointer held at their opening values.
What comes out is the frame a visitor sees before they touch anything. The name
goes over it the way the hero sets it over the page.

The card must stay in step with the shader: if the hue, the liquify constants
or hueShift in HeroBackground.svelte change, run this again.

Run from anywhere:  python3 scripts/og-art/make-og.py
Needs Pillow (with AVIF), numpy and fontTools.
"""

from io import BytesIO
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TEXTURE = ROOT / "src" / "assets" / "hero.avif"
# The .woff, not the .woff2 beside it: fontTools unpacks woff with zlib alone.
FONT = ROOT / "node_modules" / "@fontsource" / "petrona" / "files" / "petrona-latin-400-normal.woff"
OUT = ROOT / "public" / "og.png"

W, H = 1200, 630  # the size Open Graph asks for, and the largest X renders

# Every one of these is read off the shader, and means nothing on its own.
HUE_SHIFT = 0.4  # the hueShift prop HeroBackground.svelte passes in
IMAGE_ASPECT = 1530.0 / 1122.0  # the photo, on its side, as the shader has it written
MOUSE = (0.5, 0.5)  # the pointer before it has moved
TIME = 0.0  # the first frame

INK = (44, 56, 48)  # --color-base
MUTED = (122, 153, 136)  # --color-muted
# The hero's own h1 at this width: Petrona, text-9xl (8rem), tracking-wide (0.025em). The line
# below it borrows the tracking the site gives its muted captions.
NAME = ("aaron ye", 128, 0.025, INK)
TAGLINE = ("software engineer · cs @ uwaterloo", 28, 0.08, MUTED)


def rot(st, angle):
    """st * rot(angle), as GLSL multiplies a row vector by mat2."""
    c, s = np.cos(angle), np.sin(angle)
    return np.stack([st[0] * c - st[1] * s, st[0] * s + st[1] * c])


def liquify(st, rot_angle, freq, amplitude, center, aspect):
    """The shader's liquify(), at u_time 0. Five rotations, each warping the
    coordinate by a wave whose frequency climbs with the turn count."""
    st = np.stack([st[0] - center[0], st[1] - center[1]])
    st = np.stack([st[0] * aspect, st[1]])
    st = rot(st, rot_angle * 2.0 * np.pi)

    for i in range(1, 6):
        st = rot(st, i / 5.0 * np.pi * 2.0)
        ff = i * freq
        x = st[0] + amplitude * np.cos(ff * st[1] + TIME)
        y = st[1] + amplitude * np.sin(ff * x + TIME)  # on the x the line above just wrote
        st = np.stack([x, y])

    st = rot(st, rot_angle * -2.0 * np.pi)
    return np.stack([st[0] / aspect + center[0], st[1] + center[1]])


def warp(w, h):
    """The texture coordinate each pixel of a w x h canvas reads from."""
    aspect = w / h

    # gl_FragCoord / u_resolution: x from the left, y from the bottom
    xs = (np.arange(w) + 0.5) / w
    ys = (np.arange(h) + 0.5) / h
    uv_x, uv_y = np.meshgrid(xs, ys[::-1])  # row 0 is the top of the canvas

    # Landscape: the photo is turned a quarter turn, then cropped to the canvas
    tex = np.stack([1.0 - uv_y, uv_x])
    scale = aspect / IMAGE_ASPECT  # a 1.91:1 canvas is always wider than the photo on its side
    tex[0] = (tex[0] - 0.5) / scale + 0.5
    tex[1] = 1.0 - tex[1]  # mirrored

    center1 = (0.5 + (MOUSE[0] - 0.5) * 0.3, 0.5 + (MOUSE[1] - 0.5) * 0.3)
    freq1 = 5.0 * (0.14 + 0.1)
    amp1 = 0.34 * (0.2 + (0.2 / (0.14 + 0.05) - 0.2) * 0.25) * 0.4
    uv1 = tex + (liquify(tex, 0.8807, freq1, amp1, center1, aspect) - tex) * 0.15

    center2 = (0.5 + (MOUSE[0] - 0.5) * 0.2, 0.5 + (MOUSE[1] - 0.5) * 0.2)
    freq2 = 5.0 * (1.27 + 0.1)
    amp2 = 0.23 * (0.2 + (0.2 / (1.27 + 0.05) - 0.2) * 0.25) * 0.2
    uv2 = uv1 + (liquify(uv1, 0.121, freq2, amp2, center2, aspect) - uv1) * 0.08

    return np.clip(uv2, 0.0, 1.0)


def sample(tex, uv):
    """texture2D with LINEAR filtering and CLAMP_TO_EDGE.

    The texture was uploaded without UNPACK_FLIP_Y, so t = 0 is its top row.
    """
    th, tw = tex.shape[:2]
    x = np.clip(uv[0] * tw - 0.5, 0, tw - 1)
    y = np.clip(uv[1] * th - 0.5, 0, th - 1)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    x1, y1 = np.minimum(x0 + 1, tw - 1), np.minimum(y0 + 1, th - 1)
    fx, fy = (x - x0)[..., None], (y - y0)[..., None]

    top = tex[y0, x0] * (1 - fx) + tex[y0, x1] * fx
    bottom = tex[y1, x0] * (1 - fx) + tex[y1, x1] * fx
    return top * (1 - fy) + bottom * fy


def hue_shift(rgb, amount):
    """The shader's hue rotation: RGB to HSL, turn H, and back."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(axis=-1), rgb.min(axis=-1)
    d = mx - mn
    lightness = (mx + mn) * 0.5

    chromatic = d > 0.001
    denom = 1.0 - np.abs(2.0 * lightness - 1.0)
    s = np.where(chromatic & (denom > 1e-6), d / np.where(denom > 1e-6, denom, 1.0), 0.0)

    safe_d = np.where(chromatic, d, 1.0)
    h = np.select(
        [~chromatic, mx == r, mx == g],
        [0.0, np.mod((g - b) / safe_d, 6.0) / 6.0, ((b - r) / safe_d + 2.0) / 6.0],
        default=((r - g) / safe_d + 4.0) / 6.0,
    )
    h = np.mod(h + amount, 1.0)

    q = np.where(lightness < 0.5, lightness * (1.0 + s), lightness + s - lightness * s)
    p = 2.0 * lightness - q

    def channel(offset):
        t = np.mod(h + offset, 1.0)
        return np.select(
            [t < 1 / 6, t < 0.5, t < 2 / 3],
            [p + (q - p) * 6.0 * t, q, p + (q - p) * (2 / 3 - t) * 6.0],
            default=p,
        )

    turned = np.stack([channel(1 / 3), channel(0.0), channel(-1 / 3)], axis=-1)
    return np.where((s > 0.001)[..., None], turned, rgb)


def petrona(size):
    """Petrona at a pixel size, unpacked from the webfont the site itself loads."""
    buf = BytesIO()
    TTFont(FONT).save(buf)
    buf.seek(0)
    return ImageFont.truetype(buf, size)


def centered(draw, spec, baseline):
    """One line, centred on the canvas, on a baseline. Pillow has no letter
    spacing, and the hero's does not go unnoticed at 128px, so the glyphs are
    placed one at a time."""
    text, size, tracking, fill = spec
    font = petrona(size)
    gap = size * tracking
    widths = [draw.textlength(ch, font=font) for ch in text]
    x = (W - (sum(widths) + gap * (len(text) - 1))) / 2
    for ch, width in zip(text, widths):
        draw.text((x, baseline), ch, font=font, fill=fill, anchor="ls")
        x += width + gap


def main():
    tex = np.asarray(Image.open(TEXTURE).convert("RGB"), dtype=np.float32) / 255.0
    colour = hue_shift(sample(tex, warp(W, H)), HUE_SHIFT)
    card = Image.fromarray((np.clip(colour, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))

    # Held a little above the middle, the way the hero holds its own name
    draw = ImageDraw.Draw(card)
    centered(draw, NAME, 330)
    centered(draw, TAGLINE, 390)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    card.save(OUT, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Compose the card images for the Projects section.

Each card is its own composition (backdrop, framing, angle, light) built from the
screenshots in ./sources. Cards are drawn at 2x and scaled down, so tilted edges
and small UI text are anti-aliased.

Run from anywhere:  python3 scripts/project-art/compose.py [name ...]
Needs Pillow, numpy and scipy.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, zoom

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "sources"
OUT = HERE.parents[1] / "src" / "assets" / "projects"

W, H = 1600, 1200  # output size, same 4:3 shape as the card
SS = 2  # supersampling factor
CW, CH = W * SS, H * SS

Y, X = np.mgrid[0:CH, 0:CW].astype(np.float32)
Y /= CH
X /= CW


# ---------------------------------------------------------------- colour helpers


def rgb(hex_colour):
    h = hex_colour.lstrip("#")
    return np.array([int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)


def fill(colour):
    return np.broadcast_to(rgb(colour), (CH, CW, 3)).copy()


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def glow(cx, cy, rx, ry, colour, strength, falloff=2.2):
    """Soft elliptical light, centred at (cx, cy) in card fractions."""
    d2 = ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2
    return np.exp(-d2 * falloff)[..., None] * rgb(colour) * strength


def screen(img, light):
    return 1 - (1 - img) * (1 - np.clip(light, 0, 1))


def mix(img, colour, amount):
    a = amount[..., None] if np.ndim(amount) == 2 else amount
    return img * (1 - a) + rgb(colour) * a


def to_float(im):
    return np.asarray(im.convert("RGB"), dtype=np.float32) / 255


def blur(arr, sigma):
    """Gaussian blur that stays fast for large radii by working on a reduced copy."""
    if sigma <= 0:
        return arr
    f = max(f for f in (1, 2, 4, 5, 8, 10, 16, 20) if f <= max(1, sigma / 3))
    h, w = arr.shape[:2]
    extra = arr.shape[2:]
    small = arr.reshape(h // f, f, w // f, f, *extra).mean(axis=(1, 3))
    small = gaussian_filter(small, (sigma / f, sigma / f) + (0,) * len(extra), mode="nearest")
    return zoom(small, (f, f) + (1,) * len(extra), order=1) if f > 1 else small


def progressive_blur(img, strength, max_sigma, levels=6):
    """Blur that grows with `strength` (0..1 per pixel), like a frosted fade. More
    levels make the change from sharp to soft more gradual, with no ghosting."""
    stack = [img] + [blur(img, max_sigma * i / (levels - 1)) for i in range(1, levels)]
    pos = np.clip(strength, 0, 1) * (levels - 1)
    out = np.zeros_like(img)
    for i, layer in enumerate(stack):
        out += layer * np.clip(1 - np.abs(pos - i), 0, 1)[..., None]
    return out


# ---------------------------------------------------------------- shapes and frames


def rounded_mask(w, h, r, ss=4):
    """Anti-aliased rounded-rectangle mask."""
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def rounded_outline(w, h, r, width, ss=4):
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle(
        (0, 0, w * ss - 1, h * ss - 1), r * ss, outline=255, width=max(1, round(width * ss))
    )
    return m.resize((w, h), Image.LANCZOS)


def vertical_ramp(w, h, top, bottom):
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    col = rgb(top) * (1 - t) + rgb(bottom) * t
    return Image.fromarray((np.broadcast_to(col, (h, w, 3)) * 255).astype(np.uint8))


def window(
    shot,
    width,
    radius=0.012,
    bezel=0.0,
    bezel_colours=("#2c302d", "#121412"),
    edge=0.18,
):
    """A screenshot in a frame: an optional device bezel, rounded corners, a light
    hairline along the outer edge and a dark line inside the bezel."""
    w = int(width)
    b = int(bezel * w)
    r = max(2, int(radius * w))
    inner_w = w - 2 * b
    content = shot.convert("RGB").resize(
        (inner_w, round(inner_w * shot.height / shot.width)), Image.LANCZOS
    )
    inner_h = content.height
    h = inner_h + 2 * b

    frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if b:
        frame.paste(vertical_ramp(w, h, *bezel_colours), (0, 0), rounded_mask(w, h, r))
    inner_r = max(2, r - b) if b else r
    frame.paste(content, (b, b), rounded_mask(inner_w, inner_h, inner_r))

    line = max(1.0, w / 1400)
    if b:
        dark = rounded_outline(inner_w, inner_h, inner_r, line)
        frame.paste((0, 0, 0), (b, b), dark.point(lambda v: v * 0.55))
    # Light hairline that fades from the top edge to the bottom edge
    hair = np.asarray(rounded_outline(w, h, r, line), dtype=np.float32) / 255
    fade = np.linspace(1, 0.25, h, dtype=np.float32)[:, None]
    hair = Image.fromarray((hair * fade * edge * 255).astype(np.uint8))
    frame.paste((255, 255, 255), (0, 0), hair)
    return frame


def project(w, h, centre, rx=0.0, ry=0.0, rz=0.0, persp=None):
    """Corners (TL, TR, BR, BL) of a w x h plane turned in 3D, like a CSS transform.
    rx > 0 tips the top edge away, ry > 0 turns the right edge away, rz < 0 turns
    the plane anticlockwise. The rotations apply as rotateX(rotateY(rotateZ(p)))."""
    a, b, c = np.radians([rx, ry, rz])
    rot_x = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    rot_y = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    rot_z = np.array([[np.cos(c), -np.sin(c), 0], [np.sin(c), np.cos(c), 0], [0, 0, 1]])
    pts = np.array([[-w / 2, -h / 2, 0], [w / 2, -h / 2, 0], [w / 2, h / 2, 0], [-w / 2, h / 2, 0]])
    p = pts @ (rot_x @ rot_y @ rot_z).T
    p[:, 0] += centre[0]
    p[:, 1] += centre[1]
    if persp:
        s = persp / (persp - p[:, 2])
        p[:, 0] = CW / 2 + (p[:, 0] - CW / 2) * s
        p[:, 1] = CH / 2 + (p[:, 1] - CH / 2) * s
    return [tuple(q) for q in p[:, :2]]


def project_at(w, h, corner, rx=0.0, ry=0.0, rz=0.0, persp=None, anchor=0):
    """Like project(), but moves the plane in 3D until one of its corners (0 TL,
    1 TR, 2 BR, 3 BL) lands on `corner`, so the perspective stays true to a viewer
    facing the card's centre."""
    centre = np.array(corner, dtype=float) + (w / 2, h / 2)
    for _ in range(60):
        quad = project(w, h, centre, rx, ry, rz, persp)
        error = np.array(corner) - np.array(quad[anchor])
        if np.abs(error).max() < 0.25:
            break
        centre += error * 0.7
    return quad


def flat(w, h, left, top):
    return [(left, top), (left + w, top), (left + w, top + h), (left, top + h)]


def warp(layer, quad):
    """Map a layer onto a quad of the canvas. Returns premultiplied RGB and alpha."""
    w, h = layer.size
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    rows, rhs = [], []
    for (x, y), (u, v) in zip(quad, src):
        rows += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        rhs += [u, v]
    coeffs = np.linalg.solve(np.array(rows, float), np.array(rhs, float))
    out = layer.convert("RGBa").transform((CW, CH), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    arr = np.asarray(out, dtype=np.float32) / 255
    return arr[..., :3], arr[..., 3]


def offset(arr, dx, dy):
    """Move an array by (dx, dy) pixels, filling the gap with zeros."""
    out = np.zeros_like(arr)
    h, w = arr.shape[:2]
    out[max(dy, 0) : h + min(dy, 0), max(dx, 0) : w + min(dx, 0)] = arr[
        max(-dy, 0) : h + min(-dy, 0), max(-dx, 0) : w + min(-dx, 0)
    ]
    return out


def place(img, layer, quad, shadow=None, tint=None):
    """Composite a framed layer onto the canvas with an optional soft drop shadow."""
    colour, alpha = warp(layer, quad)
    if tint is not None:
        colour *= tint
    if shadow:
        sigma, dx, dy, opacity = shadow
        s = offset(blur(alpha, sigma * SS), int(dx * SS), int(dy * SS))
        img = img * (1 - opacity * s)[..., None]
    return img * (1 - alpha)[..., None] + colour, alpha


def specks(img, n, colour, area, size=(0.6, 2.2), alpha=(0.15, 0.7), seed=1, bokeh=0.15):
    """Scattered points of light (dust, pollen, stars). `area(x, y)` gives density 0..1."""
    rng = np.random.default_rng(seed)
    layer = Image.new("L", (CW, CH), 0)
    soft = Image.new("L", (CW, CH), 0)
    draw, draw_soft = ImageDraw.Draw(layer), ImageDraw.Draw(soft)
    placed = 0
    while placed < n:
        x, y = rng.random(), rng.random()
        if rng.random() > area(x, y):
            continue
        placed += 1
        if rng.random() < bokeh:
            r = rng.uniform(3, 7) * SS
            draw_soft.ellipse((x * CW - r, y * CH - r, x * CW + r, y * CH + r), fill=int(255 * rng.uniform(0.1, 0.22)))
        else:
            r = rng.uniform(*size) * SS / 2
            draw.ellipse((x * CW - r, y * CH - r, x * CW + r, y * CH + r), fill=int(255 * rng.uniform(*alpha)))
    m = np.asarray(layer, dtype=np.float32) / 255
    m = blur(m, 0.6 * SS) * 1.4 + blur(np.asarray(soft, dtype=np.float32) / 255, 2.5 * SS)
    return screen(img, m[..., None] * rgb(colour))


def finish(img, name, grain=0.016, grain_mask=None, dither=0.0056):
    """Scale down to the output size, add film grain, dither and save.

    `dither` is a light, slightly coarse noise over the whole card, screenshots included. The
    site resizes these images to 600-1200 px and re-encodes them, which averages away the
    finer grain; without this layer, slow dark gradients come out in visible bands."""
    channels = [
        np.asarray(Image.fromarray(img[..., i].astype(np.float32), "F").resize((W, H), Image.LANCZOS))
        for i in range(3)
    ]
    out = np.stack(channels, axis=-1)
    rng = np.random.default_rng(7)
    noise = gaussian_filter(rng.normal(0, 1, (H, W)).astype(np.float32), 0.55)
    noise /= noise.std()
    if grain_mask is not None:
        noise *= np.asarray(
            Image.fromarray(grain_mask.astype(np.float32), "F").resize((W, H), Image.BILINEAR)
        )
    out = out + noise[..., None] * grain
    coarse = gaussian_filter(rng.normal(0, 1, (H, W)).astype(np.float32), 0.9)
    out = out + (coarse / coarse.std())[..., None] * dither
    out = out + rng.uniform(-0.5, 0.5, out.shape) / 255
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(
        OUT / f"{name}.jpg", quality=92, subsampling=0, optimize=True, progressive=True
    )
    print(f"wrote {OUT / name}.jpg")


def src(name):
    return Image.open(SOURCES / name)


def cover(im, w, h):
    """Scale and centre-crop an image to fill w x h."""
    s = max(w / im.width, h / im.height)
    im = im.convert("RGB").resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    left, top = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((left, top, left + w, top + h))


# ---------------------------------------------------------------- the cards


def move(quad, x, y):
    """Shift a quad so its top-left corner lands on (x, y)."""
    dx, dy = x - quad[0][0], y - quad[0][1]
    return [(px + dx, py + dy) for px, py in quad]


def fern():
    """After the Shadow shot: a tablet leaning back under a soft sage haze with
    drifting pollen, with room on either side. Its lower part softens out."""
    base = "#0a110d"
    img = fill(base)
    img = screen(img, glow(0.5, -0.16, 0.75, 0.5, "#b9cc9f", 0.48))
    img = screen(img, glow(0.82, -0.05, 0.36, 0.28, "#efe0b6", 0.26))
    img = screen(img, glow(0.1, 0.02, 0.3, 0.22, "#8fae80", 0.16))
    img = specks(img, 150, "#f3ead0", lambda x, y: max(0.0, 1 - y / 0.34) ** 1.6, seed=3)

    device = window(
        src("fern.png"),
        0.88 * CW,
        radius=0.026,
        bezel=0.007,
        bezel_colours=("#454a43", "#1b1e1b"),
        edge=0.32,
    )
    quad = project(device.width, device.height, (CW / 2, CH / 2), rx=20, persp=1.5 * CW)
    quad = move(quad, quad[0][0], 0.25 * CH)
    img, alpha = place(img, device, quad, tint=0.92)

    # A faint sheen across the glass
    sheen = smoothstep(0.22, 0.0, np.abs((X * 0.55 + Y) - 0.6)) * 0.05
    img = screen(img, (sheen * alpha)[..., None] * rgb("#ffffff"))

    img = progressive_blur(img, smoothstep(0.7, 1.02, Y) ** 1.5, 7 * SS)
    img = mix(img, base, smoothstep(0.72, 1.04, Y) ** 1.4 * 0.55)
    img = mix(img, "#040705", smoothstep(0.62, 1.1, np.hypot(X - 0.5, (Y - 0.4) * 0.9)) * 0.45)
    finish(img, "fern", grain_mask=1 - alpha * 0.85)


def dime_defender():
    """After the Hack the North shot: two overlapping windows over a red courtroom
    glow, the debate on a checkout page behind and the cover art in front."""
    base = "#120605"
    img = fill(base)
    img = screen(img, glow(0.9, -0.02, 0.85, 0.75, "#d63d26", 0.62))
    img = screen(img, glow(0.62, 0.18, 0.4, 0.3, "#ff8a4c", 0.18))
    img = screen(img, glow(0.0, 1.05, 0.6, 0.45, "#e0702f", 0.22))

    frame = dict(radius=0.012, bezel=0.006, bezel_colours=("#3b2b28", "#160f0e"), edge=0.3)
    back = window(src("dime-defender-debate.png"), 0.6 * CW, **frame)
    img, back_alpha = place(
        img,
        back,
        flat(back.width, back.height, 0.37 * CW, 0.0),
        shadow=(40, 0, 24, 0.55),
        tint=0.85,
    )
    front = window(src("dime-defender.jpg"), 0.68 * CW, **frame)
    img, front_alpha = place(
        img,
        front,
        flat(front.width, front.height, 0.07 * CW, 0.4 * CH),
        shadow=(50, 0, 34, 0.75),
    )

    img = mix(img, "#070202", smoothstep(0.5, 1.05, np.hypot(X - 0.5, Y - 0.4)) * 0.5)
    finish(img, "dime-defender", grain_mask=1 - np.maximum(back_alpha, front_alpha) * 0.85)


def eureka_hacks():
    """After the Sandbox shot: a flat, centred window in a thin bezel, floating in
    its own light. The backdrop is the page itself, blurred out, with a few stars."""
    shot = src("eureka-hacks-2025.png")
    shot = shot.crop((0, 0, shot.width - 14, shot.height))  # drop the scrollbar
    img = to_float(cover(shot, CW, CH))
    img = blur(img, 70 * SS)
    lum = img.mean(axis=2, keepdims=True)
    img = (lum + (img - lum) * 1.25) * 0.5
    img = specks(img, 110, "#ffffff", lambda x, y: max(0.0, 1 - y / 0.75), size=(0.6, 1.8), seed=11, bokeh=0.08)

    win = window(
        shot,
        0.86 * CW,
        radius=0.014,
        bezel=0.006,
        bezel_colours=("#2e2848", "#100c1f"),
        edge=0.32,
    )
    left, top = (CW - win.width) / 2, 0.5 * CH - win.height / 2
    img, alpha = place(img, win, flat(win.width, win.height, left, top), shadow=(60, 0, 40, 0.6))

    img = mix(img, "#07041a", smoothstep(0.45, 1.0, np.hypot(X - 0.5, (Y - 0.5) * 1.1)) * 0.65)
    img = mix(img, "#07041a", smoothstep(0.8, 1.0, Y) * 0.6)
    finish(img, "eureka-hacks-2025", grain_mask=1 - alpha * 0.85)


def mr_goose():
    """The editor up close: VS Code runs off the left and bottom edges, with the
    extension panel in full view under a warm light."""
    shot = src("mr-goose.png")
    base = "#0f0b08"
    img = fill(base)
    img = screen(img, glow(0.8, 0.02, 0.62, 0.42, "#e2a56c", 0.6))
    img = screen(img, glow(0.35, -0.08, 0.5, 0.25, "#f0c08a", 0.14))
    img = specks(img, 60, "#ffe0b8", lambda x, y: max(0.0, 1 - y / 0.15), size=(0.6, 1.4), seed=9, bokeh=0.3)

    win = window(shot.crop((720, 0, shot.width, shot.height)), 1.0 * CW, radius=0.01, edge=0.32)
    left, top = 0.95 * CW - win.width, 0.15 * CH
    img, alpha = place(img, win, flat(win.width, win.height, left, top), shadow=(50, -10, 30, 0.7))

    img = progressive_blur(img, smoothstep(0.8, 1.05, Y) * 0.8 + smoothstep(0.35, 0.0, X) * 0.5, 8 * SS)
    # Darken without a colour shift: a warm fade over the grey editor bands badly once compressed
    img = img * (1 - smoothstep(0.55, 1.15, (1 - X) * 0.75 + Y * 0.45) * 0.75)[..., None]
    finish(img, "mr-goose", grain_mask=1 - alpha * 0.85)


def ignite_ai():
    """After the Dots shot, mirrored: the app on a device lying back at an angle, so
    only its top-right corner (the interest list and the career nodes) is in view,
    under a peach light that falls off to the left."""
    base = "#0b0a0c"
    img = fill(base)
    img = screen(img, glow(1.0, 0.0, 0.85, 0.8, "#f0925a", 0.85))
    img = screen(img, glow(0.85, 0.1, 0.4, 0.3, "#ffd3a8", 0.2))

    device = window(
        src("ignite-ai.png").crop((560, 0, 1861, 859)),
        1.5 * CW,
        radius=0.008,
        bezel=0.0035,
        bezel_colours=("#f3b98a", "#6b4128"),
        edge=0.6,
    )
    quad = project_at(
        device.width, device.height, (0.906 * CW, 0.334 * CH), rx=38, rz=20, persp=1.8 * CW, anchor=1
    )
    img, alpha = place(img, device, quad, shadow=(40, 0, 30, 0.6), tint=0.9)

    # The far side of the screen falls into shadow
    img = mix(img, base, smoothstep(0.4, 1.1, (1 - X) * 0.85 + (1 - Y) * 0.25) * 0.88)
    finish(img, "ignite-ai", grain=0.024, grain_mask=1 - alpha * 0.8)


def gdtris():
    """After the Arceus shot: the game on a tablet leaning back, running off the
    right and bottom edges, with an amber light rising from the lower left."""
    base = "#070a08"
    img = fill(base)
    img = screen(img, glow(-0.05, 1.05, 0.75, 0.85, "#d4823a", 0.75))
    img = screen(img, glow(0.3, 0.0, 0.6, 0.3, "#55704a", 0.18))

    device = window(
        src("gdtris.jpg"),
        1.0 * CW,
        radius=0.022,
        bezel=0.012,
        bezel_colours=("#33362f", "#121412"),
        edge=0.38,
    )
    quad = project(device.width, device.height, (CW / 2, CH / 2), rx=26, rz=-2, persp=1.5 * CW)
    quad = move(quad, 0.17 * CW, 0.15 * CH)
    img, alpha = place(img, device, quad, shadow=(50, 0, 30, 0.6))

    # The screen falls into shadow towards the right and the bottom, and goes out
    # of focus only in the bottom-right corner
    img = mix(img, base, smoothstep(0.55, 1.1, X * 0.7 + Y * 0.45) * 0.6)
    corner = np.hypot((1 - X) / 0.5, (1 - Y) / 0.42)
    img = progressive_blur(img, smoothstep(1.6, 0.0, corner) ** 2, 7 * SS, levels=14)
    finish(img, "gdtris", grain=0.024, grain_mask=1 - alpha * 0.8)


CARDS = {
    "fern": fern,
    "dime-defender": dime_defender,
    "eureka-hacks-2025": eureka_hacks,
    "mr-goose": mr_goose,
    "ignite-ai": ignite_ai,
    "gdtris": gdtris,
}

if __name__ == "__main__":
    for name in sys.argv[1:] or CARDS:
        CARDS[name]()

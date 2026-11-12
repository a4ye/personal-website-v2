#!/usr/bin/env python3
"""Make the footer cat and its butterfly, cut out of the pin they come from.

pin.jpg is a cat looking up at a butterfly, airbrushed and stippled on cream
paper: peach in front, going over to blue dots down its back, with dots for
eyes. Both are cut out of the paper and painted in the site's colours.

Each pixel is as opaque as it is far from the paper's colour, so the airbrushed
edge stays soft and the stipple stays dots; inside, the cat is solid. The paper
is then taken back out of the colour of the edge, so that no cream is left
round it on the page.

The cat is painted in two pigments, peach and blue. How much of each a pixel
has is mapped onto a ramp of the site's greens, and its lightness is kept, so
the shading and the dots stay and only the hue changes. The blush, pinker than
the two, is kept as a muted rose.

The pin cuts off the cat's back at its right edge, and so does the picture.
FooterCat.svelte puts that edge just past the right edge of the screen, so the
cat goes on out of sight.

The eyes are dots, so each is cut out on its own (eye-near.webp, eye-far.webp),
and in cat.avif they are painted over with the fur round them. FooterCat.svelte
moves them to look about, and squashes them to blink.

Run from anywhere:  python3 scripts/cat-art/cat.py
With --original, the cat and butterfly keep the pin's own colours.
Needs OpenCV, numpy and Pillow.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SRC = HERE / "pin.jpg"
OUT = HERE.parents[1] / "src" / "assets" / "cat"

CAT_WIDTH = 400  # twice the width the footer shows it at, for 2x screens
BUTTERFLY_WIDTH = 96
BOTTOM = 0.85  # of the pin's height; below this the cat is behind the footer line anyway
MARGIN = 0.05  # of the cat's width: how far out round it a press still counts
BUTTERFLY = (0.2, 0.395)  # the middle of the butterfly, as fractions of the pin, where the cat looks
ORIGINAL = "--original" in sys.argv


def hex_colour(h):
    return np.array([int(h[i : i + 2], 16) for i in (1, 3, 5)], np.float32) / 255


# By how much blue a pixel has, from none to all. Between --color-surface-3 and --color-accent,
# so the face stays a shade darker than the page and the dots on the back are the accent.
FUR = [hex_colour(c) for c in ("#cddfd3", "#a3c0ae", "#6f9a83", "#3d6b55")]
ROSE = hex_colour("#e8b7b3")  # the blush
EYE = hex_colour("#26392f")  # darker than the darkest dots, as the pin's eyes are
WING = [hex_colour(c) for c in ("#2f5a46", "#3d6b55", "#6f9a83")]  # around --color-accent


def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def to_lab(rgb):
    return cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)


def to_rgb(lab):
    return np.clip(cv2.cvtColor(lab.astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)


def ramp(t, colours):
    """Colours along t from 0 to 1, evenly spaced, mixed in Lab."""
    stops = to_lab(np.array([colours], np.float32))[0]
    t = np.clip(t, 0, 1) * (len(stops) - 1)
    i = np.minimum(t.astype(int), len(stops) - 2)
    f = (t - i)[..., None]
    return stops[i] * (1 - f) + stops[i + 1] * f


def biggest(mask):
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    return labels == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA]) if n > 1 else mask


def fill_holes(mask):
    flood = np.pad(~mask, 1, constant_values=True).astype(np.uint8)
    cv2.floodFill(flood, None, (0, 0), 0)  # clears everything joined to the outside; the rest is holes
    return mask | flood[1:-1, 1:-1].astype(bool)


def grow(mask, px):
    return cv2.dilate(mask.astype(np.uint8), np.ones((2 * px + 1, 2 * px + 1), np.uint8)) > 0


def blur(a, sigma):
    return cv2.GaussianBlur(a.astype(np.float32), (0, 0), sigma)


def spread(values, known, sigma):
    """Every pixel given the values of the known pixels nearest it, at wider and wider reach until all are."""
    out = np.zeros_like(values)
    done = np.zeros(values.shape[:2], bool)
    k = known.astype(np.float32)
    for s in (sigma, sigma * 3, sigma * 9, sigma * 27):
        num = blur(values * (k[..., None] if values.ndim == 3 else k), s)
        den = blur(k, s)
        fill = ~done & (den > 1e-4)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[fill] = (num / (den[..., None] if values.ndim == 3 else den))[fill]
        done |= fill
    return out


def trim(alpha):
    rows, cols = np.nonzero(alpha > 0.02)
    return cols.min(), rows.min(), cols.max() + 1, rows.max() + 1


def save(rgb, alpha, path, box, width):
    """The box of the picture, scaled to the given width, with alpha. The cat is AVIF: its dots are
    fine grain, which WebP needs more than twice the bytes for at the same look."""
    rgba = np.dstack([np.clip(rgb, 0, 1), np.clip(alpha, 0, 1)])
    im = Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA").crop(box)
    im = im.resize((width, max(1, round(im.height * width / im.width))), Image.LANCZOS)
    if path.suffix == ".avif":
        im.save(path, "AVIF", quality=50)
    else:
        im.save(path, "WEBP", quality=88, alpha_quality=100, method=6)
    print(f"{path.name}: {im.width} x {im.height}, {path.stat().st_size / 1024:.1f} KB")


def paper_of(img):
    """The paper's colour: the middle of the empty top of the pin."""
    h, w = img.shape[:2]
    return np.median(img[h // 30 : h // 5, w // 15 : w * 4 // 5].reshape(-1, 3), axis=0)


def cut_out(img, paper):
    """How far each pixel is from the paper, as alpha: none for the paper and its grain, all for
    the face's peach and anything stronger."""
    distance = np.linalg.norm(to_lab(img) - to_lab(paper[None, None]), axis=2)
    return smoothstep((distance - 3) / 12)


def unmix(img, alpha, paper):
    """The colour a pixel would have without the paper showing through it."""
    return np.clip((img - (1 - alpha[..., None]) * paper) / np.maximum(alpha, 0.05)[..., None], 0, 1)


def find_eyes(lab, filled):
    """The eyes: the two biggest dark blue blots in the face. The nose is the same blue, but
    smaller; the dots of the stipple are smaller still, and the opening takes them away."""
    L, b = lab[..., 0], lab[..., 2]
    blots = cv2.morphologyEx(((L < 55) & (b < -35) & filled).astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, labels, stats, centres = cv2.connectedComponentsWithStats(blots)
    two = sorted(range(1, n), key=lambda i: -stats[i, cv2.CC_STAT_AREA])[:2]
    # The cat faces left, so the eye nearer the left is the far one, and drawn smaller
    far, near = sorted(two, key=lambda i: centres[i][0])
    return labels == near, labels == far


def eye_alpha(lab, blob):
    """An eye as painted: as opaque as it is dark and blue, near its blot."""
    L, b = lab[..., 0], lab[..., 2]
    a = smoothstep((70 - L) / 25) * smoothstep((-b - 20) / 20)
    return blur(a * grow(blob, 4), 0.5)


def cat(img):
    h, w = img.shape[:2]
    paper = paper_of(img)
    soft = cut_out(img, paper)
    # The cat is the biggest shape on the paper; its loose dots are the ones close to it
    body = fill_holes(biggest(soft > 0.5))
    alpha = np.maximum(soft * grow(body, 10), blur(~grow(~body, 3), 1.5))

    colour = unmix(img, alpha, paper)
    near_blob, far_blob = find_eyes(to_lab(img), body)
    near_eye, far_eye = eye_alpha(to_lab(img), near_blob), eye_alpha(to_lab(img), far_blob)

    # The eyes, painted over with what is round them, before anything else sees them. Each has a
    # pale ring round it, where the airbrush is thin, so that goes too. The colour is carried in
    # from where the fur is solid, and how solid it is from all round; the near eye, which is
    # among the dots, also gets the dots of the forehead just above. The far eye is on the smooth
    # airbrushed side, with none to carry.
    for eye, dotted in ((near_eye, True), (far_eye, False)):
        hole = grow(eye > 0.05, 5)
        filled = spread(colour, ~hole & (alpha > 0.6), 2)
        if dotted:
            above = np.roll(colour, 45, axis=0)
            filled = filled + above - cv2.GaussianBlur(above, (0, 0), 2)
        solid = cv2.inpaint((alpha * 255).astype(np.uint8), hole.astype(np.uint8), 6, cv2.INPAINT_TELEA) / 255
        fade = blur(hole, 1.5)
        colour = np.clip(colour * (1 - fade[..., None]) + filled * fade[..., None], 0, 1)
        alpha = alpha * (1 - fade) + solid * fade
    lab = to_lab(colour)

    if ORIGINAL:
        rgb = colour
    else:
        # How much blue each pixel has, between the face's peach and the back's blue, and how much
        # lighter or darker it is than that mix
        peach = np.median(lab[body & (lab[..., 2] > 15) & (lab[..., 0] > 80)], axis=0)
        blue = np.median(lab[body & (lab[..., 2] < -35) & (lab[..., 0] < 50)], axis=0)
        across = blue - peach
        t = ((lab - peach) @ across) / (across @ across)
        sure = smoothstep((alpha - 0.1) / 0.3)  # the faint edge is mostly paper: its mix is a guess
        t = t * sure + spread(t, alpha > 0.4, 2) * (1 - sure)
        on_line = peach + np.clip(t, 0, 1)[..., None] * across
        out = ramp(t, FUR)
        out[..., 0] += lab[..., 0] - on_line[..., 0]
        # The blush is redder than the mix of the two, and light: the nose and some of the dots are
        # as red, but dark
        redder = blur(lab[..., 1] - on_line[..., 1], 2)
        pink = smoothstep((blur(redder, 5) - 2) / 10) * smoothstep((blur(lab[..., 0], 3) - 55) / 10) * 0.55
        out = out * (1 - pink[..., None]) + to_lab(ROSE[None, None]) * pink[..., None]
        rgb = to_rgb(out)

    alpha[round(h * BOTTOM) :] = 0
    box = trim(alpha)
    save(rgb, alpha, OUT / "cat.avif", box, CAT_WIDTH)

    bw, bh = box[2] - box[0], box[3] - box[1]
    print(f"cat aspect {bw / bh:.4f} (width over height)")
    # FooterCat.svelte keeps enough of the cat past the screen's edge that leaning never shows its end
    meets = np.argmax(blur(alpha[:, box[2] - 1], 2) > 0.5)
    print(f"its back meets the right edge {(meets - box[1]) / bh:.3f} of its height down")
    print(f"the pin's butterfly at {(BUTTERFLY[0] * w - box[0]) / bw:.2f}, {(BUTTERFLY[1] * h - box[1]) / bw:.2f} cat widths from its top left")
    print(f"outline {outline(alpha[box[1] : box[3], box[0] : box[2]])}")
    for name, a in (("near", near_eye), ("far", far_eye)):
        x0, y0, x1, y1 = trim(a)
        x0, y0, x1, y1 = x0 - 2, y0 - 2, x1 + 2, y1 + 2
        flat = EYE if not ORIGINAL else np.median(img[a > 0.8], axis=0)
        save(np.broadcast_to(flat, img.shape), a, OUT / f"eye-{name}.webp", (x0, y0, x1, y1), round((x1 - x0) * CAT_WIDTH / bw))
        print(
            f"{name} eye at left {(x0 - box[0]) / bw:.4f}, top {(y0 - box[1]) / bh:.4f}, "
            f"width {(x1 - x0) / bw:.4f}, height {(y1 - y0) / bh:.4f}"
        )


def outline(alpha):
    """The cat's outline, MARGIN out from it, as a CSS polygon. Its points are fractions of a box
    MARGIN bigger than the picture all round, which is the box FooterCat.svelte presses it in."""
    h, w = alpha.shape
    m = round(MARGIN * w)
    shape = np.pad(fill_holes(biggest(blur(alpha, 3) > 0.3)), m)
    shape = cv2.dilate(shape.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * m + 1, 2 * m + 1)))
    contours, _ = cv2.findContours(shape, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    points = cv2.approxPolyDP(max(contours, key=cv2.contourArea), 0.006 * w, True)[:, 0]
    H, W = shape.shape
    return "polygon(" + ", ".join(f"{100 * x / (W - 1):.1f}% {100 * y / (H - 1):.1f}%" for x, y in points) + ")"


def butterfly(img):
    h, w = img.shape[:2]
    paper = paper_of(img)
    alpha = cut_out(img, paper)
    # It is the biggest shape in the top left of where the cat is not; the leaves are far below it
    alpha[h // 2 :] = 0
    alpha[:, w // 2 :] = 0
    alpha *= grow(biggest(alpha > 0.5), 6)
    colour = unmix(img, alpha, paper)
    if not ORIGINAL:
        light = to_lab(colour)[..., 0]
        solid = alpha > 0.9
        lo, hi = np.percentile(light[solid], [2, 98])
        colour = to_rgb(ramp((light - lo) / (hi - lo), WING))
    save(colour, alpha, OUT / "butterfly.webp", trim(alpha), BUTTERFLY_WIDTH)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    pin = np.asarray(Image.open(SRC).convert("RGB"), np.float32) / 255
    butterfly(pin)
    cat(pin)

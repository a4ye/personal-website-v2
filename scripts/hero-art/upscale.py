#!/usr/bin/env python3
"""Make the hero image: a clean, 2x-size version of the hero photo.

The photo (hero-photo.png) is small and carries compression blocks, which show
up as pixelation once the hero shader stretches it across a large screen.
Real-ESRGAN redraws it at 4x without the blocks; it is then scaled down to 2x
(2244 x 3060, the shape the shader expects) and saved as 10-bit AVIF, which
keeps the smooth gradients far better than 8-bit AVIF or lossy WebP. Smaller
copies are written beside it, one per screen size the shader might be asked to
cover, so a phone does not download a texture meant for a 4K monitor.

Run from anywhere:  python3 scripts/hero-art/upscale.py
Needs realesrgan-ncnn-vulkan (https://github.com/xinntao/Real-ESRGAN/releases) on
the PATH or in $REALESRGAN, avifenc (libavif) on the PATH, plus OpenCV, numpy
and Pillow.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SRC = HERE / "hero-photo.png"
OUT = HERE.parents[1] / "src" / "assets" / "hero.avif"

W, H = 2244, 3060
SIZES = (1536, 2304)  # the smaller copies, by height; see main()
TILE = 256  # Real-ESRGAN tile size, in source pixels


def esrgan(exe, img, tmp):
    """Real-ESRGAN 4x of an RGB uint8 array."""
    src, big = Path(tmp) / "in.png", Path(tmp) / "out.png"
    Image.fromarray(img).save(src)
    # The binary finds its models/ folder relative to the working directory
    subprocess.run([exe, "-i", str(src), "-o", str(big), "-n", "realesrgan-x4plus", "-s", "4", "-t", str(TILE)],
                   cwd=Path(exe).resolve().parent, check=True, capture_output=True)
    return np.asarray(Image.open(big).convert("RGB"), np.float32) / 255


def upscale(photo):
    """Real-ESRGAN 4x without tile seams, then area-average down to 2x.

    The GPU build works in tiles, and their edges show as faint lines in flat
    gradients. So it runs four times with the tile grid shifted by half a tile,
    and each pixel is blended from the runs whose tile middle it is nearest to:
    triangle weights that are zero on a run's own seams and always sum to one."""
    exe = os.environ.get("REALESRGAN") or shutil.which("realesrgan-ncnn-vulkan")
    if not exe:
        sys.exit("realesrgan-ncnn-vulkan not found: put it on the PATH or set $REALESRGAN")
    h, w = photo.shape[:2]

    def weight(n, shift):  # per output pixel along one axis
        u = ((np.arange(n * 4) + 0.5) / 4 - shift) / TILE
        return 1 - np.abs(2 * (u % 1) - 1)

    total = np.zeros((h * 4, w * 4, 3), np.float32)
    with tempfile.TemporaryDirectory() as tmp:
        for dy in (0, TILE // 2):
            for dx in (0, TILE // 2):
                py, px = (TILE - dy) % TILE, (TILE - dx) % TILE  # padding that moves the seams to k*TILE + d
                padded = cv2.copyMakeBorder(photo, py, 0, px, 0, cv2.BORDER_REFLECT_101)
                out = esrgan(exe, padded, tmp)[py * 4 : py * 4 + h * 4, px * 4 : px * 4 + w * 4]
                total += out * (weight(h, dy)[:, None] * weight(w, dx)[None, :])[..., None]
    return cv2.resize(total, (W, H), interpolation=cv2.INTER_AREA)


def save(img, path):
    """10-bit, full-chroma AVIF, encoded from 16-bit so gradients don't band."""
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "out.png"
        cv2.imwrite(str(png), (np.clip(img, 0, 1) * 65535 + 0.5).astype(np.uint16)[..., ::-1])  # OpenCV wants BGR
        subprocess.run(["avifenc", "-d", "10", "-y", "444", "-q", "95", "--speed", "4", str(png), str(path)],
                       check=True, capture_output=True)


def main():
    photo = np.asarray(Image.open(SRC).convert("RGB"))
    peaks = photo.max((0, 1)) / 255  # Real-ESRGAN nudges some reds to full; keep the photo's peaks
    big = np.minimum(upscale(photo), peaks)
    save(big, OUT)
    written = [OUT]
    # The shader covers the window with this photo, so the only part of it anyone sees is about as
    # many pixels as the canvas is long, plus the fifth the liquify pass stretches it by. A phone
    # needs about 1500 of them and used to download all 3060. index.astro picks between these.
    for tall in SIZES:
        wide = round(tall * W / H)
        path = OUT.with_name(f"{OUT.stem}-{tall}{OUT.suffix}")
        save(cv2.resize(big, (wide, tall), interpolation=cv2.INTER_AREA), path)
        written.append(path)
    for path in written:
        print(f"wrote {path.relative_to(HERE.parents[1])} ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()

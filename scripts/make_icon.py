#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "FCP Shotcut.app" / "Contents" / "Resources"
ICONSET = ROOT / "build" / "FCPShotcut.iconset"
ICNS = RESOURCES / "FCPShotcut.icns"
PREVIEW = ROOT / "assets" / "icon-preview.png"


def rounded_rect_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size, size), radius=radius, fill=255)
    return mask


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def make_base(size: int = 1024) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    bg = Image.new("RGBA", (size, size))
    bg_px = bg.load()
    top = (81, 68, 222)
    bottom = (0, 198, 172)
    for y in range(size):
        t = y / (size - 1)
        for x in range(size):
            side = (x / (size - 1) - 0.5) * 0.18
            tt = min(1, max(0, t + side))
            bg_px[x, y] = (
                lerp(top[0], bottom[0], tt),
                lerp(top[1], bottom[1], tt),
                lerp(top[2], bottom[2], tt),
                255,
            )
    mask = rounded_rect_mask(size, int(size * 0.22))
    img.alpha_composite(bg)
    img.putalpha(mask)

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    frame = (278, 116, 746, 908)
    sd.rounded_rectangle(frame, radius=72, fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    img.alpha_composite(shadow)

    d = ImageDraw.Draw(img)
    d.rounded_rectangle(frame, radius=72, fill=(246, 250, 255, 240), outline=(255, 255, 255, 210), width=10)
    inner = (322, 166, 702, 858)
    d.rounded_rectangle(inner, radius=42, fill=(24, 31, 50, 255))

    colors = [(113, 88, 255), (0, 203, 190), (255, 255, 255)]
    shot_h = 118
    y = 205
    for i in range(4):
        color = colors[i % len(colors)]
        d.rounded_rectangle((356, y, 668, y + shot_h), radius=26, fill=color + (245,))
        if i < 3:
            dash_y = y + shot_h + 27
            for x in range(354, 669, 50):
                d.line((x, dash_y, x + 25, dash_y), fill=(255, 255, 255, 180), width=10)
        y += 155

    # Small stylized scissors at the main cut.
    cx, cy = 512, 535
    d.line((430, 450, 594, 616), fill=(255, 255, 255, 245), width=22)
    d.line((594, 450, 430, 616), fill=(255, 255, 255, 245), width=22)
    d.ellipse((360, 590, 455, 685), outline=(255, 255, 255, 245), width=20)
    d.ellipse((569, 590, 664, 685), outline=(255, 255, 255, 245), width=20)
    d.ellipse((cx - 19, cy - 19, cx + 19, cy + 19), fill=(24, 31, 50, 255))

    highlight = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    hd = ImageDraw.Draw(highlight)
    hd.arc((82, 72, 942, 932), start=210, end=300, fill=(255, 255, 255, 80), width=18)
    img.alpha_composite(highlight)
    return img


def write_iconset(base: Image.Image) -> None:
    if ICONSET.exists():
        shutil.rmtree(ICONSET)
    ICONSET.mkdir(parents=True)
    sizes = [16, 32, 128, 256, 512]
    for size in sizes:
        base.resize((size, size), Image.Resampling.LANCZOS).save(ICONSET / f"icon_{size}x{size}.png")
        base.resize((size * 2, size * 2), Image.Resampling.LANCZOS).save(ICONSET / f"icon_{size}x{size}@2x.png")


def main() -> int:
    RESOURCES.mkdir(parents=True, exist_ok=True)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    base = make_base()
    base.save(PREVIEW)
    write_iconset(base)
    subprocess.run(["iconutil", "-c", "icns", str(ICONSET), "-o", str(ICNS)], check=True)
    print(ICNS)
    print(PREVIEW)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

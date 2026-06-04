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
    top = (245, 249, 255)
    bottom = (204, 233, 255)
    for y in range(size):
        t = y / (size - 1)
        for x in range(size):
            radial = math.hypot((x / size) - 0.32, (y / size) - 0.2) * 0.24
            tt = min(1, max(0, t + radial))
            bg_px[x, y] = (
                lerp(top[0], bottom[0], tt),
                lerp(top[1], bottom[1], tt),
                lerp(top[2], bottom[2], tt),
                255,
            )
    mask = rounded_rect_mask(size, int(size * 0.22))
    img.alpha_composite(bg)
    img.putalpha(mask)

    d = ImageDraw.Draw(img)

    # Subtle glass highlight, like a native macOS utility icon.
    shine = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sh = ImageDraw.Draw(shine)
    sh.ellipse((-170, -250, 1020, 540), fill=(255, 255, 255, 95))
    shine.putalpha(shine.split()[-1].filter(ImageFilter.GaussianBlur(12)))
    img.alpha_composite(shine)

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    phone = (310, 116, 714, 908)
    sd.rounded_rectangle(phone, radius=86, fill=(18, 34, 64, 80))
    shadow = shadow.filter(ImageFilter.GaussianBlur(30))
    img.alpha_composite(shadow)

    # Main vertical timeline glyph.
    d.rounded_rectangle(phone, radius=86, fill=(255, 255, 255, 250))
    inner = (350, 160, 674, 864)
    d.rounded_rectangle(inner, radius=52, fill=(23, 36, 64, 255))

    track = (394, 220, 630, 790)
    d.rounded_rectangle(track, radius=42, fill=(36, 55, 92, 255))

    # Three clean shot blocks, separated by fine cut lines. Keep the palette
    # restrained so the icon reads like a native macOS utility.
    blocks = [
        ((418, 248, 606, 374), (82, 121, 255)),
        ((418, 428, 606, 554), (82, 121, 255)),
        ((418, 608, 606, 734), (82, 121, 255)),
    ]
    for rect, color in blocks:
        d.rounded_rectangle(rect, radius=28, fill=color + (255,))

    for y in (400, 580):
        d.line((394, y, 630, y), fill=(236, 244, 255, 230), width=10)
        d.polygon([(512, y - 22), (543, y), (512, y + 22)], fill=(236, 244, 255, 245))

    # Minimal playhead/cut indicator.
    d.line((512, 205, 512, 808), fill=(255, 255, 255, 210), width=8)
    d.ellipse((492, 492, 532, 532), fill=(255, 255, 255, 255))
    d.ellipse((502, 502, 522, 522), fill=(23, 36, 64, 255))

    # Tiny FCP-like sparkle accent, restrained.
    accent = (706, 194)
    d.polygon(
        [
            (accent[0], accent[1] - 28),
            (accent[0] + 9, accent[1] - 8),
            (accent[0] + 30, accent[1]),
            (accent[0] + 9, accent[1] + 8),
            (accent[0], accent[1] + 28),
            (accent[0] - 9, accent[1] + 8),
            (accent[0] - 30, accent[1]),
            (accent[0] - 9, accent[1] - 8),
        ],
        fill=(82, 121, 255, 145),
    )
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

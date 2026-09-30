#!/usr/bin/env python3
"""Build the mini-site image set (WebP heroes/cards + 1200x630 OG JPEGs).

Source photos come from the main site's design-preview assets (same owner).
Run:  python3 tools/make_images.py [path-to-main-repo]
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PIL import Image

MAIN = Path(sys.argv[1] if len(sys.argv) > 1 else "/Users/son/Code/vibe-vietnam-tour")
SRC_ASSETS = MAIN / "design-preview" / "assets"
OUT = Path(__file__).resolve().parent.parent / "src" / "assets"
IMG = OUT / "img"
OG = OUT / "og"

HERO = 1100   # hero width
CARD = 600    # index-card width

# page slug -> source photo (from the main site's own asset library)
PHOTOS = {
    "home-hero": ("hero-1200.webp",),
    "5-days-north-vietnam": ("dest-halong.jpg",),
    "7-days-north-to-central": ("dest-danang.jpg",),
    "10-days-vietnam-north-to-south": ("dest-hcmc.jpg",),
    "best-time-to-visit-vietnam": ("dest-hue.jpg",),
    "getting-around-vietnam": ("dest-hanoi.jpg",),
}

COPY = ["logo.png", "logo-white.png", "favicon.png", "favicon-192.png", "apple-touch-icon.png"]


def webp(src: Path, dest: Path, width: int, quality: int = 70, max_bytes: int = 130_000) -> tuple[int, int]:
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > width:
            height = round(im.height * width / im.width)
            im = im.resize((width, height), Image.LANCZOS)
        dest.parent.mkdir(parents=True, exist_ok=True)
        for q in (quality, 64, 58, 52, 46):
            im.save(dest, "WEBP", quality=q, method=6)
            if dest.stat().st_size <= max_bytes:
                break
        return im.size


def og_crop(src: Path, dest: Path, quality: int = 80) -> None:
    """Centre-crop to 1200x630 and save as JPEG (safest format for social cards)."""
    with Image.open(src) as im:
        im = im.convert("RGB")
        target_ratio = 1200 / 630
        w, h = im.size
        if w / h > target_ratio:
            new_w = round(h * target_ratio)
            left = (w - new_w) // 2
            im = im.crop((left, 0, left + new_w, h))
        else:
            new_h = round(w / target_ratio)
            top = int((h - new_h) * 0.35)
            im = im.crop((0, top, w, top + new_h))
        im = im.resize((1200, 630), Image.LANCZOS)
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "JPEG", quality=quality, optimize=True, progressive=True)


def main() -> None:
    IMG.mkdir(parents=True, exist_ok=True)
    OG.mkdir(parents=True, exist_ok=True)
    for stale in IMG.glob("*.webp"):
        stale.unlink()
    for name, (source,) in PHOTOS.items():
        src = SRC_ASSETS / source
        if not src.exists():
            print("missing source:", src)
            continue
        hero = webp(src, IMG / f"{name}.webp", HERO)
        card = webp(src, IMG / f"{name}-card.webp", CARD, quality=68)
        og_crop(src, OG / f"{name}.jpg")
        print(f"{name:34} hero={hero} card={card}")
    # default OG image reuses the brand card
    og_crop(SRC_ASSETS / "hero-1200.webp", OG / "default.jpg", quality=78)
    # card-only image for the visa guide (its page has no hero photo)
    webp(SRC_ASSETS / "dest-hoian.jpg", IMG / "visa-card.webp", CARD, quality=68, max_bytes=70_000)
    print("default OG image written")
    for name in COPY:
        src = SRC_ASSETS / name
        if src.exists():
            shutil.copy(src, IMG / name)
            print("copied", name)
        else:
            print("missing", name)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Make a 2.35:1 WeChat cover (1880x800): text on the left, an optional image on the right.

  cover.py out.png --title "网站 → 公众号" --lines "三周近 10 万用户" "粉丝 6.7k → 29.4k" \
           --pill "附开源 Skill" --foot example.com --image hero.jpg --theme latepost

The cover shows in the feed at a small size: keep the title under ~10 characters
and at most two short lines. Use a real product screenshot or illustration as
--image when you have one.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import PALETTES  # noqa: E402

FONTS = ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc",
         "/System/Library/Fonts/STHeiti Medium.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
         "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc", "C:/Windows/Fonts/msyhbd.ttc"]


def font(size: int, path: str | None) -> ImageFont.FreeTypeFont:
    for f in [path] + FONTS if path else FONTS:
        if f and Path(f).exists():
            return ImageFont.truetype(f, size)
    raise SystemExit("no CJK font found; pass --font")


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--title", required=True)
    ap.add_argument("--lines", nargs="*", default=[])
    ap.add_argument("--pill")
    ap.add_argument("--foot")
    ap.add_argument("--image", type=Path, help="right-hand image, cropped to fill")
    ap.add_argument("--theme", default="latepost", choices=sorted(PALETTES))
    ap.add_argument("--font")
    args = ap.parse_args()
    p = PALETTES[args.theme]
    W, H = 1880, 800
    bg = hex_rgb(p["bg"])
    img = Image.new("RGB", (W, H), bg)
    text_w = W
    if args.image:
        art = ImageOps.fit(Image.open(args.image).convert("RGB"), (860, H))
        img.paste(art, (W - 860, 0))
        text_w = W - 860
    d = ImageDraw.Draw(img)
    x, y = 96, 150
    d.text((x, y), args.title, font=font(96, args.font), fill=hex_rgb(p["heading"]))
    y += 150
    for n, line in enumerate(args.lines[:2]):
        d.text((x, y), line, font=font(52, args.font), fill=hex_rgb(p["accent"] if n else p["heading"]))
        y += 80
    if args.pill:
        f = font(34, args.font)
        w = d.textlength(args.pill, font=f) + 72
        y += 60
        d.rounded_rectangle((x, y, x + w, y + 80), radius=40, fill=hex_rgb(p.get("tag", p["accent"])))
        d.text((x + 36, y + 18), args.pill, font=f, fill=(255, 255, 255))
    if args.foot:
        d.text((x, H - 120), args.foot, font=font(34, args.font), fill=hex_rgb(p["muted"]))
    if text_w < W and d.textlength(args.title, font=font(96, args.font)) > text_w - x - 40:
        print("WARN title is wider than the text area; shorten it", file=sys.stderr)
    img.save(args.out)
    print(f"cover: {args.out} ({W}x{H})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

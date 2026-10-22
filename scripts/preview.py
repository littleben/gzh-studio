#!/usr/bin/env python3
"""Phone-width preview of a rendered article, with a copy-to-WeChat button.

  preview.py article.md [--theme T] [-o preview.html]        write the preview page
  preview.py article.md --shots DIR                          also screenshot it at 390 px (needs playwright)

Open the page, press the button, paste into the WeChat editor: styles survive
because the copied fragment is the validated inline-styled HTML.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from render import render  # noqa: E402

PAGE = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>body{{margin:0;background:#f3f3f3}}#bar{{position:sticky;top:0;z-index:9;display:flex;justify-content:space-between;
align-items:center;padding:10px 14px;background:#fff;border-bottom:1px solid #e5e5e5;font:13px -apple-system,sans-serif;color:#666}}
#bar button{{border:0;border-radius:8px;background:#07c160;color:#fff;font-weight:700;padding:8px 14px;cursor:pointer}}
#page{{max-width:420px;margin:0 auto;background:#fff;padding:16px 12px 40px}}</style></head><body>
<div id="bar"><span>手机宽度预览</span><button onclick="copyIt(this)">复制到公众号</button></div>
<div id="page"><div id="gzh">{body}</div></div>
<script>function copyIt(b){{const r=document.createRange();r.selectNodeContents(document.getElementById('gzh'));
const s=getSelection();s.removeAllRanges();s.addRange(r);document.execCommand('copy');s.removeAllRanges();
b.textContent='已复制，去公众号编辑器粘贴';setTimeout(()=>b.textContent='复制到公众号',2500)}}</script></body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("article", type=Path)
    ap.add_argument("--theme")
    ap.add_argument("--cta")
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--shots", type=Path, help="directory for 390 px screenshots of the whole page")
    args = ap.parse_args()
    article = args.article.resolve()
    meta, body, warnings = render(article.read_text(encoding="utf-8"), args.theme, args.cta)
    for w in warnings:
        print(f"WARN {w}", file=sys.stderr)

    def local(m: re.Match) -> str:
        src = Path(m.group(1))
        src = src if src.is_absolute() else article.parent / src
        return f'src="{src.as_uri()}"'

    body = re.sub(r'src="(?!https?:|file:)([^"]+)"', local, body)
    out = args.out or article.with_suffix(".preview.html")
    out.write_text(PAGE.format(title=meta.get("title", "preview"), body=body), encoding="utf-8")
    print(f"preview: {out}")
    if args.shots:
        shoot(out, args.shots)
    return 0


def shoot(page: Path, folder: Path) -> None:
    from playwright.sync_api import sync_playwright
    folder.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:  # noqa: BLE001 - fall back to the installed Chrome
            browser = p.chromium.launch(channel="chrome")
        pg = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        pg.goto(page.as_uri())
        pg.wait_for_timeout(1200)
        height = pg.evaluate("document.body.scrollHeight")
        for n, y in enumerate(range(0, height, 2000)):
            pg.screenshot(path=str(folder / f"phone-{n:02d}.png"), full_page=True,
                          clip={"x": 0, "y": y, "width": 390, "height": min(2000, height - y)})
        browser.close()
    print(f"screenshots: {folder}")


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Sharp (2x) screenshots of real pages for article illustrations.

Logged-in pages (analytics, the WeChat backend, dashboards): start Chrome with
--remote-debugging-port=9222 and a profile that is signed in, then

  shot.py out.png --cdp http://localhost:9222 --url https://analytics.google.com/... --clip 340,78,1130,610
  shot.py out.png --cdp http://localhost:9222 --tab mp.weixin.qq.com --selector ".chart"

Public pages need no Chrome profile:

  shot.py out.png --url https://example.com --width 1280 --clip 0,0,1280,900
  shot.py out.png --url https://example.com --mobile            # 390 px phone, WeChat user agent with --wechat

--clip x,y,w,h is in CSS pixels; --tab reuses an open tab whose URL contains the text.
Crop to the part the sentence talks about: a full wide page is unreadable on a phone.
"""
from __future__ import annotations

import argparse
import base64
from pathlib import Path

WECHAT_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
             "Mobile/15E148 MicroMessenger/8.0.50(0x1800322d) NetType/WIFI Language/zh_CN")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--url")
    ap.add_argument("--cdp", help="Chrome DevTools endpoint of a signed-in Chrome")
    ap.add_argument("--tab", help="reuse the open tab whose URL contains this text")
    ap.add_argument("--clip", help="x,y,w,h in CSS pixels")
    ap.add_argument("--selector", help="screenshot this element instead of a clip")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=1000)
    ap.add_argument("--mobile", action="store_true", help="390 px phone viewport")
    ap.add_argument("--wechat", action="store_true", help="with --mobile: WeChat in-app browser user agent")
    ap.add_argument("--wait", type=int, default=4000, help="ms to wait after load")
    ap.add_argument("--dark", action="store_true")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        if args.cdp:
            browser = p.chromium.connect_over_cdp(args.cdp)
            ctx = browser.contexts[0]
            page = next((t for t in ctx.pages if args.tab and args.tab in t.url), None) or ctx.new_page()
            own = page.url == "about:blank"
        else:
            try:
                browser = p.chromium.launch()
            except Exception:  # noqa: BLE001 - no bundled browser: use the installed Chrome
                browser = p.chromium.launch(channel="chrome")
            opts = {"color_scheme": "dark" if args.dark else "light", "locale": "zh-CN"}
            if args.mobile:
                opts.update(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
                            user_agent=WECHAT_UA if args.wechat else None)
            ctx = browser.new_context(**{k: v for k, v in opts.items() if v is not None})
            page, own = ctx.new_page(), True
        w, h = (390, 844) if args.mobile else (args.width, args.height)
        session = ctx.new_cdp_session(page)
        # Playwright's own screenshot stays at 1x on a CDP-attached page; force 2x through CDP.
        session.send("Emulation.setDeviceMetricsOverride",
                     {"width": w, "height": h, "deviceScaleFactor": 2, "mobile": args.mobile})
        if args.url:
            page.goto(args.url, wait_until="domcontentloaded")
        page.wait_for_timeout(args.wait)
        if args.selector:
            box = page.locator(args.selector).first.bounding_box()
            clip = {"x": box["x"], "y": box["y"], "width": box["width"], "height": box["height"]}
        elif args.clip:
            x, y, cw, ch = (float(v) for v in args.clip.split(","))
            clip = {"x": x, "y": y, "width": cw, "height": ch}
        else:
            clip = {"x": 0, "y": 0, "width": w, "height": h}
        shot = session.send("Page.captureScreenshot",
                            {"format": "png", "captureBeyondViewport": True, "clip": {**clip, "scale": 1}})
        args.out.write_bytes(base64.b64decode(shot["data"]))
        session.send("Emulation.clearDeviceMetricsOverride")
        if own and args.cdp:
            page.close()
        if not args.cdp:
            browser.close()
    print(f"screenshot: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

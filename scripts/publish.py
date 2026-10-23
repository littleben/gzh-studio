#!/usr/bin/env python3
"""Render, validate and push a Markdown article to the WeChat draft box.

  publish.py article.md --dry-run            render + validate + prepare images, upload nothing
  publish.py article.md                      call the API from this machine (IP must be whitelisted)
  publish.py article.md --ssh myserver       call the API on a whitelisted server over SSH

Credentials: WECHAT_APP_ID / WECHAT_APP_SECRET, or --config file with
  app_id: wx...
  app_secret: ...
With --ssh they travel over SSH stdin, never in argv, logs or uploaded files.
Needs Pillow locally, and requests wherever the API call runs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from render import render, split_frontmatter  # noqa: E402

MAX_BYTES = 1_000_000


def credentials(config: Path | None) -> tuple[str, str]:
    if config:
        text = config.read_text(encoding="utf-8")
        found = {k: re.search(rf"^\s*{k}:\s*['\"]?([^'\"#\n]+?)['\"]?\s*$", text, re.M) for k in ("app_id", "app_secret")}
        if not all(found.values()):
            raise SystemExit(f"{config} needs app_id and app_secret")
        return found["app_id"].group(1), found["app_secret"].group(1)
    try:
        return os.environ["WECHAT_APP_ID"], os.environ["WECHAT_APP_SECRET"]
    except KeyError:
        raise SystemExit("set WECHAT_APP_ID / WECHAT_APP_SECRET or pass --config") from None


def prepare_image(src: Path, dest: Path, cover: bool = False) -> None:
    """Save as JPEG <= 1 MB, at most 1080 px wide; crop the cover to 2.35:1."""
    from PIL import Image
    im = Image.open(src).convert("RGB")
    if cover:
        w, h = im.size
        th = round(w / 2.35)
        if h > th:
            top = (h - th) // 2
            im = im.crop((0, top, w, top + th))
        elif h < th:
            tw = round(h * 2.35)
            left = (w - tw) // 2
            im = im.crop((left, 0, left + tw, h))
    if im.width > 1080:
        im = im.resize((1080, round(im.height * 1080 / im.width)), Image.LANCZOS)
    for quality in (88, 78, 68, 58, 48):
        im.save(dest, "JPEG", quality=quality, optimize=True)
        if dest.stat().st_size <= MAX_BYTES:
            return
    raise RuntimeError(f"{src} is still over 1 MB after compression")


def build_job(article: Path, job: Path, theme: str | None, cta: str | None) -> dict:
    md = article.read_text(encoding="utf-8")
    meta, content, warnings = render(md, theme, cta)
    for w in warnings:
        print(f"WARN {w}", file=sys.stderr)
    title, cover = meta.get("title", "").strip(), meta.get("cover", "").strip()
    if not title or not cover:
        raise SystemExit("frontmatter needs title and cover")
    if len(title) > 64:
        raise SystemExit(f"title is {len(title)} characters; WeChat allows 64")

    html_path = job / "content.html"
    html_path.write_text(content, encoding="utf-8")
    res = subprocess.run([sys.executable, str(HERE / "validate.py"), str(html_path)], capture_output=True, text=True)
    print(res.stdout.strip().splitlines()[-1] if res.stdout.strip() else "validator: no output")
    if res.returncode != 0:
        raise SystemExit("validator reported errors:\n" + res.stdout)

    (job / "assets").mkdir()
    base = article.parent
    for n, raw in enumerate(dict.fromkeys(re.findall(r'<img src="([^"]+)"', content))):
        src = Path(raw) if Path(raw).is_absolute() else (base / raw)
        if not src.is_file():
            raise SystemExit(f"image not found: {raw}")
        name = f"{n:02d}.jpg"
        prepare_image(src, job / "assets" / name)
        content = content.replace(f'src="{raw}"', f'src="assets/{name}"')
    html_path.write_text(content, encoding="utf-8")
    cover_src = Path(cover) if Path(cover).is_absolute() else base / cover
    prepare_image(cover_src, job / "cover.jpg", cover=True)

    body = re.sub(r"<!--.*?-->", "", split_frontmatter(md)[1], flags=re.S)
    first = next((ln for ln in body.splitlines()
                  if ln.strip() and not ln.startswith(("!", "#", "-", "`", ">", "|"))), "")
    digest = meta.get("digest") or re.sub(r"\*\*|\+\+|==|`", "", first).strip()[:110]
    info = {"title": title, "digest": digest, "author": meta.get("author", "")}
    (job / "meta.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    shutil.copy2(HERE / "wechat_api.py", job / "wechat_api.py")
    sizes = {p.name: p.stat().st_size for p in sorted((job / "assets").iterdir())}
    print(f"title: {title}\ndigest: {digest}\nimages: {len(sizes)}  cover: {(job / 'cover.jpg').stat().st_size} bytes")
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description="Render and push an article to the WeChat draft box.")
    ap.add_argument("article", type=Path)
    ap.add_argument("--theme", help="override the frontmatter theme")
    ap.add_argument("--cta", help="footer call to action")
    ap.add_argument("--dry-run", action="store_true", help="render, validate and prepare images only")
    ap.add_argument("--preview", type=Path, help="also write the rendered HTML here")
    ap.add_argument("--ssh", metavar="HOST", help="run the API call on this whitelisted SSH host")
    ap.add_argument("--config", type=Path, help="file with app_id / app_secret")
    args = ap.parse_args()
    article = args.article.resolve()

    with tempfile.TemporaryDirectory(prefix="markdown-to-wechat-") as tmp:
        job = Path(tmp) / "job"
        job.mkdir()
        build_job(article, job, args.theme, args.cta)
        if args.preview:
            shutil.copy2(job / "content.html", args.preview)
        if args.dry_run:
            print("dry run: nothing uploaded")
            return 0
        app_id, app_secret = credentials(args.config)
        if not args.ssh:
            sys.path.insert(0, str(job))
            from wechat_api import run_job
            run_job(str(job), app_id, app_secret)
            return 0
        remote = f"/tmp/markdown-to-wechat-{uuid.uuid4().hex[:12]}"
        subprocess.run(["ssh", args.ssh, f"mkdir -p {shlex.quote(remote)}"], check=True)
        subprocess.run(["scp", "-q", "-r", *[str(p) for p in job.iterdir()], f"{args.ssh}:{remote}/"], check=True)
        script = (f"set -eu\ntrap 'rm -rf {shlex.quote(remote)}' EXIT\n"
                  f"export WECHAT_APP_ID={shlex.quote(app_id)}\nexport WECHAT_APP_SECRET={shlex.quote(app_secret)}\n"
                  f"python3 {shlex.quote(remote + '/wechat_api.py')} {shlex.quote(remote)}\n")
        subprocess.run(["ssh", "-o", "BatchMode=yes", args.ssh, "bash -s"], input=script, text=True, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

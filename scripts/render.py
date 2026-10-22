#!/usr/bin/env python3
"""Render a WeChat Official Account article from Markdown to paste/API-ready HTML.

Platform rules (inline styles only, <section> instead of <div>, every text node
wrapped in <span leaf="">) and the component designs come from gzh-design
(https://github.com/isjiamu/gzh-design-skill, AGPL-3.0). Every theme is built
from one palette, so all components work in every theme.

Markdown it understands:
  frontmatter title / cover / author / digest / cta / theme
  ## chapter (auto-numbered in tag themes; a leading 「一、」 is dropped)
  ### section, paragraphs (the first one is the lead), lists, ``` fences (```bash),
  images ![caption](path) (alt 封面 is skipped), | tables |, ---
  inline: **bold**  ++underline++  ==highlight==  `code`  [text](url)
  > **Title** + lines   bordered quote card
  > single plain line   centred pull quote
  > [!TYPE] ...         INTRO TOC DATA TIMELINE PILLS QUOTE NOTE WARN TIP END
  **关于作者** at the very end becomes the footer.

Usage: render.py article.md [-o out.html] [--theme latepost] [--cta "..."]
Density warnings follow references/layout-standard.md.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

FONT = ("-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB',"
        "'Microsoft YaHei',sans-serif")
SERIF = "'Noto Serif SC','Songti SC',Georgia,serif"
MONO = "'SF Mono',Menlo,Consolas,monospace"
DEFAULT_CTA = "如果这篇文章对你有帮助，欢迎点赞、在看、转发，让更多人看到。"

# One palette per theme. h2: tag (numbered block) | bar (left bar) |
# rule (small number + bottom rule) | center (serif, centred).
PALETTES = {
    "latepost": dict(name="晚点红", accent="#EE0000", dark="#B00000", bg="#FFF4F4", border="#FFE4E4",
                     text="#1a1a1a", heading="#1a1a1a", muted="#888888", line="#e0e0e0",
                     underline="#FFB3B3", strong="accent", size=16, lh=1.75, ls=0.8, h2="tag"),
    "emerald": dict(name="摸鱼绿", accent="#059669", dark="#065F46", bg="#ECFDF5", border="#D1FAE5",
                    text="#374151", heading="#111827", muted="#9CA3AF", line="#E5E7EB",
                    underline="#A7F3D0", strong="accent", size=15, lh=1.85, ls=0.5, h2="tag"),
    "ocean": dict(name="科技蓝", accent="#2563EB", dark="#1E40AF", bg="#EFF6FF", border="#DBEAFE",
                  text="#334155", heading="#0F172A", muted="#94A3B8", line="#E2E8F0",
                  underline="#93C5FD", strong="accent", size=15, lh=1.8, ls=0.5, h2="bar"),
    "graphite": dict(name="石墨极简", accent="#52525B", dark="#27272A", bg="#F4F4F5", border="#E4E4E7",
                     text="#3F3F46", heading="#27272A", muted="#A1A1AA", line="#E4E4E7",
                     underline="#52525B", strong="heading", size=15, lh=1.8, ls=0.3, h2="rule"),
    "olive": dict(name="橄榄手记", accent="#ED7B2F", dark="#1E1F23", bg="#EEEFE9", border="#E5E7E0",
                  text="#4D4F46", heading="#23251D", muted="#9EA096", line="#BFC1B7",
                  underline="#ED7B2F", strong="heading", size=15, lh=1.85, ls=0.5, h2="tag", tag="#1E1F23"),
    "zen": dict(name="留白禅意", accent="#4A5D52", dark="#3D5046", bg="#EEF3F0", border="#D6E4DC",
                text="#525252", heading="#2B2B2B", muted="#A3A3A3", line="#E8E8E8",
                underline="#B5C8BC", strong="heading", size=15, lh=1.9, ls=0.3, h2="center", serif=True),
}


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def leaf(text: str) -> str:
    return f'<span leaf="">{html.escape(text, quote=False)}</span>'


class Renderer:
    def __init__(self, theme: str):
        if theme not in PALETTES:
            raise SystemExit(f"unknown theme {theme}; choose from {', '.join(PALETTES)}")
        self.p = p = PALETTES[theme]
        self.h2_count = 0
        self.head_font = SERIF if p.get("serif") else FONT
        strong = p["accent"] if p["strong"] == "accent" else p["heading"]
        self.s = {
            "p": (f'margin:20px 0;font-size:{p["size"]}px;line-height:{p["lh"]};letter-spacing:{p["ls"]}px;'
                  f'text-align:justify;color:{p["text"]};'),
            "lead": f'font-size:{p["size"] + 1}px;font-weight:600;color:{p["heading"]};',
            "strong": f"color:{strong};font-weight:700;",
            "underline": f'border-bottom:2px solid {p["underline"]};font-weight:600;color:{p["heading"]};',
            "mark": f'background:{p["border"]};color:{p["dark"]};padding:2px 6px;border-radius:3px;font-weight:700;',
            "code": f'background:{p["bg"]};color:{p["dark"]};padding:2px 6px;border-radius:4px;font-size:14px;font-weight:600;',
        }

    # ---- inline ----

    def inline(self, text: str) -> str:
        s, out, pos = self.s, [], 0
        pattern = re.compile(r"\*\*(?P<b>.+?)\*\*|\+\+(?P<u>.+?)\+\+|==(?P<h>.+?)==|`(?P<c>[^`]+)`|"
                             r"\[(?P<lt>[^\]]+)\]\((?P<lu>[^)]+)\)")
        for m in pattern.finditer(text):
            if m.start() > pos:
                out.append(leaf(text[pos:m.start()]))
            if m.group("b") is not None:
                out.append(f'<strong style="{s["strong"]}">{leaf(m.group("b"))}</strong>')
            elif m.group("u") is not None:
                out.append(f'<span style="{s["underline"]}">{leaf(m.group("u"))}</span>')
            elif m.group("h") is not None:
                out.append(f'<span style="{s["mark"]}">{leaf(m.group("h"))}</span>')
            elif m.group("c") is not None:
                out.append(f'<span style="{s["code"]}font-family:{MONO};">{leaf(m.group("c"))}</span>')
            else:  # WeChat strips outbound links; keep the text.
                out.append(leaf(m.group("lt")))
            pos = m.end()
        if pos < len(text):
            out.append(leaf(text[pos:]))
        return "".join(out)

    # ---- text blocks ----

    def para(self, text: str, lead: bool = False) -> str:
        return f'<p style="{self.s["p"]}{self.s["lead"] if lead else ""}">{self.inline(text)}</p>'

    def h2(self, title: str) -> str:
        p, kind = self.p, self.p["h2"]
        self.h2_count += 1
        m = re.match(r"^(?:[一二三四五六七八九十]+、|\d+[.、]\s*)(.+)$", title)
        title = m.group(1) if m else title
        num = f"{self.h2_count:02d}"
        font = f"font-family:{self.head_font};"
        if kind == "tag":
            return (f'<section style="margin:48px 0 24px;padding-bottom:12px;border-bottom:2px solid {p["accent"]};'
                    f'display:flex;align-items:center;">'
                    f'<span style="display:inline-block;background:{p.get("tag", p["accent"])};color:#FFFFFF;font-size:17px;'
                    f'font-weight:900;padding:3px 12px;border-radius:6px;margin-right:12px;line-height:1.3;flex-shrink:0;">'
                    f'{leaf(num)}</span><h3 style="font-size:19px;font-weight:800;color:{p["heading"]};margin:0;'
                    f'letter-spacing:0.5px;line-height:1.45;{font}">{leaf(title)}</h3></section>')
        if kind == "bar":
            return (f'<h3 style="font-size:20px;font-weight:800;color:{p["heading"]};margin:44px 0 20px;'
                    f'padding:6px 0 6px 12px;border-left:6px solid {p["accent"]};background:{p["bg"]};'
                    f'border-radius:0 6px 6px 0;line-height:1.4;{font}">{leaf(title)}</h3>')
        if kind == "rule":
            return (f'<section style="margin:52px 0 24px;padding-bottom:14px;border-bottom:1px solid {p["line"]};">'
                    f'<p style="margin:0 0 6px;font-size:13px;font-weight:700;letter-spacing:2px;color:{p["muted"]};">'
                    f'{leaf(num)}</p><h3 style="font-size:20px;font-weight:800;color:{p["heading"]};margin:0;'
                    f'line-height:1.4;{font}">{leaf(title)}</h3></section>')
        return (f'<section style="margin:60px 0 28px;text-align:center;">'
                f'<p style="margin:0 0 8px;font-size:13px;letter-spacing:4px;color:{p["accent"]};">{leaf(num)}</p>'
                f'<h3 style="font-size:20px;font-weight:700;color:{p["heading"]};margin:0 0 14px;line-height:1.5;'
                f'letter-spacing:2px;{font}">{leaf(title)}</h3>'
                f'<section style="width:32px;height:1px;background:{p["accent"]};margin:0 auto;"><span leaf=""><br></span>'
                f'</section></section>')

    def h3(self, title: str) -> str:
        p = self.p
        return (f'<p style="font-size:17px;font-weight:700;line-height:1.4;letter-spacing:0.5px;padding:8px 12px;'
                f'border-left:4px solid {p["accent"]};background:{p["bg"]};border-radius:0 6px 6px 0;'
                f'color:{p["heading"]};margin:28px 0 16px;font-family:{self.head_font};">{leaf(title)}</p>')

    def ordered(self, items: list[str]) -> str:
        p = self.p
        rows = "".join(
            f'<section style="display:flex;align-items:flex-start;margin-bottom:12px;">'
            f'<span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;'
            f'background:{p["accent"]};color:#FFFFFF;font-size:12px;font-weight:700;border-radius:50%;flex-shrink:0;'
            f'margin:3px 10px 0 0;">{leaf(str(i))}</span>'
            f'<p style="font-size:{p["size"]}px;color:{p["text"]};margin:0;line-height:{p["lh"]};flex:1;'
            f'text-align:justify;">{self.inline(x)}</p></section>'
            for i, x in enumerate(items, 1))
        return f'<section style="margin:20px 0 24px;">{rows}</section>'

    def bullets(self, items: list[str]) -> str:
        p = self.p
        rows = "".join(
            f'<p style="{self.s["p"]}margin:0 0 10px;padding-left:18px;text-indent:-18px;">'
            f'<span style="color:{p["accent"]};font-weight:700;">{leaf("• ")}</span>{self.inline(x)}</p>'
            for x in items)
        return f'<section style="margin:20px 0 24px;">{rows}</section>'

    def code_block(self, lines: list[str], lang: str = "") -> str:
        rows = "".join(
            f'<p style="margin:0;font-family:{MONO};line-height:1.6;color:#f5f5f5;font-size:12px;">'
            f'{leaf(ln.replace("    ", "　　") or " ")}</p>' for ln in lines)
        dot = ("display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:7px;"
               "font-size:0;line-height:0;overflow:hidden;background:")
        bar = "".join(f'<span style="{dot}{c};">.</span>' for c in ("#FF5F56", "#FFBD2E", "#27C93F"))
        if lang:
            bar += (f'<span style="margin-left:6px;font-size:12px;color:#8a8a8a;font-family:{MONO};'
                    f'letter-spacing:1px;">{leaf(lang)}</span>')
        return (f'<section style="margin:28px 0;border-radius:8px;overflow:hidden;background:#2a2a2a;">'
                f'<section style="display:flex;align-items:center;padding:9px 14px;background:#1f1f1f;">{bar}</section>'
                f'<section style="padding:12px 16px;">{rows}</section></section>')

    def image(self, src: str, caption: str) -> str:
        p = self.p
        out = (f'<section style="margin:32px 0 8px;background:#FFFFFF;border-radius:12px;padding:6px;'
               f'border:1px solid #E5E7EB;box-shadow:0 4px 12px -2px rgba(0,0,0,0.08);">'
               f'<section style="margin:0;border-radius:8px;overflow:hidden;"><span leaf=""><img src="{html.escape(src)}" '
               f'style="max-width:100%;height:auto;display:block;margin:0 auto;"></span></section></section>')
        if caption:
            out += (f'<p style="font-size:13px;color:{p["muted"]};text-align:center;margin:0 0 28px;">'
                    f'{leaf("— " + caption)}</p>')
        return out

    def table(self, header: list[str], rows: list[list[str]]) -> str:
        p = self.p
        th = "".join(f'<th style="background:{p["accent"]};color:#FFFFFF;font-weight:700;padding:8px 10px;'
                     f'text-align:left;">{leaf(h)}</th>' for h in header)
        body = ""
        for n, row in enumerate(rows):
            bg = f'background:{p["bg"]};' if n % 2 else ""
            body += "<tr>" + "".join(
                f'<td style="padding:8px 10px;border-bottom:1px solid {p["border"]};color:{p["text"]};{bg}'
                f'vertical-align:top;line-height:1.6;">{self.inline(c)}</td>' for c in row) + "</tr>"
        return (f'<section style="margin:24px 0;overflow-x:auto;"><table style="width:100%;border-collapse:collapse;'
                f'font-size:14px;"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></section>')

    def divider(self) -> str:
        return (f'<p style="text-align:center;margin:36px 0;font-size:14px;font-weight:700;letter-spacing:4px;'
                f'color:{self.p["accent"]};">{leaf("- - -")}</p>')

    # ---- quotes and callouts ----

    def quote(self, lines: list[str]) -> str:
        p = self.p
        if len(lines) == 1 and "**" not in lines[0]:
            return (f'<p style="margin:36px 24px;padding:14px 0;border-top:1px solid {p["heading"]};'
                    f'border-bottom:1px solid {p["heading"]};text-align:center;font-size:18px;font-weight:700;'
                    f'line-height:1.6;letter-spacing:2px;color:{p["accent"]};font-family:{self.head_font};">'
                    f'{self.inline(lines[0])}</p>')
        rows = ""
        for i, ln in enumerate(lines):
            title = re.fullmatch(r"\*\*(.+)\*\*", ln)
            if i == 0 and title:
                rows += f'<p style="font-size:16px;font-weight:700;color:{p["accent"]};margin:0 0 10px;">{leaf(title.group(1))}</p>'
            else:
                rows += (f'<p style="font-size:15px;line-height:1.75;color:{p["text"]};margin:0 0 8px;">'
                         f'{self.inline(ln)}</p>')
        return (f'<section style="margin:28px 0;padding:20px 22px 14px;border:1px solid {p["heading"]};'
                f'border-bottom:3px solid {p["accent"]};">{rows}</section>')

    def intro(self, text: str) -> str:
        p = self.p
        pieces = []
        for part in re.split(r"(==.+?==)", text):
            if part.startswith("==") and part.endswith("=="):
                pieces.append(f'<span style="background:{p["accent"]};color:#FFFFFF;padding:2px 8px;border-radius:4px;">'
                              f'{leaf(part[2:-2])}</span>')
            elif part:
                pieces.append(self.inline(part))
        return (f'<section style="margin:8px 0 32px;background:#FFFFFF;border-radius:12px;'
                f'box-shadow:0 4px 24px -4px {rgba(p["accent"], 0.18)};padding:26px 22px 22px;overflow:hidden;">'
                f'<p style="font-size:42px;color:{p["accent"]};font-weight:900;margin:0;line-height:0.6;">{leaf("“")}</p>'
                f'<p style="font-size:17px;font-weight:800;color:{p["heading"]};margin:12px 0 0;line-height:1.9;'
                f'font-family:{self.head_font};">{"".join(pieces)}</p></section>')

    def toc(self, items: list[str]) -> str:
        p = self.p
        items = items[:3]
        cards = "".join(
            f'<section style="flex:1;background:{p["bg"]};border-radius:10px;padding:14px 10px;'
            f'{"margin-right:8px;" if n < len(items) else ""}text-align:center;border:1px solid {p["border"]};">'
            f'<p style="display:inline-block;background:{p.get("tag", p["accent"])};color:#FFFFFF;font-size:12px;'
            f'font-weight:800;padding:2px 10px;border-radius:4px;margin:0 0 8px;">{leaf(f"{n:02d}")}</p>'
            f'<p style="font-size:13px;font-weight:700;color:{p["heading"]};margin:0;line-height:1.5;">{leaf(item)}</p>'
            f'</section>' for n, item in enumerate(items, 1))
        return (f'<section style="margin:0 0 32px;"><p style="font-size:14px;color:{p["muted"]};margin:0 0 12px;'
                f'letter-spacing:1px;">{leaf("本文看点")}</p><section style="display:flex;">{cards}</section></section>')

    def data_cards(self, rows: list[tuple[str, str]]) -> str:
        p = self.p
        big = "28px" if len(rows) <= 2 else "22px"
        cards = "".join(
            f'<section style="flex:1;background:{p["bg"]};border-radius:10px;padding:16px 8px;'
            f'{"margin-right:8px;" if n < len(rows) else ""}text-align:center;border:1px solid {p["border"]};">'
            f'<p style="font-size:{big};font-weight:900;color:{p["accent"]};margin:0 0 6px;line-height:1.1;">{leaf(num)}</p>'
            f'<p style="font-size:12px;color:{p["muted"]};margin:0;line-height:1.5;">{leaf(label)}</p></section>'
            for n, (num, label) in enumerate(rows, 1))
        return f'<section style="display:flex;margin:24px 0;">{cards}</section>'

    def timeline(self, rows: list[tuple[str, str]]) -> str:
        p, out = self.p, []
        for n, (title, text) in enumerate(rows, 1):
            line = (f'<section style="width:2px;background:{p["border"]};flex:1;margin-top:4px;min-height:36px;">'
                    f'<span leaf=""><br></span></section>') if n < len(rows) else ""
            out.append(
                f'<section style="display:flex;"><section style="display:flex;flex-direction:column;align-items:center;'
                f'margin-right:14px;flex-shrink:0;"><section style="width:14px;height:14px;border-radius:50%;'
                f'border:3px solid {p["accent"]};background:#FFFFFF;margin-top:5px;"><span leaf=""><br></span></section>'
                f'{line}</section><section style="flex:1;padding-bottom:14px;">'
                f'<p style="margin:0 0 4px;font-size:15px;font-weight:800;color:{p["heading"]};">{leaf(title)}</p>'
                f'<p style="font-size:15px;margin:0;color:{p["text"]};line-height:1.75;text-align:justify;">'
                f'{self.inline(text)}</p></section></section>')
        return f'<section style="margin:24px 0;">{"".join(out)}</section>'

    def pills(self, rows: list[tuple[str, str]]) -> str:
        p = self.p
        out = "".join(
            f'<section style="margin-bottom:14px;"><p style="margin:0 0 6px;"><span style="display:inline-block;'
            f'font-size:14px;font-weight:700;color:{p["dark"]};background:{p["border"]};padding:3px 12px;'
            f'border-radius:999px;">{leaf("● " + title)}</span></p><p style="font-size:15px;color:{p["text"]};'
            f'margin:0;line-height:1.75;text-align:justify;">{self.inline(text)}</p></section>'
            for title, text in rows)
        return f'<section style="margin:20px 0 24px;">{out}</section>'

    def side_quote(self, text: str) -> str:
        p = self.p
        return (f'<section style="background:{p["bg"]};border-radius:0 10px 10px 0;border-left:4px solid {p["accent"]};'
                f'padding:16px 20px;margin:24px 0;"><p style="font-size:16px;font-weight:800;color:{p["dark"]};margin:0;'
                f'line-height:1.8;">{self.inline(text)}</p></section>')

    def note(self, text: str) -> str:
        p = self.p
        return (f'<section style="border-left:4px solid #D6D3D1;padding:12px 18px;margin:24px 0;background:#FAFAFA;'
                f'border-radius:0 8px 8px 0;"><p style="font-size:14px;color:{p["text"]};margin:0;line-height:1.8;'
                f'text-align:justify;">{self.inline(text)}</p></section>')

    def warn(self, text: str) -> str:
        p = self.p
        return (f'<section style="padding:6px 0 4px;margin:20px 0;"><p style="margin:0 0 6px;font-size:12px;'
                f'font-weight:700;letter-spacing:1px;color:{p["accent"]};">{leaf("！踩坑提示")}</p>'
                f'<p style="font-size:15px;color:{p["text"]};margin:0;line-height:1.75;text-align:justify;">'
                f'{self.inline(text)}</p></section>')

    def tip(self, text: str) -> str:
        p = self.p
        return (f'<section style="background:{p["bg"]};border-left:4px solid {p["accent"]};border-radius:0 8px 8px 0;'
                f'padding:14px 18px;margin:24px 0;"><p style="font-size:15px;font-weight:700;color:{p["dark"]};margin:0;'
                f'line-height:1.8;">{self.inline(text)}</p></section>')

    def end_mark(self) -> str:
        p = self.p
        side = f'display:inline-block;height:1px;width:60px;background:{p["accent"]};'
        return (f'<section style="display:flex;align-items:center;justify-content:center;margin:40px 0 28px;">'
                f'<span style="{side}margin-right:12px;"><span leaf=""><br></span></span>'
                f'<span style="font-size:11px;color:{p["accent"]};letter-spacing:3px;font-weight:700;">{leaf("END")}</span>'
                f'<span style="{side}margin-left:12px;"><span leaf=""><br></span></span></section>')

    def footer(self, cta: str, about: list[str]) -> str:
        p = self.p
        small = f'font-size:14px;line-height:1.8;color:{p["muted"]};letter-spacing:0.5px;'
        body = f'<p style="margin:0 0 20px;{small}">{leaf(cta)}</p>' if cta else ""
        for i, line in enumerate(about):
            weight = f'font-weight:700;color:{p["text"]};' if i == 0 else ""
            body += f'<p style="margin:0 0 4px;{small}{weight}">{self.inline(line.lstrip("- "))}</p>'
        return f'<section style="border-top:1px solid {p["line"]};padding-top:24px;margin:40px 0 24px;">{body}</section>'


def split_frontmatter(src: str) -> tuple[dict, str]:
    meta: dict[str, str] = {}
    if src.startswith("---\n"):
        end = src.index("\n---", 4)
        for line in src[4:end].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip("\"'")
        src = src[end + 4:]
    return meta, src


CONTAINERS = {"image", "quote", "callout", "table", "code"}


def render(md: str, theme: str | None = None, cta: str | None = None) -> tuple[dict, str, list[str]]:
    meta, body = split_frontmatter(md)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)  # template notes for the writer
    r = Renderer(theme or meta.get("theme") or "latepost")
    about: list[str] = []
    m = re.search(r"\n\*\*关于作者\*\*\s*\n(.*)\Z", body, re.S)
    if m:
        about = ["关于作者"] + [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]
        body = body[:m.start()]
    blocks = re.split(r"\n\s*\n", body.strip())
    parts: list[str] = []
    kinds: list[str] = []
    warnings: list[str] = []
    counts = {"++": 0, "==": 0, "**": 0, "TIP": 0, "pull": 0}
    seen_para, i = False, 0

    def add(html_part: str, kind: str) -> None:
        parts.append(html_part)
        kinds.append(kind)

    while i < len(blocks):
        b = blocks[i].strip()
        nxt = blocks[i + 1].strip() if i + 1 < len(blocks) else ""
        i += 1
        if not b:
            continue
        if b.startswith("```"):
            while b.count("```") < 2 and i < len(blocks):
                b += "\n\n" + blocks[i]
                i += 1
            lines = b.split("\n")
            add(r.code_block(lines[1:-1], lines[0][3:].strip()), "code")
            continue
        if re.fullmatch(r"-{3,}", b):
            if nxt and not nxt.startswith("## "):
                add(r.divider(), "rule")
            continue
        if b.startswith("## "):
            add(r.h2(b[3:].strip()), "h2")
            continue
        if b.startswith("### "):
            add(r.h3(b[4:].strip()), "h3")
            continue
        img = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", b)
        if img:
            if img.group(1).strip() != "封面":
                add(r.image(img.group(2).strip(), img.group(1).strip()), "image")
            continue
        lines = b.split("\n")
        callout = re.match(r">\s*\[!([A-Z]+)\]\s*(.*)$", lines[0])
        if callout and all(ln.startswith(">") for ln in lines):
            kind, first = callout.group(1), callout.group(2).strip()
            items = ([first] if first else []) + [ln.lstrip(">").strip() for ln in lines[1:] if ln.lstrip(">").strip()]
            text = " ".join(items)
            pairs = [tuple(x.strip() for x in it.split("|", 1)) if "|" in it else (it, "") for it in items]
            builders = {
                "TIP": lambda: r.tip(text), "INTRO": lambda: r.intro(text),
                "TOC": lambda: r.toc([x.strip() for x in text.split("|")]),
                "DATA": lambda: r.data_cards(pairs), "TIMELINE": lambda: r.timeline(pairs),
                "PILLS": lambda: r.pills(pairs), "QUOTE": lambda: r.side_quote(text),
                "NOTE": lambda: r.note(text), "WARN": lambda: r.warn(text), "END": r.end_mark,
            }
            if kind not in builders:
                warnings.append(f"unknown callout [!{kind}], rendered as a quote card")
                add(r.quote(items), "quote")
            else:
                counts["TIP"] += kind == "TIP"
                # NOTE / WARN are light side notes, not boxes that compete for attention.
                add(builders[kind](), {"END": "end", "NOTE": "light", "WARN": "light"}.get(kind, "callout"))
            continue
        if len(lines) >= 3 and all(ln.startswith("|") for ln in lines) and re.fullmatch(r"\|[\s:|-]+\|", lines[1]):
            cells = [[c.strip() for c in ln.strip("|").split("|")] for ln in lines]
            add(r.table(cells[0], cells[2:]), "table")
            continue
        if all(ln.startswith(">") for ln in lines):
            q = [ln.lstrip(">").strip() for ln in lines if ln.lstrip(">").strip()]
            counts["pull"] += len(q) == 1 and "**" not in q[0]
            add(r.quote(q), "quote")
            continue
        if all(re.match(r"\d+\.\s", ln) for ln in lines):
            add(r.ordered([re.sub(r"^\d+\.\s+", "", ln) for ln in lines]), "list")
            continue
        if all(re.match(r"[-*]\s", ln) for ln in lines):
            items = [ln[2:].strip() for ln in lines]
            if sum(x.startswith("**") for x in items) > 2:
                warnings.append(f"bold label on most list items: {items[0][:20]}…")
            add(r.bullets(items), "list")
            continue
        text = " ".join(ln.strip() for ln in lines)
        n = text.count("++") // 2
        if n > 1:
            warnings.append(f"more than 1 underline in one paragraph: {text[:24]}…")
        for k in ("++", "==", "**"):
            counts[k] += text.count(k) // 2
        add(r.para(text, lead=not seen_para), "para")
        seen_para = True

    # Density standard (references/layout-standard.md).
    limits = {"++": (8, "underlines"), "==": (5, "highlights"), "**": (10, "bold phrases"),
              "TIP": (2, "tip bars"), "pull": (2, "pull quotes")}
    for k, (cap, label) in limits.items():
        if counts[k] > cap:
            warnings.append(f"{counts[k]} {label} (standard: at most {cap})")
    for a, b in zip(range(len(kinds)), range(1, len(kinds))):
        if kinds[a] in CONTAINERS and kinds[b] in CONTAINERS and "image" not in (kinds[a], kinds[b]):
            warnings.append(f"two containers back to back ({kinds[a]} + {kinds[b]}) near block {b}: add a sentence between")

    meta_cta = meta.get("cta")
    final_cta = cta if cta is not None else (meta_cta if meta_cta is not None else DEFAULT_CTA)
    if about or final_cta:
        parts.append(r.footer(final_cta, about))
    p = r.p
    out = (f'<section style="max-width:677px;margin:0 auto;padding:0 6px;background:#FFFFFF;'
           f'font-family:{FONT};color:{p["text"]};line-height:{p["lh"]};letter-spacing:{p["ls"]}px;">'
           + "".join(parts) + "</section>")
    return meta, out, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("markdown", type=Path)
    ap.add_argument("-o", "--out", type=Path, help="output .html (default: <markdown>.gzh.html)")
    ap.add_argument("--theme", choices=sorted(PALETTES), help="default: frontmatter theme, else latepost")
    ap.add_argument("--cta", help="footer call to action (default: frontmatter cta, else a generic line)")
    args = ap.parse_args()
    meta, out, warnings = render(args.markdown.read_text(encoding="utf-8"), args.theme, args.cta)
    dest = args.out or args.markdown.with_suffix(".gzh.html")
    dest.write_text(out, encoding="utf-8")
    print(f"title: {meta.get('title', '')}\nhtml: {dest}")
    for w in warnings:
        print(f"WARN {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

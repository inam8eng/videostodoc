#!/usr/bin/env python3
"""Give every article a unique banner in the site's flat-vector blue style.

Why generated, not hand-drawn in Gemini: Gemini makes lovely images but one at a
time through a browser, and doing 23 of them (plus regenerating when the brand
shifts) is slow and flaky. This draws the same visual language, deterministically
from each article's slug, so every article gets its OWN banner, they all match,
and re-running is one command. The three Gemini banners that already shipped use
the exact same motifs, so the set reads as one family.

Each banner is a left motif, a bold arrow, and a right motif, on the light
ground, chosen from what the article is actually about. A hash of the slug
nudges tile counts and a secondary accent so no two look identical even within
a topic.

Usage:
    py -3.12 tools/make_article_art.py            # write assets/art/<slug>.jpg for all
    py -3.12 tools/make_article_art.py --list     # print the slug -> motif plan
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "assets" / "art"
ARTICLES = ROOT / "articles"

W, H = 1280, 720

# The site palette, as literals so this runs without the stylesheet.
BG = (242, 245, 250)
INK = (15, 27, 45)
ACC = (11, 132, 227)
ACC_LT = (63, 169, 245)
ACC_WASH = (215, 235, 250)
SOFT = (120, 138, 165)
OK = (18, 133, 90)


def _font(size, mono=False):
    from PIL import ImageFont
    names = (["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf"] if mono
             else ["seguisb.ttf", "segoeui.ttf", "Arial.ttf", "DejaVuSans.ttf"])
    for n in names:
        for base in (Path("C:/Windows/Fonts"), Path("/System/Library/Fonts"),
                     Path("/usr/share/fonts/truetype/dejavu")):
            if (base / n).exists():
                try:
                    return ImageFont.truetype(str(base / n), size)
                except Exception:
                    pass
    return ImageFont.load_default()


# ------------------------------------------------------------------ primitives

def _rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def m_play(d, box, seed=0):
    """A video: rounded rect with a play triangle."""
    x0, y0, x1, y1 = box
    _rrect(d, box, 18, fill=(255, 255, 255), outline=INK, width=4)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s = min(x1 - x0, y1 - y0) * 0.20
    d.polygon([(cx - s * 0.7, cy - s), (cx - s * 0.7, cy + s), (cx + s, cy)], fill=ACC)


def m_stack(d, box, seed=0):
    """A channel: a vertical stack of small play tiles."""
    x0, y0, x1, y1 = box
    n = 4 + (seed % 2)
    gap = 14
    th = (y1 - y0 - gap * (n - 1)) / n
    tw = (x1 - x0) * 0.82
    for i in range(n):
        ty = y0 + i * (th + gap)
        m_play(d, (x0, ty, x0 + tw, ty + th))


def m_arrow(d, box):
    x0, y0, x1, y1 = box
    cy = (y0 + y1) / 2
    h = (y1 - y0) * 0.16
    d.rectangle([x0, cy - h / 2, x1 - h * 1.6, cy + h / 2], fill=ACC)
    d.polygon([(x1 - h * 2.2, cy - h * 1.5), (x1, cy), (x1 - h * 2.2, cy + h * 1.5)], fill=ACC)


def m_doc(d, box, seed=0, images=True):
    """A document page: title bar, text lines, and image thumbnails."""
    x0, y0, x1, y1 = box
    _rrect(d, box, 10, fill=(255, 255, 255), outline=INK, width=4)
    pad = (x1 - x0) * 0.10
    ln_w = x1 - x0 - pad * 2
    y = y0 + pad
    _rrect(d, (x0 + pad, y, x0 + pad + ln_w * 0.55, y + 16), 4, fill=INK)
    y += 42
    rows = seed % 3
    for i in range(6):
        if images and i in (2, 4 + rows % 2):
            iw = ln_w * 0.34
            _rrect(d, (x0 + pad, y, x0 + pad + iw, y + 46), 6, fill=ACC_WASH, outline=ACC_LT, width=2)
            d.line([x0 + pad + 8, y + 40, x0 + pad + iw * 0.4, y + 24, x0 + pad + iw - 8, y + 40], fill=ACC, width=3)
            _rrect(d, (x0 + pad + iw + 14, y + 6, x1 - pad, y + 14), 3, fill=SOFT)
            _rrect(d, (x0 + pad + iw + 14, y + 24, x1 - pad - ln_w * 0.1, y + 32), 3, fill=SOFT)
            y += 58
        else:
            fw = ln_w * (0.9 - (i % 3) * 0.15)
            _rrect(d, (x0 + pad, y, x0 + pad + fw, y + 12), 3, fill=SOFT)
            y += 26


def m_grid(d, box, seed=0):
    """Frames: a grid of image tiles."""
    x0, y0, x1, y1 = box
    cols = 4
    rows = 3 + (seed % 2)
    gap = 12
    tw = (x1 - x0 - gap * (cols - 1)) / cols
    th = (y1 - y0 - gap * (rows - 1)) / rows
    for r in range(rows):
        for c in range(cols):
            tx = x0 + c * (tw + gap)
            ty = y0 + r * (th + gap)
            _rrect(d, (tx, ty, tx + tw, ty + th), 5, fill=(255, 255, 255), outline=INK, width=2)
            d.line([tx + 6, ty + th - 6, tx + tw * 0.4, ty + th * 0.45, tx + tw - 6, ty + th - 6], fill=ACC, width=2)
            d.ellipse([tx + tw - 16, ty + 8, tx + tw - 8, ty + 16], fill=ACC_LT)


def m_wave(d, box, seed=0):
    """Audio waveform: vertical bars."""
    x0, y0, x1, y1 = box
    cy = (y0 + y1) / 2
    import math
    n = 13
    bw = (x1 - x0) / (n * 1.7)
    for i in range(n):
        bx = x0 + i * bw * 1.7
        amp = (y1 - y0) * 0.45 * (0.35 + 0.65 * abs(math.sin((i + seed) * 0.9)))
        col = ACC if i % 2 else ACC_LT
        _rrect(d, (bx, cy - amp, bx + bw, cy + amp), bw / 2, fill=col)


def m_lines(d, box, seed=0):
    """Transcript: neat horizontal text lines with tiny timestamps."""
    x0, y0, x1, y1 = box
    y = y0
    for i in range(7):
        _rrect(d, (x0, y + 2, x0 + 30, y + 12), 3, fill=ACC)  # timestamp
        _rrect(d, (x0 + 42, y, x1 - (x1 - x0) * (0.05 + (i % 3) * 0.12), y + 12), 3, fill=INK if i % 2 == 0 else SOFT)
        y += (y1 - y0) / 7


def m_chat(d, box, seed=0):
    """Ask an AI: a chat bubble with a sparkle."""
    x0, y0, x1, y1 = box
    _rrect(d, (x0, y0, x1, y1 - (y1 - y0) * 0.14), 22, fill=(255, 255, 255), outline=INK, width=4)
    d.polygon([(x0 + (x1 - x0) * 0.22, y1 - (y1 - y0) * 0.15),
               (x0 + (x1 - x0) * 0.34, y1 - (y1 - y0) * 0.15),
               (x0 + (x1 - x0) * 0.20, y1)], fill=(255, 255, 255), outline=INK)
    pad = (x1 - x0) * 0.16
    yy = y0 + pad
    for fw in (0.7, 0.9, 0.5):
        _rrect(d, (x0 + pad, yy, x0 + pad + (x1 - x0 - pad * 2) * fw, yy + 12), 3, fill=SOFT)
        yy += 30
    # sparkle
    sx, sy = x1 - pad * 0.7, y0 + pad * 0.7
    d.line([sx - 12, sy, sx + 12, sy], fill=ACC, width=4)
    d.line([sx, sy - 12, sx, sy + 12], fill=ACC, width=4)


def m_shield(d, box, seed=0):
    """Privacy: a shield with a play button inside."""
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    w = (x1 - x0) * 0.8
    top = y0
    pts = [(cx, top), (cx + w / 2, top + (y1 - y0) * 0.18),
           (cx + w / 2, top + (y1 - y0) * 0.55), (cx, y1),
           (cx - w / 2, top + (y1 - y0) * 0.55), (cx - w / 2, top + (y1 - y0) * 0.18)]
    d.polygon(pts, fill=(255, 255, 255), outline=INK)
    d.line(pts + [pts[0]], fill=INK, width=4, joint="curve")
    s = (y1 - y0) * 0.12
    ccy = (top + y1) / 2 - (y1 - y0) * 0.05
    d.polygon([(cx - s * 0.6, ccy - s), (cx - s * 0.6, ccy + s), (cx + s, ccy)], fill=ACC)


def m_code(d, box, seed=0):
    """Code: a window with </> and code lines."""
    x0, y0, x1, y1 = box
    _rrect(d, box, 10, fill=INK, width=0)
    pad = (x1 - x0) * 0.12
    y = y0 + pad
    for i, fw in enumerate((0.5, 0.75, 0.4, 0.68, 0.55)):
        ind = (x1 - x0) * 0.12 if i in (2, 3) else 0
        col = ACC_LT if i % 2 else (120, 200, 255)
        _rrect(d, (x0 + pad + ind, y, x0 + pad + ind + (x1 - x0 - pad * 2) * fw, y + 12), 3, fill=col)
        y += (y1 - y0 - pad * 2) / 5


def m_cap(d, box, seed=0):
    """Study: a graduation cap over a page."""
    x0, y0, x1, y1 = box
    m_doc(d, (x0, y0 + (y1 - y0) * 0.28, x1, y1), seed, images=False)
    cx = (x0 + x1) / 2
    capw = (x1 - x0) * 0.6
    cy = y0 + (y1 - y0) * 0.12
    d.polygon([(cx, cy - 20), (cx + capw / 2, cy), (cx, cy + 20), (cx - capw / 2, cy)], fill=ACC)
    d.line([cx + capw * 0.42, cy + 6, cx + capw * 0.42, cy + 40], fill=ACC, width=4)
    d.ellipse([cx + capw * 0.42 - 6, cy + 38, cx + capw * 0.42 + 6, cy + 50], fill=ACC_LT)


def m_download(d, box, seed=0):
    """Download: a cloud with a down arrow (the video file itself)."""
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    m_play(d, (x0, y0, x1, y0 + (y1 - y0) * 0.5))
    ax = cx
    ay0 = y0 + (y1 - y0) * 0.58
    ay1 = y1 - 6
    d.line([ax, ay0, ax, ay1 - 18], fill=ACC, width=8)
    d.polygon([(ax - 22, ay1 - 30), (ax + 22, ay1 - 30), (ax, ay1)], fill=ACC)


def m_numdoc(d, box, seed=0):
    """SOP / blog: a document with numbered steps."""
    x0, y0, x1, y1 = box
    _rrect(d, box, 10, fill=(255, 255, 255), outline=INK, width=4)
    pad = (x1 - x0) * 0.12
    y = y0 + pad
    for i in range(4):
        r = 13
        d.ellipse([x0 + pad, y, x0 + pad + r * 2, y + r * 2], fill=ACC)
        _rrect(d, (x0 + pad + r * 2 + 14, y + 3, x1 - pad * (1 + (i % 3) * 0.4), y + 14), 3, fill=SOFT)
        _rrect(d, (x0 + pad + r * 2 + 14, y + 22, x1 - pad * (1.4 + (i % 2) * 0.5), y + 30), 3, fill=SOFT)
        y += (y1 - y0 - pad * 2) / 4


MOTIFS = {
    "play": m_play, "stack": m_stack, "doc": m_doc, "grid": m_grid,
    "wave": m_wave, "lines": m_lines, "chat": m_chat, "shield": m_shield,
    "code": m_code, "cap": m_cap, "download": m_download, "numdoc": m_numdoc,
}


def plan_for(slug: str):
    """(left motif, right motif) for an article, by what it is about."""
    s = slug
    def has(*ks): return any(k in s for k in ks)
    if has("get-transcript", "-to-text", "transcribe", "text-converters", "mp4-to-text"):
        return "wave", "lines"
    if has("summarize", "feed-video-to-chatgpt", "chatgpt-or-claude", "why-chatgpt", "vs-transcription", "give-claude", "feed-a-long"):
        return "doc", "chat"
    if has("study", "lecture", "course", "notes", "cite-a-video", "conference-talk"):
        return "play", "cap"
    if has("blog", "sop"):
        return "play", "numdoc"
    if has("code"):
        return "play", "code"
    if has("frame", "images-only", "slides", "deduplicate", "csv-index", "gta-6", "how-many-frames"):
        return "play", "grid"
    if has("channel", "playlist", "batch", "webinar", "meeting"):
        return "stack", "doc"
    if has("download", "vimeo"):
        return "play", "download"
    if has("privacy", "local", "is-it-safe", "upload", "offline", "no-upload"):
        return "play", "shield"
    return "play", "doc"


def render(slug: str, out: Path):
    from PIL import Image, ImageDraw
    seed = int(hashlib.sha1(slug.encode()).hexdigest(), 16)
    left, right = plan_for(slug)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # subtle centred glow
    glow = Image.new("RGB", (W, H), BG)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W * 0.2, H * 0.05, W * 0.8, H * 0.95], fill=(232, 242, 251))
    img = Image.blend(img, glow, 0.5)
    d = ImageDraw.Draw(img)

    # three columns: left motif | arrow | right motif
    lw = W * 0.30
    box_l = (W * 0.08, H * 0.20, W * 0.08 + lw, H * 0.80)
    box_a = (W * 0.44, H * 0.42, W * 0.56, H * 0.58)
    box_r = (W * 0.62, H * 0.16, W * 0.92, H * 0.84)
    MOTIFS[left](d, box_l, seed)
    m_arrow(d, box_a)
    MOTIFS[right](d, box_r, seed >> 7)

    img.save(out, "JPEG", quality=84, optimize=True, progressive=True)
    return left, right


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    ART.mkdir(parents=True, exist_ok=True)
    slugs = sorted(d.name for d in ARTICLES.iterdir()
                   if d.is_dir() and (d / "index.html").exists())
    if args.list:
        for s in slugs:
            print(f"  {s:44} {plan_for(s)}")
        return 0
    for s in slugs:
        l, r = render(s, ART / f"{s}.jpg")
        kb = (ART / f"{s}.jpg").stat().st_size / 1024
        print(f"  {s:44} {l:>7} -> {r:<8} {kb:.0f} KB")
    print(f"\n{len(slugs)} unique article banners written to assets/art/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

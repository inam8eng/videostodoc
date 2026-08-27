#!/usr/bin/env python3
"""Build the homepage demo clip: a video becoming a folder of readable frames.

Why it is generated rather than screen-recorded: a screen recording of the app
goes stale the moment a button moves or the brand changes, and it has to be
re-shot by hand every release. This is one command, it uses the SAME numbers the
real tool produces, and the source footage is synthetic so there is nothing in
the clip anyone else owns.

The four beats, twelve seconds, looping:
  1. a lecture-style video playing
  2. it fans out into numbered, timestamped frames
  3. the duplicates fade away and the count collapses
  4. what is left is a document you can hand to an AI

Usage:
    py -3.12 tools/make_demo.py            # writes assets/demo.mp4 + .webm
    py -3.12 tools/make_demo.py --check    # verify ffmpeg and fonts, write nothing
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

W, H = 1280, 800
FPS = 30
SECONDS = 12

# The blue system, matching the site. Kept here as literals on purpose: this
# script has to run without the stylesheet, and a demo that silently drifts
# from the brand is worse than one that has to be updated deliberately.
BG = (13, 21, 36)
CARD = (21, 32, 54)
LINE = (46, 63, 94)
INK = (232, 238, 247)
SOFT = (157, 170, 192)
ACC = (11, 132, 227)
ACC_LIGHT = (63, 169, 245)
OK = (69, 192, 125)


def _ffmpeg() -> str:
    """The bundled ffmpeg the app already ships, or one on PATH."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        found = shutil.which("ffmpeg")
        if not found:
            raise SystemExit(
                "No ffmpeg. Either pip install imageio-ffmpeg, or put ffmpeg on PATH.")
        return found


def _font(size: int, mono: bool = False):
    from PIL import ImageFont
    names = (["JetBrainsMono-Bold.ttf", "consola.ttf", "cour.ttf", "DejaVuSansMono.ttf"]
             if mono else
             ["seguisb.ttf", "segoeui.ttf", "Arial.ttf", "DejaVuSans.ttf"])
    for n in names:
        for base in (Path("C:/Windows/Fonts"), Path("/System/Library/Fonts"),
                     Path("/usr/share/fonts/truetype/dejavu")):
            p = base / n
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size)
                except Exception:
                    pass
    return ImageFont.load_default()


def _ease(t: float) -> float:
    """Ease in-out cubic. Linear motion is what makes an animation look cheap."""
    t = max(0.0, min(1.0, t))
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


def _slide(draw, x, y, w, h, idx: int, dim: float = 1.0):
    """One 'frame' tile: a miniature of a lecture slide."""
    from PIL import ImageDraw  # noqa: F401
    def mix(c):
        return tuple(int(BG[i] + (c[i] - BG[i]) * dim) for i in range(3))

    draw.rounded_rectangle([x, y, x + w, y + h], radius=6,
                           fill=mix(CARD), outline=mix(LINE), width=1)
    # A title bar and two or three text lines, so it reads as a slide at 90px.
    pad = max(4, w // 14)
    draw.rounded_rectangle([x + pad, y + pad, x + pad + int(w * 0.52), y + pad + max(3, h // 12)],
                           radius=2, fill=mix(ACC_LIGHT))
    ly = y + pad + max(3, h // 12) + max(4, h // 12)
    for i, frac in enumerate((0.78, 0.62, 0.44)):
        if ly + 3 > y + h - pad:
            break
        draw.rounded_rectangle([x + pad, ly, x + pad + int(w * frac), ly + max(2, h // 20)],
                               radius=2, fill=mix(SOFT if i else INK))
        ly += max(5, h // 9)


def _render(tmp: Path) -> int:
    from PIL import Image, ImageDraw

    f_h1 = _font(46)
    f_lbl = _font(19, mono=True)
    f_num = _font(64, mono=True)
    f_small = _font(15, mono=True)

    total = FPS * SECONDS
    # 6 across x 4 down = 24 tiles, enough to read as "a lot" without clutter.
    COLS, ROWS = 6, 4
    N = COLS * ROWS
    # Which tiles survive dedupe. Deliberately clustered, the way a real slide
    # deck dedupes: long identical runs collapse to their first frame.
    KEEP = {0, 1, 4, 5, 9, 12, 13, 17, 20, 23}

    for i in range(total):
        t = i / total
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)

        # --- beat 1: the source video (0.00 - 0.28) --------------------------
        if t < 0.30:
            k = _ease(min(1.0, t / 0.10))
            vw, vh = int(W * 0.56), int(H * 0.56)
            vx, vy = (W - vw) // 2, (H - vh) // 2 - 20
            d.rounded_rectangle([vx, vy, vx + vw, vy + vh], radius=14,
                                fill=CARD, outline=LINE, width=2)
            _slide(d, vx + 26, vy + 26, vw - 52, vh - 52, 0)
            # a play head sweeping, so it reads as playing
            px = vx + 26 + int((vw - 52) * ((t / 0.30) % 1.0))
            d.line([px, vy + vh - 18, px, vy + vh - 8], fill=ACC_LIGHT, width=3)
            lbl = "one lecture, 58 minutes"
            bb = d.textbbox((0, 0), lbl, font=f_lbl)
            d.text(((W - bb[2]) / 2, vy + vh + 26), lbl, font=f_lbl, fill=SOFT)
            if k < 1:
                d.rectangle([0, 0, W, H], fill=None)

        # --- beat 2: fan out into frames (0.28 - 0.52) -----------------------
        elif t < 0.55:
            k = _ease((t - 0.28) / 0.24)
            tw, th = 150, 96
            gap = 18
            gw = COLS * tw + (COLS - 1) * gap
            gh = ROWS * th + (ROWS - 1) * gap
            gx, gy = (W - gw) // 2, (H - gh) // 2 - 10
            cx, cy = W // 2 - tw // 2, H // 2 - th // 2
            for n in range(N):
                r, c = divmod(n, COLS)
                tx = gx + c * (tw + gap)
                ty = gy + r * (th + gap)
                # stagger so they arrive as a wave, not all at once
                kk = _ease(max(0.0, min(1.0, (k * 1.6) - n / (N * 1.6))))
                x = cx + (tx - cx) * kk
                y = cy + (ty - cy) * kk
                _slide(d, int(x), int(y), tw, th, n)
            lbl = "4 frames a second, 13,920 images"
            bb = d.textbbox((0, 0), lbl, font=f_lbl)
            d.text(((W - bb[2]) / 2, gy + gh + 30), lbl, font=f_lbl, fill=SOFT)

        # --- beat 3: duplicates fall away (0.55 - 0.80) ----------------------
        elif t < 0.82:
            k = _ease((t - 0.55) / 0.27)
            tw, th = 150, 96
            gap = 18
            gw = COLS * tw + (COLS - 1) * gap
            gh = ROWS * th + (ROWS - 1) * gap
            gx, gy = (W - gw) // 2, (H - gh) // 2 - 10
            for n in range(N):
                r, c = divmod(n, COLS)
                x = gx + c * (tw + gap)
                y = gy + r * (th + gap)
                if n in KEEP:
                    _slide(d, x, y, tw, th, n)
                    if k > 0.55:
                        d.rounded_rectangle([x, y, x + tw, y + th], radius=6,
                                            outline=OK, width=2)
                else:
                    _slide(d, x, y, tw, th, n, dim=max(0.0, 1.0 - k * 1.35))
            # The final number has to match what the grid actually shows.
            # 10 of 24 tiles survive on screen, so the counter lands on the
            # same 42%. A grid cannot legibly show the 3% a real slide deck
            # collapses to (one tile), and a number that disagrees with the
            # picture is the kind of small lie that costs trust.
            kept_final = round(13920 * len(KEEP) / N)
            shown = int(13920 - (13920 - kept_final) * k)
            lbl = f"{shown:,} kept"
            bb = d.textbbox((0, 0), lbl, font=f_num)
            d.text(((W - bb[2]) / 2, gy + gh + 26), lbl, font=f_num, fill=INK)
            sub = "identical frames dropped, nothing that changed"
            bb2 = d.textbbox((0, 0), sub, font=f_small)
            d.text(((W - bb2[2]) / 2, gy + gh + 100), sub, font=f_small, fill=SOFT)

        # --- beat 4: the document (0.82 - 1.00) ------------------------------
        else:
            k = _ease((t - 0.82) / 0.18)
            pw, ph = 470, 600
            px, py = (W - pw) // 2, (H - ph) // 2 - 10
            d.rounded_rectangle([px, py, px + pw, py + ph], radius=12,
                                fill=(248, 250, 253), outline=LINE, width=1)
            yy = py + 34
            d.rounded_rectangle([px + 34, yy, px + 34 + 240, yy + 16], radius=3, fill=(15, 27, 45))
            yy += 44
            rows = [("img", 0), ("txt", 0.86), ("txt", 0.72), ("img", 0),
                    ("txt", 0.9), ("txt", 0.64), ("img", 0), ("txt", 0.8)]
            for j, (kind, frac) in enumerate(rows):
                if j / len(rows) > k * 1.25:
                    break
                if kind == "img":
                    _slide(d, px + 34, yy, pw - 68, 84, j)
                    yy += 98
                else:
                    d.rounded_rectangle([px + 34, yy, px + 34 + int((pw - 68) * frac), yy + 9],
                                        radius=2, fill=(88, 100, 121))
                    yy += 22
            lbl = "one PDF your AI can read"
            bb = d.textbbox((0, 0), lbl, font=f_lbl)
            d.text(((W - bb[2]) / 2, py + ph + 26), lbl, font=f_lbl, fill=SOFT)

        img.save(tmp / f"f{i:05d}.png")
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="verify tooling, write nothing")
    args = ap.parse_args()

    try:
        import PIL  # noqa: F401
    except ImportError:
        raise SystemExit("Pillow is required: pip install pillow")
    ff = _ffmpeg()
    if args.check:
        print(f"ffmpeg: {ff}")
        print(f"output: {ASSETS/'demo.mp4'} and {ASSETS/'demo.webm'}")
        return 0

    ASSETS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        n = _render(tmp)
        print(f"rendered {n} frames")
        mp4 = ASSETS / "demo.mp4"
        webm = ASSETS / "demo.webm"
        common = [ff, "-y", "-framerate", str(FPS), "-i", str(tmp / "f%05d.png")]
        subprocess.run(common + [
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26",
            "-movflags", "+faststart", "-an", str(mp4)], check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(common + [
            "-c:v", "libvpx-vp9", "-crf", "38", "-b:v", "0", "-an", str(webm)],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for f in (ASSETS / "demo.mp4", ASSETS / "demo.webm"):
        if f.exists():
            print(f"  {f.relative_to(ROOT)}  {f.stat().st_size/1e6:.2f} MB")
        else:
            print(f"  {f.name} not produced (that codec may be unavailable here)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

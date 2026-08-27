"""Generate the 1200x630 social-share image (og.png) on the Designesh
"Node x Matrix" brand: light page, faint dot-matrix field, one orange eye
mark, JetBrains Mono display + IBM Plex Sans body. Matches the live site hero.
Run:  python make_og.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = 2
W, H = 1200 * S, 630 * S
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent                      # project root
FONTS = ROOT / "videodoc" / "web" / "fonts"    # bundled brand fonts

# --- brand tokens ---
PAGE    = (244, 245, 247)   # --page
INK     = (26, 37, 49)      # --ink
SLATE   = (86, 97, 110)     # --slate-soft
MUTE    = (138, 149, 161)   # --slate-muted
ORANGE  = (255, 106, 44)    # --orange
ORANGE2 = (255, 135, 70)    # --orange-light
DOT     = (26, 37, 49)      # dot-field base (drawn at low alpha)
WHITE   = (255, 255, 255)


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size * S)


DISP  = lambda s: font("JetBrainsMono-ExtraBold.ttf", s)   # wordmark
DISPB = lambda s: font("JetBrainsMono-Bold.ttf", s)        # headline
BODY  = lambda s: font("IBMPlexSans-400.ttf", s)
BODYM = lambda s: font("IBMPlexSans-500.ttf", s)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def cubic(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n
        m = 1 - t
        x = m**3*p0[0] + 3*m*m*t*p1[0] + 3*m*t*t*p2[0] + t**3*p3[0]
        y = m**3*p0[1] + 3*m*m*t*p1[1] + 3*m*t*t*p2[1] + t**3*p3[1]
        out.append((x, y))
    return out


def grad_text(base, xy, text, fnt, c0=ORANGE, c1=ORANGE2):
    """Draw text filled with a horizontal orange gradient."""
    tmp = Image.new("RGBA", base.size, (0, 0, 0, 0))
    dd = ImageDraw.Draw(tmp)
    dd.text(xy, text, font=fnt, fill=WHITE)
    bbox = dd.textbbox(xy, text, font=fnt)
    grad = Image.new("RGBA", base.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    x0, x1 = int(bbox[0]), int(bbox[2])
    for x in range(x0, x1):
        gd.line([(x, bbox[1]), (x, bbox[3])], fill=lerp(c0, c1, (x - x0) / max(1, x1 - x0)))
    grad.putalpha(tmp.split()[3])
    base.alpha_composite(grad)


def mark(base, x, y, size):
    """Orange rounded tile + white eye outline + white pupil (the brand mark)."""
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    td.rounded_rectangle([0, 0, size - 1, size - 1], radius=round(size * 0.26), fill=ORANGE + (255,))
    s = size / 64.0
    outline = cubic((12*s, 32*s), (20*s, 20*s), (44*s, 20*s), (52*s, 32*s)) \
        + cubic((52*s, 32*s), (44*s, 44*s), (20*s, 44*s), (12*s, 32*s))
    td.line(outline, fill=WHITE, width=max(1, round(3.4 * s)), joint="curve")
    r = 6.5 * s
    td.ellipse([32*s - r, 32*s - r, 32*s + r, 32*s + r], fill=WHITE)
    base.alpha_composite(tile, (round(x), round(y)))


img = Image.new("RGBA", (W, H), PAGE + (255,))
d = ImageDraw.Draw(img)

# faint dot-matrix field (kept out of the text block so copy stays crisp)
gap, dr = 22 * S, 1.4 * S
pad = 84 * S
clear = (int(pad - 24 * S), int(pad + 118 * S), int(W * 0.66), int(pad + 402 * S))
for yy in range(gap, H, gap):
    for xx in range(gap, W, gap):
        if clear[0] <= xx <= clear[2] and clear[1] <= yy <= clear[3]:
            continue
        d.ellipse([xx - dr, yy - dr, xx + dr, yy + dr], fill=DOT + (20,))

# soft orange glow, top-right corner
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(glow).ellipse([W*0.55, -H*0.5, W*1.15, H*0.55], fill=ORANGE + (55,))
img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(150 * S)))

d = ImageDraw.Draw(img)
pad = 84 * S

# wordmark lockup
mark(img, pad, pad, 46 * S)
d = ImageDraw.Draw(img)
d.text((pad + 62 * S, pad + 9 * S), "VideoDoc", font=DISP(26), fill=INK)

# headline
hy = pad + 152 * S
d.text((pad, hy), "Give your AI ", font=DISPB(60), fill=INK)
w = d.textlength("Give your AI ", font=DISPB(60))
grad_text(img, (pad + w, hy), "eyes", DISPB(60))
d = ImageDraw.Draw(img)
d.text((pad, hy + 82 * S), "for any video.", font=DISPB(60), fill=INK)

# subline
d.text((pad, hy + 182 * S),
       "One document. A timestamped transcript with the on-screen",
       font=BODY(22), fill=SLATE)
d.text((pad, hy + 216 * S),
       "content as images, so ChatGPT or Claude can read the whole video.",
       font=BODY(22), fill=SLATE)

# Try-free pill + address line
py = H - pad - 56 * S
pill_w = 188 * S
d.rounded_rectangle([pad, py, pad + pill_w, py + 56 * S], radius=28 * S, fill=ORANGE + (255,))
d.text((pad + 34 * S, py + 15 * S), "Try free  →", font=DISPB(20), fill=WHITE)
d.text((pad + pill_w + 30 * S, py + 17 * S), "videostodoc.com  ·  by Inam Ul Haq",
       font=BODYM(17), fill=MUTE)

img.convert("RGB").resize((1200, 630), Image.LANCZOS).save(HERE / "og.png", "PNG")
print("wrote", HERE / "og.png")

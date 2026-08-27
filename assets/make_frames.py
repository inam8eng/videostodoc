"""Generate two legible 'captured from the video' frames for the site:
  slide-frame.jpg  — a clean lecture slide (title + steps + a flow diagram)
  code-frame.jpg   — a VS Code-style editor with readable code
These prove the product claim ('captures the on-screen content'). Own content, no rights issue.
Run:  python make_frames.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

S = 2
W, H = 1200 * S, 675 * S
HERE = Path(__file__).resolve().parent


def f(name, size):
    return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size * S)


def rr(d, box, r, **kw):
    d.rounded_rectangle([box[0]*S, box[1]*S, box[2]*S, box[3]*S], radius=r*S, **kw)


# ---------- slide-frame ----------
img = Image.new("RGB", (W, H), (243, 244, 248))
d = ImageDraw.Draw(img)
# left accent rail
d.rectangle([0, 0, 12*S, H], fill=(124, 92, 255))
# eyebrow + title
d.text((72*S, 70*S), "LECTURE · 12", font=f("segoeuib.ttf", 15), fill=(140, 120, 210))
d.text((70*S, 104*S), "Deploy a full-stack app, free", font=f("segoeuib.ttf", 46), fill=(24, 24, 40))
# steps
steps = ["Build with Next.js and Supabase", "Push the repo to GitHub",
         "Deploy on Vercel in one click"]
y = 210
for i, s in enumerate(steps, 1):
    d.ellipse([72*S, y*S, (72+30)*S, (y+30)*S], fill=(124, 92, 255))
    d.text((80*S, (y+4)*S), str(i), font=f("segoeuib.ttf", 17), fill=(255, 255, 255))
    d.text((118*S, (y+2)*S), s, font=f("segoeui.ttf", 24), fill=(60, 60, 82))
    y += 56
# flow diagram
bx, by, bw, bh, gap = 72, 430, 200, 92, 70
labels = ["Code", "Build", "Live"]
for i, lab in enumerate(labels):
    x = bx + i * (bw + gap)
    rr(d, (x, by, x + bw, by + bh), 14, fill=(255, 255, 255), outline=(220, 222, 232), width=2*S)
    tw = d.textlength(lab, font=f("segoeuib.ttf", 22))
    d.text(((x + bw/2)*S - tw/2, (by + bh/2 - 16)*S), lab, font=f("segoeuib.ttf", 22), fill=(40, 40, 60))
    if i < 2:
        ax = x + bw + 12
        d.line([ax*S, (by+bh/2)*S, (ax+gap-24)*S, (by+bh/2)*S], fill=(124, 92, 255), width=4*S)
        d.polygon([((ax+gap-24)*S, (by+bh/2-7)*S), ((ax+gap-24)*S, (by+bh/2+7)*S), ((ax+gap-10)*S, (by+bh/2)*S)], fill=(124, 92, 255))
img.resize((1200, 675), Image.LANCZOS).save(HERE / "slide-frame.jpg", "JPEG", quality=88)
print("wrote slide-frame.jpg")

# ---------- code-frame ----------
BG = (13, 17, 23)
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
# title bar + tab
d.rectangle([0, 0, W, 44*S], fill=(22, 27, 34))
for i, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
    d.ellipse([(20+i*22)*S, 15*S, (20+i*22+13)*S, 28*S], fill=c)
rr(d, (110, 8, 240, 44), 6, fill=(13, 17, 23))
d.text((124*S, 15*S), "server.py", font=f("consola.ttf", 15), fill=(180, 190, 205))
# code
KW, STR, COM, FN, VAR, TXT = (198, 120, 221), (152, 195, 121), (95, 106, 120), (224, 176, 90), (86, 182, 240), (200, 208, 218)
mono = f("consola.ttf", 19)
lines = [
    [("from ", KW), ("fastapi ", TXT), ("import ", KW), ("FastAPI", FN)],
    [("app ", VAR), ("= ", TXT), ("FastAPI()", FN)],
    [],
    [("# transcribe on the user's own machine", COM)],
    [("def ", KW), ("build_document", FN), ("(video):", TXT)],
    [("    audio  ", VAR), ("= ", TXT), ("extract_audio", FN), ("(video)", TXT)],
    [("    text   ", VAR), ("= ", TXT), ("whisper", FN), ("(audio)", TXT)],
    [("    frames ", VAR), ("= ", TXT), ("keyframes", FN), ("(video)  ", TXT), ("# content-aware", COM)],
    [("    return ", KW), ("assemble", FN), ("(text, frames)", TXT)],
]
y = 74
for i, parts in enumerate(lines, 1):
    d.text((28*S, y*S), str(i).rjust(2), font=mono, fill=(70, 80, 95))
    x = 78
    for txt, col in parts:
        d.text((x*S, y*S), txt, font=mono, fill=col)
        x += d.textlength(txt, font=mono) / S
    y += 34
img.resize((1200, 675), Image.LANCZOS).save(HERE / "code-frame.jpg", "JPEG", quality=90)
print("wrote code-frame.jpg")

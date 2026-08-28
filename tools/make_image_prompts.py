#!/usr/bin/env python3
"""Write one file of Gemini image prompts for every article: a main banner
prompt plus a prompt for each section (step) inside the article.

Why this exists: driving Gemini's browser UI to generate 100+ images is slow and
flaky. This reads the real articles, and for each one writes a ready-to-paste
prompt for the hero image and for every H2 section, all sharing the site's exact
visual style so whatever you generate matches. Paste them into Gemini one by
one, download, and drop them in assets/art/.

Usage:
    py -3.12 tools/make_image_prompts.py        # writes tools/ARTICLE_IMAGE_PROMPTS.md
"""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
OUT = ROOT / "tools" / "ARTICLE_IMAGE_PROMPTS.md"

STYLE = ("Flat vector illustration, wide 16:9 banner, clean and minimal with "
         "lots of whitespace. Strict palette: blue #0B84E3 as the only accent, "
         "dark navy #0F1B2D for line work, on a very light #F2F5FA background. "
         "No text, letters or numbers anywhere in the image.")

STEP_STYLE = ("Flat vector spot illustration, square-ish, simple and iconic, "
              "generous whitespace. Same palette: blue #0B84E3 accent, navy "
              "#0F1B2D lines, light #F2F5FA background. No text or letters.")

# The main-banner concept per article, reusing the same motif plan the local
# art generator uses, so a Gemini redraw lands in the same visual family.
MOTIF = {
    "play": "a video player card with a blue play button",
    "stack": "a vertical stack of several small video thumbnails (a whole channel)",
    "doc": "a document page showing a few lines of text and two small embedded image thumbnails",
    "grid": "a neat 4-by-3 grid of small identical image frames",
    "wave": "an audio waveform of blue bars",
    "lines": "neat horizontal lines of transcript text, each with a tiny blue timestamp tag",
    "chat": "an AI chat bubble with a small sparkle",
    "shield": "a shield outline with a play button inside it",
    "code": "a dark code-editor window with a few lines of colourful code",
    "cap": "a graduation cap resting on top of a document page",
    "download": "a video thumbnail with a bold downward download arrow",
    "numdoc": "a document page with numbered step markers down the side",
}


def plan_for(slug: str):
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


def step_visual(heading: str, fallback: str) -> str:
    """A concrete little scene for a section heading, by its keywords.

    When nothing matches, fall back to the article's own concept rather than a
    vague 'represent this idea', so even a narrative heading gets an on-topic,
    drawable image.
    """
    h = heading.lower()
    rules = [
        (("free", "cost", "price", "trick"), "a price tag showing a zero, or an open padlock, to signal free"),
        (("duplicate", "dedupe", "identical"), "two identical image frames side by side with one marked to be removed"),
        (("face", "webcam", "blur", "black out", "privacy", "redact"), "a webcam bubble in the corner of a slide, covered by a solid rounded shape"),
        (("download", "4k", "hd", "quality"), "a video thumbnail with a downward download arrow"),
        (("frame", "every frame", "images", "slides", "screenshot", "capture"), "a video on the left and a grid of extracted image frames on the right"),
        (("transcript", "text", "words", "caption", "subtitle"), "an audio waveform turning into horizontal lines of text"),
        (("playlist", "channel", "batch", "folder", "course", "many"), "several video thumbnails merging into one tall document"),
        (("pdf", "document", "export", "file"), "a clean document page with text and small image thumbnails"),
        (("summarise", "summary", "chatgpt", "claude", "ai", "ask", "feed"), "a document flowing into an AI chat bubble with a sparkle"),
        (("note", "study", "learn", "revise", "lecture"), "a document with a highlighter mark and a graduation cap"),
        (("code", "snippet", "editor", "programming"), "a code-editor window with a few lines of colourful code"),
        (("step", "how", "process", "workflow", "sop"), "three simple numbered circles connected by arrows, left to right"),
        (("index", "csv", "timestamp", "spreadsheet", "search"), "a spreadsheet grid with a magnifier over one row"),
        (("limit", "honest", "warning", "careful"), "a simple caution triangle beside a document"),
        (("private", "local", "offline", "upload", "cloud", "safe"), "a laptop with a shield, a crossed-out cloud beside it"),
        (("language", "translate", "urdu", "hindi"), "a speech bubble with a small globe"),
        (("slow", "fast", "speed", "gpu", "power"), "a small speed gauge or a lightning bolt on a chip"),
    ]
    for keys, scene in rules:
        if any(k in h for k in keys):
            return scene
    return fallback


def extract(idx: Path):
    raw = idx.read_text(encoding="utf-8")
    h1 = re.search(r"<h1>(.*?)</h1>", raw, re.S)
    headline = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1)).strip()) if h1 else idx.parent.name
    h2s = []
    for m in re.finditer(r'<h2[^>]*>(.*?)</h2>', raw, re.S):
        t = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip())
        if t and t.lower() not in ("quick questions",):
            h2s.append(t)
    return headline, h2s


def main() -> int:
    slugs = sorted(d.name for d in ARTICLES.iterdir()
                   if d.is_dir() and (d / "index.html").exists())
    out = []
    out.append("# VideoDoc article image prompts\n")
    out.append("One main banner prompt per article, then a prompt for each "
               "section inside it. Paste each into Gemini, download the image, "
               "and save it where the filename says.\n")
    out.append("Every prompt already carries the site's style and palette, so "
               "the images come out matching. The main banner for an article "
               "should be saved as `assets/art/<slug>.jpg` to replace the "
               "auto-drawn one; step images can go in "
               "`assets/art/<slug>-step-1.jpg`, `-step-2.jpg`, and so on.\n")
    out.append("---\n")

    for slug in slugs:
        headline, h2s = extract(ARTICLES / slug / "index.html")
        left, right = plan_for(slug)
        out.append(f"## {headline}\n")
        out.append(f"`{slug}`\n")
        out.append("**Main banner** &rarr; save as `assets/art/%s.jpg`\n" % slug)
        out.append("> " + STYLE + " On the left, " + MOTIF[left] +
                   ". A bold blue arrow pointing right. On the right, " +
                   MOTIF[right] + ".\n")
        if h2s:
            out.append("**Section images**\n")
        default_scene = MOTIF[right]
        for i, h in enumerate(h2s, 1):
            scene = step_visual(h, default_scene)
            out.append(f"{i}. *{h}* &rarr; save as `assets/art/{slug}-step-{i}.jpg`\n")
            out.append(f'   > {STEP_STYLE} A small icon-style illustration for '
                       f'a section about "{h}". Show {scene}.\n')
        out.append("---\n")

    OUT.write_text("\n".join(out), encoding="utf-8", newline="\n")
    n_steps = sum(len(extract(ARTICLES / s / "index.html")[1]) for s in slugs)
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  {len(slugs)} articles, {len(slugs)} main prompts, {n_steps} section prompts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Publish one article onto videostodoc.com from a JSON spec.

Why this exists: the article program runs unattended, one post a day. Letting an
agent hand-write 250 lines of HTML every night is how a site slowly rots - a
missing canonical here, a malformed JSON-LD blob there, a card that never made
it into the hub. So the agent writes *prose only*, as JSON, and this script owns
every structural decision: the template, the three schema blobs, the hub card,
the sitemap entry, the internal links both ways.

Everything is checked before anything is written. If a single validation fails
the run aborts having touched nothing, so a bad night leaves the live site
exactly as it was.

Usage:
    python tools/new_article.py path/to/spec.json          # publish
    python tools/new_article.py path/to/spec.json --check   # validate only
    python tools/new_article.py --verify-site               # audit what is live
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
TEMPLATE = Path(__file__).resolve().parent / "article_template.html"
SITEMAP = ROOT / "sitemap.xml"
HUB = ARTICLES / "index.html"
SITE = "https://videostodoc.com"

# The hub is grouped into four themed sections, in document order. A new article
# declares which one it belongs to; anything else is a spec error rather than a
# silent append to the bottom.
HUB_SECTIONS = ["start", "study", "work", "privacy"]

CATEGORIES = {"Guide", "Work", "Study", "Privacy", "Compare"}

# Body block types the spec may use. Anything else aborts the run - an unknown
# block would otherwise vanish from the page without a word.
BLOCK_TYPES = {"h2", "p", "ul", "ol", "callout", "cta", "steps"}

MAX_TITLE = 60
MAX_DESC = 160


# ---------------------------------------------------------------- helpers


def esc(text: str) -> str:
    """Escape for HTML text nodes, but keep the inline tags we allow."""
    return html.escape(text, quote=False)


def inline(text: str) -> str:
    """Allow a tiny inline vocabulary inside prose: **bold**, `code`, [x](url).

    Everything else is escaped. This is deliberately small: the daily agent
    should be writing sentences, not markup.
    """
    out = esc(text)
    out = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return out


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def human_date(iso: str) -> str:
    y, m, d = (int(p) for p in iso.split("-"))
    months = ("January February March April May June July August "
              "September October November December").split()
    return f"{months[m - 1]} {d}, {y}"


def read_minutes(spec: dict) -> int:
    """Word count over 200 wpm, floored at 4 and capped at 12.

    The existing articles all read 5-7 minutes; a number wildly outside that
    band means the draft is either thin or bloated, and the caller sees it in
    the metadata rather than discovering it in Search Console.
    """
    words = len(spec["short_answer"].split()) + len(spec.get("closer", "").split())
    for b in spec["body"]:
        if b["type"] in ("p", "h2"):
            words += len(b["text"].split())
        elif b["type"] in ("ul", "ol", "steps"):
            words += sum(len(i.split()) for i in b["items"])
        elif b["type"] == "callout":
            words += len(b["text"].split())
        elif b["type"] == "cta":
            words += len(b.get("text", "").split())
    for q in spec["faq"]:
        words += len(q["q"].split()) + len(q["a"].split())
    return max(4, min(12, round(words / 200)))


# ---------------------------------------------------------------- rendering


def render_body(spec: dict) -> str:
    parts: list[str] = []
    for b in spec["body"]:
        t = b["type"]
        if t == "h2":
            anchor = b.get("id") or slugify(b["text"])
            parts.append(f'        <h2 id="{anchor}">{esc(b["text"])}</h2>')
        elif t == "p":
            parts.append(f'        <p>{inline(b["text"])}</p>')
        elif t in ("ul", "ol", "steps"):
            tag = "ol" if t in ("ol", "steps") else "ul"
            items = "\n".join(f"          <li>{inline(i)}</li>" for i in b["items"])
            parts.append(f"        <{tag}>\n{items}\n        </{tag}>")
        elif t == "callout":
            parts.append(
                '        <div class="callout">\n'
                f'          <span class="lbl">{esc(b.get("label", "Honest limits"))}</span>\n'
                f'          <p>{inline(b["text"])}</p>\n'
                "        </div>"
            )
        elif t == "cta":
            parts.append(
                '        <div class="ctabox">\n'
                '          <div class="halo" aria-hidden="true"></div>\n'
                f'          <span class="k">{esc(b["kicker"])}</span>\n'
                f'          <h3>{esc(b["heading"])}</h3>\n'
                f'          <p>{inline(b["text"])}</p>\n'
                '          <div class="row">\n'
                '            <a class="btn solid" href="../../try/">Try free in your browser</a>\n'
                '            <a class="btn onink" href="https://designesh.gumroad.com/l/videodoc">'
                "Get Pro · $19 lifetime</a>\n"
                "          </div>\n"
                "        </div>"
            )
    return "\n\n".join(parts)


def render_faq(spec: dict) -> str:
    out = []
    for i, q in enumerate(spec["faq"]):
        opened = " open" if i == 0 else ""
        out.append(
            f"          <details{opened}>\n"
            f'            <summary>{esc(q["q"])}</summary>\n'
            f'            <p>{inline(q["a"])}</p>\n'
            "          </details>"
        )
    return "\n".join(out)


def card(slug: str, title: str, blurb: str, cat: str, minutes: int, prefix: str) -> str:
    return (
        f'          <a class="artcard" href="{prefix}{slug}/">\n'
        f'            <span class="t">{esc(title)}</span>\n'
        f"            <p>{esc(blurb)}</p>\n"
        f'            <span class="meta"><span>{cat.upper()} · {minutes} min</span>'
        f'<span class="go">→</span></span>\n'
        "          </a>"
    )


def render_related(spec: dict, index: dict) -> str:
    picked = spec["related"]
    out = []
    for slug in picked:
        meta = index[slug]
        out.append(card(slug, meta["title"], meta["blurb"], meta["cat"], meta["min"], "../"))
    return "\n".join(out)


# ---------------------------------------------------------------- site index


def scan_articles() -> dict:
    """Read every published article's identity straight off disk.

    Deriving this from the files rather than a side-car list means the index can
    never drift out of step with what is actually live.
    """
    index: dict[str, dict] = {}
    for d in sorted(ARTICLES.iterdir()):
        if not d.is_dir() or not (d / "index.html").exists():
            continue
        raw = (d / "index.html").read_text(encoding="utf-8")
        h1 = re.search(r"<h1>(.*?)</h1>", raw, re.S)
        cat = re.search(r'<span class="cat">(.*?)</span>', raw, re.S)
        mins = re.search(r"<span>(\d+) min read</span>", raw)
        desc = re.search(r'<meta name="description" content="(.*?)">', raw, re.S)
        index[d.name] = {
            "title": html.unescape(h1.group(1).strip()) if h1 else d.name,
            "cat": cat.group(1).strip() if cat else "Guide",
            "min": int(mins.group(1)) if mins else 6,
            "blurb": html.unescape(desc.group(1).strip())[:110] if desc else "",
        }
    return index


# ---------------------------------------------------------------- validation


class SpecError(Exception):
    pass


def validate(spec: dict, index: dict) -> None:
    need = ("slug", "title_tag", "meta_desc", "headline", "category",
            "hub_section", "hub_blurb", "short_answer", "body", "faq",
            "related", "closer")
    for k in need:
        if k not in spec:
            raise SpecError(f"spec is missing required key: {k}")

    slug = spec["slug"]
    if slug != slugify(slug):
        raise SpecError(f"slug {slug!r} is not url-clean (want {slugify(slug)!r})")
    if (ARTICLES / slug).exists():
        raise SpecError(f"articles/{slug}/ already exists - pick a new slug or delete it first")

    if len(spec["title_tag"]) > MAX_TITLE:
        raise SpecError(f"title_tag is {len(spec['title_tag'])} chars, max {MAX_TITLE}")
    if len(spec["meta_desc"]) > MAX_DESC:
        raise SpecError(f"meta_desc is {len(spec['meta_desc'])} chars, max {MAX_DESC}")
    if len(spec["meta_desc"]) < 70:
        raise SpecError(f"meta_desc is only {len(spec['meta_desc'])} chars - too thin to earn a click")

    if spec["category"] not in CATEGORIES:
        raise SpecError(f"category {spec['category']!r} not one of {sorted(CATEGORIES)}")
    if spec["hub_section"] not in HUB_SECTIONS:
        raise SpecError(f"hub_section must be one of {HUB_SECTIONS}")

    for b in spec["body"]:
        if b.get("type") not in BLOCK_TYPES:
            raise SpecError(f"unknown body block type: {b.get('type')!r}")
    if not any(b["type"] == "cta" for b in spec["body"]):
        raise SpecError("body has no cta block - every article must offer the next step")
    if sum(1 for b in spec["body"] if b["type"] == "h2") < 3:
        raise SpecError("body needs at least 3 h2 sections to be worth publishing")

    if not 3 <= len(spec["faq"]) <= 6:
        raise SpecError(f"faq has {len(spec['faq'])} entries, want 3 to 6")

    if len(spec["related"]) != 3:
        raise SpecError(f"related must name exactly 3 existing articles, got {len(spec['related'])}")
    for r in spec["related"]:
        if r not in index:
            raise SpecError(f"related article {r!r} does not exist on disk")
        if r == slug:
            raise SpecError("an article cannot be related to itself")

    # A duplicate title is the clearest signal of keyword cannibalisation, and
    # it is cheap to catch here rather than in Search Console three months on.
    for other, meta in index.items():
        if meta["title"].strip().lower() == spec["headline"].strip().lower():
            raise SpecError(f"headline duplicates existing article {other!r}")


def check_rendered(page: str, slug: str) -> None:
    """Post-render checks: the things that silently break a page."""
    for blob in re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', page, re.S):
        json.loads(blob)  # raises on malformed schema

    # Match the placeholder token itself, not bare braces: nested JSON-LD ends
    # in "}}" all the time, which made a naive brace check fail every run.
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", page)
    if leftover:
        raise SpecError(f"template placeholders left unfilled: {sorted(set(leftover))}")

    if page.count("<h1>") != 1:
        raise SpecError(f"page has {page.count('<h1>')} h1 tags, want exactly 1")

    if f"/articles/{slug}/" not in page:
        raise SpecError("canonical url does not match the slug")

    # Relative asset links must resolve from articles/<slug>/. Fragments and
    # query strings are addresses within a page, not files, so they come off
    # before the path is checked.
    for href in re.findall(r'(?:href|src)="(\.\./\.\./[^"]+)"', page):
        path = href.split("#", 1)[0].split("?", 1)[0]
        if not path or path.rstrip("/") in ("..", "../.."):
            continue
        target = (ARTICLES / slug / path).resolve()
        if target.is_dir():
            target = target / "index.html"
        if not target.exists():
            raise SpecError(f"relative link {href} resolves to a missing file: {target}")


# ---------------------------------------------------------------- writers


def build_page(spec: dict, index: dict, today: str) -> str:
    minutes = read_minutes(spec)
    tpl = TEMPLATE.read_text(encoding="utf-8")

    article_ld = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": spec["headline"], "description": spec["meta_desc"],
        "datePublished": today, "dateModified": today,
        "author": {"@type": "Person", "name": "Inam Ul Haq"},
        "publisher": {"@type": "Organization", "name": "VideoDoc",
                      "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/og.png"}},
        "image": f"{SITE}/assets/og.png",
        "mainEntityOfPage": f"{SITE}/articles/{spec['slug']}/",
    }
    faq_ld = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": q["a"]}}
                       for q in spec["faq"]],
    }
    crumb_ld = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "Articles", "item": f"{SITE}/articles/"},
            {"@type": "ListItem", "position": 3, "name": spec["headline"]},
        ],
    }

    fills = {
        "TITLE_TAG": esc(spec["title_tag"]),
        "META_DESC": html.escape(spec["meta_desc"], quote=True),
        "OG_TITLE": html.escape(spec.get("og_title", spec["headline"]), quote=True),
        "OG_DESC": html.escape(spec.get("og_desc", spec["meta_desc"]), quote=True),
        "SLUG": spec["slug"],
        "CATEGORY": esc(spec["category"]),
        "HEADLINE": esc(spec["headline"]),
        "DATE_HUMAN": human_date(today),
        "READ_MIN": str(minutes),
        "SHORT_ANSWER": inline(spec["short_answer"]),
        "BODY": render_body(spec),
        "FAQ": render_faq(spec),
        "CLOSER": inline(spec["closer"]),
        "RELATED": render_related(spec, index),
        "SCHEMA_ARTICLE": json.dumps(article_ld, ensure_ascii=False),
        "SCHEMA_FAQ": json.dumps(faq_ld, ensure_ascii=False),
        "SCHEMA_BREADCRUMB": json.dumps(crumb_ld, ensure_ascii=False),
    }
    page = tpl
    for k, v in fills.items():
        page = page.replace("{{" + k + "}}", v)
    return page


def insert_hub_card(spec: dict, minutes: int) -> str:
    raw = HUB.read_text(encoding="utf-8")
    sections = list(re.finditer(r'<section class="artsec">', raw))
    idx = HUB_SECTIONS.index(spec["hub_section"])
    if idx >= len(sections):
        raise SpecError(f"hub has {len(sections)} sections, cannot target #{idx + 1}")

    start = sections[idx].end()
    end = sections[idx + 1].start() if idx + 1 < len(sections) else len(raw)
    block = raw[start:end]

    last = None
    for m in re.finditer(r'        <a class="artcard".*?</a>\n', block, re.S):
        last = m
    if last is None:
        raise SpecError(f"no existing card found in hub section #{idx + 1} to anchor after")

    new_card = card(spec["slug"], spec["headline"], spec["hub_blurb"],
                    spec["category"], minutes, "").replace("\n          ", "\n          ")
    # Hub cards sit one indent level shallower than the related-grid cards.
    new_card = "\n".join(line[2:] if line.startswith("          ") else line
                         for line in new_card.split("\n"))
    at = start + last.end()
    return raw[:at] + new_card + "\n" + raw[at:]


def insert_sitemap(slug: str, today: str) -> str:
    raw = SITEMAP.read_text(encoding="utf-8")
    if f"/articles/{slug}/" in raw:
        raise SpecError(f"sitemap already lists {slug}")
    entry = (f"  <url>\n"
             f"    <loc>{SITE}/articles/{slug}/</loc>\n"
             f"    <lastmod>{today}</lastmod>\n"
             f"    <changefreq>monthly</changefreq>\n"
             f"    <priority>0.7</priority>\n"
             f"  </url>\n")
    raw = raw.replace("</urlset>", entry + "</urlset>")
    # The hub gained a card, so its lastmod moves too.
    raw = re.sub(r"(<loc>" + re.escape(SITE) + r"/articles/</loc>\s*<lastmod>)[\d-]+",
                 r"\g<1>" + today, raw)
    return raw


def add_backlinks(spec: dict, index: dict, minutes: int) -> dict[Path, str]:
    """Give the new article three inbound links from the pages it cites.

    An article that only the hub links to is an orphan, and orphans do not rank.
    Each of the three 'related' pages drops its oldest related card and picks up
    the new one, so link equity actually flows to the newest page.
    """
    edits: dict[Path, str] = {}
    new_card = card(spec["slug"], spec["headline"], spec["hub_blurb"],
                    spec["category"], minutes, "../")
    for slug in spec["related"]:
        path = ARTICLES / slug / "index.html"
        raw = path.read_text(encoding="utf-8")
        if f'href="../{spec["slug"]}/"' in raw:
            continue
        grid = re.search(r'(<div class="relgrid">\n)(.*?)(\n        </div>)', raw, re.S)
        if not grid:
            continue
        cards = re.findall(r'          <a class="artcard".*?</a>', grid.group(2), re.S)
        if not cards:
            continue
        kept = cards[1:] if len(cards) >= 3 else cards
        body = "\n".join([new_card] + kept)
        edits[path] = raw[:grid.start(2)] + body + raw[grid.end(2):]
    return edits


# ---------------------------------------------------------------- verify


def verify_site() -> int:
    """Audit what is on disk: every article in the sitemap, no dangling links."""
    problems: list[str] = []
    index = scan_articles()
    sitemap = SITEMAP.read_text(encoding="utf-8")
    hub = HUB.read_text(encoding="utf-8")

    for slug in index:
        if f"/articles/{slug}/" not in sitemap:
            problems.append(f"articles/{slug}/ is live but missing from sitemap.xml")
        if f'href="{slug}/"' not in hub:
            problems.append(f"articles/{slug}/ has no card on the articles hub")

    for loc in re.findall(r"<loc>" + re.escape(SITE) + r"(/[^<]*)</loc>", sitemap):
        rel = loc.strip("/")
        target = ROOT / rel / "index.html" if rel else ROOT / "index.html"
        if not target.exists():
            problems.append(f"sitemap lists {loc} but {target.relative_to(ROOT)} does not exist")

    for page in list(ROOT.rglob("*.html")):
        if "tools" in page.parts:
            continue
        raw = page.read_text(encoding="utf-8")
        # Relative (../foo/) and root-relative (/foo/) both have to resolve. The
        # root-relative form is the one that bit us: it looks fine in an editor
        # and only 404s once the page is served from a domain root.
        for href in re.findall(r'(?:href|src)="([./][^":#?]*)"', raw):
            if href in ("./", "/"):
                continue
            base = ROOT if href.startswith("/") else page.parent
            target = (base / href.lstrip("/")).resolve()
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                problems.append(f"{page.relative_to(ROOT)} -> dangling link {href}")
        for blob in re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', raw, re.S):
            try:
                json.loads(blob)
            except json.JSONDecodeError as e:
                problems.append(f"{page.relative_to(ROOT)} -> malformed JSON-LD: {e}")

    if problems:
        print(f"{len(problems)} problem(s):")
        for p in sorted(set(problems)):
            print("  -", p)
        return 1
    print(f"site OK: {len(index)} articles, all in sitemap, all on the hub, no dangling links")
    return 0


# ---------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", nargs="?", help="path to the article spec JSON")
    ap.add_argument("--check", action="store_true", help="validate and render, write nothing")
    ap.add_argument("--verify-site", action="store_true", help="audit the whole site and exit")
    ap.add_argument("--date", default=date.today().isoformat(), help="publish date (YYYY-MM-DD)")
    args = ap.parse_args()

    if args.verify_site:
        return verify_site()
    if not args.spec:
        ap.error("give a spec file, or use --verify-site")

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    index = scan_articles()

    try:
        validate(spec, index)
        page = build_page(spec, index, args.date)
        check_rendered(page, spec["slug"])
        minutes = read_minutes(spec)
        hub = insert_hub_card(spec, minutes)
        sitemap = insert_sitemap(spec["slug"], args.date)
        backlinks = add_backlinks(spec, index, minutes)
    except (SpecError, KeyError, json.JSONDecodeError) as e:
        print(f"ABORTED, nothing written: {e}", file=sys.stderr)
        return 1

    if args.check:
        print(f"OK (dry run): {spec['slug']} · {minutes} min · "
              f"{len(spec['faq'])} faq · {len(backlinks)} backlinks · "
              f"title {len(spec['title_tag'])}/{MAX_TITLE} · desc {len(spec['meta_desc'])}/{MAX_DESC}")
        return 0

    out = ARTICLES / spec["slug"]
    out.mkdir(parents=True)
    (out / "index.html").write_text(page, encoding="utf-8", newline="\n")
    HUB.write_text(hub, encoding="utf-8", newline="\n")
    SITEMAP.write_text(sitemap, encoding="utf-8", newline="\n")
    for path, text in backlinks.items():
        path.write_text(text, encoding="utf-8", newline="\n")

    print(f"published articles/{spec['slug']}/ · {minutes} min read")
    print(f"  hub card added to the '{spec['hub_section']}' section")
    print(f"  sitemap entry added ({args.date})")
    print(f"  inbound links added from: {', '.join(p.parent.name for p in backlinks)}")
    return verify_site()


if __name__ == "__main__":
    raise SystemExit(main())

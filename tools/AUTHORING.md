# How to write one VideoDoc article

This is the brief the daily article job follows. It exists so that a page
written in month six reads like a page written in month one.

## The job, in order

1. Open `tools/queue.json`. Take the **first** item whose `done` is `null`.
2. Write a spec JSON for it (shape below). Prose only — no HTML.
3. `py -3.12 tools/new_article.py spec.json --check` — fix whatever it rejects.
4. `py -3.12 tools/new_article.py spec.json` — publishes, and re-verifies the
   whole site before it exits. A non-zero exit means **do not commit**.
5. Stamp `done` with today's date in `tools/queue.json`.
6. Commit and push. The site is live within a minute of the push.

`new_article.py` owns every structural decision: the three JSON-LD blobs, the
hub card, the sitemap entry, the reciprocal internal links, the read-time
estimate. Do not hand-edit generated HTML — if the output is wrong, the script
is wrong, so fix the script.

## Voice

Read `articles/youtube-video-to-pdf/index.html` before writing. That is the
target. In short:

- **First person, one person.** "I built this because I wanted my AI to read
  the lectures I study from." Never "we", never a company voice.
- **Plain words.** Short sentences. If a sentence needs a comma to survive,
  it probably needs to be two sentences.
- **Concrete over clever.** "An hour of video is about 14,400 images" beats
  "a substantial volume of extracted content".
- **Admit the limits, in the article, unprompted.** Every page carries an
  honest-limits callout. This is the single biggest reason these pages get
  cited rather than skimmed. If a page has nothing to admit, the page is
  probably lying.
- **A real anecdote, once per article.** One paragraph of lived detail — the
  lecture that made no sense a month later, the friend who pressed Return
  before dragging the file. Never invent an anecdote that could be checked
  and found false; keep them about the tool and the work.
- **Never an em dash.** Not one appears in his own writing, and it is the
  clearest signal a line was not typed by him. Use a comma, a colon, or two
  sentences. The same goes for the `--` and `&mdash;` forms.
- **No hype.** Not "revolutionary", not "seamless", not "game-changing". The
  product is a small honest desktop tool and the writing should sound like it.
- **Never promise what the app does not do.** Cross-check any capability claim
  against `CHANGELOG.md` in the app repo. Public videos only. Two machines per
  licence, freed only by replying to the Gumroad receipt (there is no in-app
  move). Apple Silicon only on Mac, macOS 14 or newer.
- **Price: write no number.** Say Pro is a one time payment and link to the
  pricing on the home page. The price is not settled (Gumroad showed $10 on
  2026-11-14 while older pages said $19), so a number in an article goes stale.
- **Claim only released versions.** The live version is the one in
  https://github.com/inam8eng/videodoc-releases/releases/latest/download/videodoc_version.json.
  `CHANGELOG.md` can carry a newer, unreleased version at its top, so check the
  feed before describing the top entry. v0.5.0 was released on 2026-11-15.
- **Video to shorts (v0.5.0, released 2026-11-15, Windows and Apple Silicon
  Macs).** A second tab turns a long video into vertical shorts. It finds the
  best parts with 1 to 5 dots and a plain reason for each, trims on a simple
  timeline, and the frame follows the face, shows the whole picture, puts a
  facecam on top, or stays where the reader drags it. Word by word captions are
  on by default. It exports 1080x1920, or square, 4:5 or the original shape.
  Lite takes videos up to 20 minutes and adds a small "Made with VideoDoc"
  mark; Pro has no limit and no mark. The first run downloads the speech engine
  once (about 486 MB for Balanced). Do not claim shorts on iPhone or Android
  (not released), never promise views or income, and only show clipping
  someone else's video when they allow it. The product page for shorts is
  https://videostodoc.com/shorts/ (live since 2026-11-15): every shorts
  article links to it once, in the cta or in a sentence after the reader has
  been helped. Never link /iphone/ from an article while it is a beta.
- **More formats (v0.4.0, released 2026-11-13).** Every finished document has
  a More formats button: Word (words and pictures), PowerPoint, Excel and 25
  more. Lite's free ones are SRT, VTT, CSV and JSON, the rest are Pro. The AI
  kits are prompt files the reader pastes into their own ChatGPT or Claude;
  VideoDoc has no AI that writes. Do not name Premiere Pro or DaVinci Resolve
  for the cut list (it was never tried in them). Do not say VideoDoc sends
  nothing anywhere (the licence and update checks use the internet).

## Structure of a good page

- **The short answer** up top, 40–70 words, answering the query outright.
  Someone who reads only this box should leave satisfied.
- **3 to 6 `h2` sections.** At least one must be a genuinely useful free
  method that does not involve buying anything — including where it stops.
- **One `callout`** with honest limits.
- **One `cta`**, placed after the value is delivered, never before.
- **3 FAQ entries** (the script needs at least 3): short, only questions readers
  really ask, never padded. FAQ rich results ended in May 2026; they are not
  there for Google (mandate retired on Inam's yes, 2026-11-15).
- **A closer**: one or two sentences telling the reader the single next thing
  to do tonight.

## Length

800–1,400 words. The script computes read time and refuses anything that lands
outside 4–12 minutes. Under 800 words does not rank; over 1,400 is usually one
article pretending to be two — split it and queue the second.

## Titles and descriptions

- `title_tag` **max 60 characters**, and it must contain the target keyword.
- `meta_desc` **70–160 characters**, written to earn a click, not to summarise.
- `headline` is the on-page `h1` and may differ from `title_tag`. Make it read
  like a sentence a person would say.
- Never duplicate an existing headline. The script blocks this, because two
  pages chasing one keyword means neither wins.

## Internal links

Pick `related` as **exactly 3 existing slugs** that a reader of this page would
genuinely want next. The script also rewrites those three pages to link back,
so the new article is never an orphan. Prefer articles in the same
`hub_section`, plus one deliberate jump to a different section.

## Spec shape

```json
{
  "slug": "extract-every-frame-from-a-video",
  "title_tag": "Extract Every Frame From a Video (2026 Guide)",
  "meta_desc": "Save a whole video as images, four a second, with duplicates removed and every file named by its exact moment. Runs on your own computer.",
  "og_title": "Extract every frame from a video",
  "og_desc": "Four frames a second, duplicates removed, every file named by its moment.",
  "headline": "How to extract every frame from a video",
  "category": "Work",
  "hub_section": "work",
  "hub_blurb": "Four a second, duplicates dropped, each one named by its exact moment.",
  "short_answer": "…40–70 words…",
  "body": [
    { "type": "p",  "text": "Opening paragraph." },
    { "type": "h2", "text": "The free way, and where it stops" },
    { "type": "ol", "items": ["First step.", "Second step."] },
    { "type": "callout", "label": "Honest limits", "text": "What this does not do." },
    { "type": "cta", "kicker": "One video, every frame",
      "heading": "Try it on a file you already have.",
      "text": "Free in your browser. Pro is a one time payment." }
  ],
  "faq": [
    { "q": "How many images is an hour of video?", "a": "About 14,400 at four a second." }
  ],
  "related": ["extract-slides-from-video", "youtube-video-to-pdf", "video-lecture-to-notes"],
  "closer": "Pick the video you keep rewatching and pull its frames tonight."
}
```

Body block types: `h2`, `p`, `ul`, `ol`, `steps`, `callout`, `cta`.
Inside any text you may use `**bold**`, `` `code` `` and `[label](url)`.
Everything else is escaped — that is deliberate.

## Weekly pass (Mondays)

On top of the day's article:

1. `py -3.12 tools/new_article.py --verify-site` — must exit clean.
2. Check Search Console for queries the site is getting impressions but no
   clicks on. Those are title and description problems, not content problems;
   rewrite the meta and note it.
3. A query the site ranks 8 to 20 for means: improve the page that already ranks
   for it. Queue a new page only when no existing page answers that query, and
   name in the queue row the page it would otherwise compete with. (Changed on
   Inam's yes, 2026-11-15: a new page for every ranked query made near twins.)
   `download-youtube-video-hd-4k` is noindex since 2026-11-15: keep it out of
   the sitemap and llms.txt, and never link to it from a new article.
4. Re-read the two oldest articles. If a claim has gone stale against
   `CHANGELOG.md`, fix it and bump `dateModified` in the Article schema.

## What not to do

- Do not publish two articles in one day to catch up. The cadence is the point.
- Do not write a page for a keyword the product cannot honestly serve.
- Do not touch `style.css` or `article.css` from the article job. Layout
  changes belong in their own commit, reviewed by a human.
- Do not let the queue run dry silently. When fewer than 7 items remain, say so
  in the commit message.

## Article images

Every article gets its own banner, drawn by `tools/make_article_art.py` from the
slug in the site's flat-vector blue style. `new_article.py` runs it automatically
at publish time, so a new article always ships with a matching image. To redraw
them all after a style change: `py -3.12 tools/make_article_art.py`. A spec can
point at a hand-made image instead with `"hero": "some-file.jpg"` (a filename in
`assets/art/`).

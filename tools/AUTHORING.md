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
- **No hype.** Not "revolutionary", not "seamless", not "game-changing". The
  product is a small honest desktop tool and the writing should sound like it.
- **Never promise what the app does not do.** Cross-check any capability claim
  against `CHANGELOG.md` in the app repo. Public videos only. Two machines per
  licence. Apple Silicon only on Mac. $19 once.

## Structure of a good page

- **The short answer** up top, 40–70 words, answering the query outright.
  Someone who reads only this box should leave satisfied. This box is what
  AI search engines quote.
- **3 to 6 `h2` sections.** At least one must be a genuinely useful free
  method that does not involve buying anything — including where it stops.
- **One `callout`** with honest limits.
- **One `cta`**, placed after the value is delivered, never before.
- **3 to 6 FAQ entries**, phrased as real queries. These become FAQPage schema.
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
      "text": "Free in your browser. Pro is $19 once." }
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
3. Any query the site ranks 8–20 for is worth a dedicated page — add it to the
   **top** of the queue, above the planned items.
4. Re-read the two oldest articles. If a claim has gone stale against
   `CHANGELOG.md`, fix it and bump `dateModified` in the Article schema.

## What not to do

- Do not publish two articles in one day to catch up. The cadence is the point.
- Do not write a page for a keyword the product cannot honestly serve.
- Do not touch `style.css` or `article.css` from the article job. Layout
  changes belong in their own commit, reviewed by a human.
- Do not let the queue run dry silently. When fewer than 7 items remain, say so
  in the commit message.

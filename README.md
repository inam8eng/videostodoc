# VideoDoc website — deploy guide

Static site, no build step, no server. Built on the Designesh **"Node × Matrix"**
brand (light page `#F4F5F7`, one orange accent `#FF6A2C`, JetBrains Mono display +
IBM Plex Sans body, a faint dot-matrix field, a floating app-window hero). Light and
dark themes via the toggle.

Files:
- `index.html` + `style.css` — the landing page (fonts from Google Fonts).
- `try/` — the **free in-browser app**: drop a file, it transcribes on the visitor's own machine (WebGPU, falls back to CPU), download the transcript. Costs you nothing to run. Shares `style.css`; logic in `app.js` (unchanged).
- `favicon.svg` — the VideoDoc mark (an orange tile with a white eye + pupil).
- `assets/og.png` — social-share image on the orange brand (regenerate with `assets/make_og.py`).
- `assets/*.jpg` + `assets/make_frames.py` — legacy sample-frame images; the current hero and features are built in HTML/CSS, so these are no longer referenced by the page.
- `_headers`, `robots.txt`, `sitemap.xml` — Cloudflare Pages config + SEO.

Hosting is **free** on Cloudflare Pages. Domain `videostodoc.com` is already baked
into the canonical URL, Open Graph tags, and sitemap.

## Model
- **Free** = `try/` (runs in the visitor's browser, local files only, transcript).
- **Pro** = the full desktop app on **Gumroad** (`https://designesh.gumroad.com/l/videodoc`) — YouTube, playlists, long videos, keyframes, forever.
- Every Buy button points at `designesh.gumroad.com/l/videodoc`. **No binary is published here** (the app ships via Gumroad).

## Preview locally
The `try/` app loads its AI model over the network, so serve over **http**, not `file://`:
```
cd "D:\Projects\Gumroad\2026-06-12 Claude VideoDoc\site"
python -m http.server 8000
```
Open `http://localhost:8000/` (landing) and `http://localhost:8000/try/` (the app).
Use **Chrome or Edge** for the GPU path; first run downloads the model once.

## Deploy — Cloudflare Pages (free, zero-config)
1. Cloudflare → **Workers & Pages → Create → Pages → Upload assets** (Direct Upload).
   Drag the whole `site/` folder in. No repo, no build step, no framework.
2. It deploys to a free `*.pages.dev` URL in seconds. Test `/` and `/try/` there —
   you can share this link immediately, before the domain is live.
3. When `videostodoc.com` is registered: Pages project → **Custom domains** → add
   `videostodoc.com`. If the domain is on Cloudflare, DNS + HTTPS auto-configure;
   otherwise point its nameservers to Cloudflare first. Delete any parking records.

## Notes
- Site cost **$0/mo**, domain ~$12/yr, transcription compute **$0** (runs in each visitor's browser).
- The domain is hard-coded as `https://videostodoc.com`. If you register a different
  name, Find & Replace `videostodoc.com` across `index.html`, `try/index.html`,
  `sitemap.xml`, `robots.txt`.
- To update later: edit the files, re-upload the folder, Cloudflare redeploys in seconds.

> Ready to deploy? Ask the AI OS to run the **host-otherdom-on-cloudflare** skill for the click-by-click with the gotchas.

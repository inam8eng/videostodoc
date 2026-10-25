// Main thread: decode the chosen file to 16kHz mono audio, hand it to the worker,
// render the transcript, let the user download it. Nothing leaves the browser.
const GUMROAD = "https://designesh.gumroad.com/l/videodoc";
const $ = (id) => document.getElementById(id);
const fileInput = $("file");
const drop = $("drop");
const statusEl = $("status");
const barWrap = $("barwrap");
const barEl = $("bar");
const outWrap = $("outwrap");
const outEl = $("out");

let worker = null;
let lastText = "";
let lastChunks = [];
let lastName = "transcript";
let busy = false;
const prog = {};

// ---------- the working view ----------
// Built here, not in index.html: for a few minutes after an update a visitor
// can have the old page with this new script, and everything must still work.
// Styles use the site's own tokens, so light and dark themes both follow.
const CSS = `
.drop{transition:border-color .2s,background .2s,transform .2s,box-shadow .2s}
.drop.over{border-style:solid;transform:scale(1.01);box-shadow:0 0 0 5px var(--orange-wash)}
.drop.nope{border-color:#BB3434;background:rgba(187,52,52,.07);cursor:no-drop}
.drop.shake{animation:vdt-shake .4s ease-in-out}
html.vdt-drag .drop{border-color:var(--accent);animation:vdt-glow 1.6s ease-in-out infinite}
.vdt-card,.vdt-done{display:flex;align-items:center;gap:14px;max-width:560px;margin:14px auto 0;text-align:left}
.vdt-card{padding:12px 14px;border:1px solid var(--border-strong);border-radius:14px;background:var(--surface)}
.vdt-thumb{width:96px;height:54px;flex:0 0 auto;border-radius:8px;overflow:hidden;background:var(--surface-sunk);display:flex;align-items:center;justify-content:center;color:var(--text-accent)}
.vdt-thumb img{width:100%;height:100%;object-fit:cover;display:block}
.vdt-main{flex:1;min-width:0}
.vdt-name{font-family:var(--font-mono);font-weight:700;font-size:14px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.vdt-meta{font-family:var(--font-mono);font-size:12.5px;color:var(--text-muted);margin-top:3px;font-variant-numeric:tabular-nums}
.vdt-steps{display:flex;flex-wrap:wrap;justify-content:center;gap:6px 18px;list-style:none;padding:0;margin:16px 0 0;font-family:var(--font-mono);font-size:12.5px;color:var(--text-faint)}
.vdt-steps li{display:inline-flex;align-items:center;gap:7px}
.vdt-steps .d{width:10px;height:10px;border-radius:50%;border:1.5px solid var(--border-strong);background:var(--surface);flex:0 0 auto}
.vdt-steps li.done{color:var(--green-deep)}
.vdt-steps li.done .d{background:var(--green);border-color:var(--green)}
.vdt-steps li.now{color:var(--text-accent);font-weight:700}
.vdt-steps li.now .d{border-color:var(--accent);background:var(--orange-wash);animation:vdt-beat 1.2s ease-in-out infinite}
.vdt-live{max-width:560px;margin:10px auto 0;text-align:center}
.vdt-cheer{color:var(--green-deep);font-size:14px}
.vdt-cheer.fresh,.vdt-heard.fresh{animation:vdt-in .25s ease-out}
.vdt-clock{font-family:var(--font-mono);font-size:12.5px;color:var(--text-muted);margin-top:4px;font-variant-numeric:tabular-nums}
.vdt-heard{margin:10px auto 0;padding:10px 14px;border-left:3px solid var(--accent);background:var(--orange-wash);border-radius:0 10px 10px 0;text-align:left;font-size:14.5px;line-height:1.55;color:var(--text);overflow-wrap:anywhere}
.vdt-done{justify-content:center}
.vdt-tick{width:34px;height:34px;border-radius:50%;background:var(--green);color:#fff;display:flex;align-items:center;justify-content:center;flex:0 0 auto}
.vdt-tick path{stroke-dasharray:24;stroke-dashoffset:24;animation:vdt-draw .45s .1s ease-out forwards}
.vdt-chips{display:flex;flex-wrap:wrap;gap:6px}
.vdt-chip{font-family:var(--font-mono);font-size:12.5px;font-weight:600;padding:4px 10px;border-radius:999px;background:var(--green-wash);color:var(--green-deep);font-variant-numeric:tabular-nums}
.vdt-card[hidden],.vdt-done[hidden],.vdt-steps[hidden],.vdt-live[hidden],.vdt-heard[hidden]{display:none!important}
@keyframes vdt-glow{0%,100%{box-shadow:0 0 0 0 var(--orange-wash)}50%{box-shadow:0 0 0 7px var(--orange-wash)}}
@keyframes vdt-shake{0%,100%{transform:translateX(0)}20%,60%{transform:translateX(-6px)}40%,80%{transform:translateX(6px)}}
@keyframes vdt-beat{0%,100%{box-shadow:0 0 0 0 var(--orange-wash)}50%{box-shadow:0 0 0 4px var(--orange-wash)}}
@keyframes vdt-in{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
@keyframes vdt-draw{to{stroke-dashoffset:0}}
@media (prefers-reduced-motion:reduce){.vdt-tick path{stroke-dashoffset:0!important}}
@media (max-width:560px){.vdt-thumb{width:72px;height:41px}}
`;
const ICO_VIDEO = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="5" width="15" height="14" rx="2"/><path d="m17 10 5-3v10l-5-3z"/></svg>';
const ICO_AUDIO = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>';

const STEPS = [["read", "Read file"], ["model", "Load AI (first time)"], ["listen", "Listen"], ["ready", "Ready"]];
const CHEER = {
  read: ["Reading your file, right here in your browser."],
  model: ["Getting the AI ready. This happens once, then your browser keeps it.", "Almost ready to listen."],
  listen: ["Listening to every word.", "Writing down what is said.", "Nothing leaves your computer."],
};

const V = {};   // the working-view elements, created once
function buildView() {
  if (V.card) return;
  const style = document.createElement("style");
  style.textContent = CSS;
  document.head.appendChild(style);
  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html) n.innerHTML = html;
    n.hidden = true;
    return n;
  };
  V.card = el("div", "vdt-card",
    '<div class="vdt-thumb"></div><div class="vdt-main"><div class="vdt-name"></div><div class="vdt-meta"></div></div>');
  V.steps = el("ol", "vdt-steps", STEPS.map(([k, label]) =>
    `<li data-step="${k}"><span class="d"></span>${label}</li>`).join(""));
  V.steps.setAttribute("aria-label", "Steps");
  V.live = el("div", "vdt-live", '<div class="vdt-cheer"></div><div class="vdt-clock"></div>');
  V.heard = el("div", "vdt-heard");
  V.heard.title = "The words being written down right now";
  V.done = el("div", "vdt-done",
    '<span class="vdt-tick" aria-hidden="true"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg></span><div class="vdt-chips"></div>');
  drop.after(V.card, V.steps, V.live, V.heard);
  (outWrap || barWrap).before(V.done);
  // The status line moves under the stepper, where the eye already is.
  if (statusEl) V.live.after(statusEl);
  if (barWrap) statusEl.after(barWrap);
}

// ---------- step, timer, encouragement ----------
let step = "";
let t0 = 0;
let audioSecs = 0;
let clockTimer = 0;
let heardText = "";
let lastCheer = "";

function setStep(s) {
  step = s;
  V.steps.hidden = false;
  const at = STEPS.findIndex(([k]) => k === s);
  V.steps.querySelectorAll("li").forEach((li, i) => {
    li.className = i < at || s === "ready" ? "done" : i === at ? "now" : "";
  });
  tickClock();
}
function fmtClock(sec) {
  sec = Math.max(0, Math.round(sec || 0));
  const m = Math.floor(sec / 60), s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
function tickClock() {
  if (!t0) return;
  const secs = (performance.now() - t0) / 1000;
  const list = CHEER[step] || [];
  const cheer = list.length ? list[Math.floor(secs / 6) % list.length] : "";
  const ch = V.live.querySelector(".vdt-cheer");
  if (cheer !== lastCheer) {
    ch.textContent = cheer;
    ch.classList.remove("fresh"); void ch.offsetWidth; ch.classList.add("fresh");
    lastCheer = cheer;
  }
  V.live.querySelector(".vdt-clock").textContent =
    (audioSecs ? `${fmtClock(audioSecs)} of audio · ` : "") + `${Math.round(secs)} s so far`;
  V.live.hidden = !cheer;
}
function startWork() {
  t0 = performance.now();
  heardText = ""; lastCheer = ""; audioSecs = 0;
  V.heard.hidden = true; V.heard.textContent = "";
  V.done.hidden = true;
  clearInterval(clockTimer);
  clockTimer = setInterval(tickClock, 1000);
  setStep("read");
}
function stopWork() {
  clearInterval(clockTimer);
  V.live.hidden = true;
}
function showHeard(piece) {
  heardText = (heardText + piece).replace(/\s+/g, " ");
  const tail = heardText.length > 180 ? "…" + heardText.slice(-180).replace(/^\S*\s/, "") : heardText;
  if (!tail.trim()) return;
  V.heard.textContent = `“${tail.trim()}”`;
  if (V.heard.hidden) {
    V.heard.hidden = false;
    V.heard.classList.remove("fresh"); void V.heard.offsetWidth; V.heard.classList.add("fresh");
  }
}

// ---------- the chosen file, as a card ----------
const MEDIA_EXT = /\.(mp4|m4v|mov|mkv|webm|avi|mpe?g|3gp|ogv|mp3|wav|m4a|aac|flac|ogg|oga|opus)$/i;
const AUDIO_EXT = /\.(mp3|wav|m4a|aac|flac|ogg|oga|opus)$/i;
const isMedia = (f) => !!f && (/^(video|audio)\//.test(f.type || "") || MEDIA_EXT.test(f.name || ""));
const isAudio = (f) => /^audio\//.test(f.type || "") || AUDIO_EXT.test(f.name || "");
function fmtSize(b) {
  if (b >= 1e9) return (b / 1e9).toFixed(1) + " GB";
  if (b >= 1e6) return (b / 1e6).toFixed(b >= 1e8 ? 0 : 1) + " MB";
  return Math.max(1, Math.round(b / 1e3)) + " KB";
}
function showCard(file) {
  V.card.hidden = false;
  V.card.querySelector(".vdt-name").textContent = file.name;
  V.card.querySelector(".vdt-name").title = file.name;
  V.card.querySelector(".vdt-meta").textContent = fmtSize(file.size);
  V.card.querySelector(".vdt-thumb").innerHTML = isAudio(file) ? ICO_AUDIO : ICO_VIDEO;
  if (isAudio(file)) return;
  // One frame from the video, made in the browser; nothing is sent anywhere.
  const url = URL.createObjectURL(file);
  const v = document.createElement("video");
  let done = false;
  const finish = () => {
    if (done) return;
    done = true;
    clearTimeout(timer);
    v.removeAttribute("src"); v.load();
    URL.revokeObjectURL(url);
  };
  const timer = setTimeout(finish, 6000);
  v.muted = true; v.preload = "metadata"; v.playsInline = true;
  v.onerror = finish;
  v.onloadedmetadata = () => {
    if (!v.videoWidth) return finish();
    v.currentTime = Math.min((v.duration || 0) * 0.15, 8);
  };
  v.onseeked = () => {
    try {
      const c = document.createElement("canvas");
      c.width = 96;
      c.height = Math.max(1, Math.min(72, Math.round(96 * v.videoHeight / v.videoWidth)));
      c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
      V.card.querySelector(".vdt-thumb").innerHTML = `<img src="${c.toDataURL("image/jpeg", 0.72)}" alt="">`;
    } catch (e) { /* no thumbnail for this one */ }
    finish();
  };
  v.src = url;
}
function cardMeta(file) {
  const bits = [fmtSize(file.size)];
  if (audioSecs) bits.push(fmtClock(audioSecs));
  V.card.querySelector(".vdt-meta").textContent = bits.join(" · ");
}

// ---------- unchanged core: status, worker, decode ----------
function setStatus(msg, pct) {
  statusEl.textContent = msg || "";
  if (typeof pct === "number") {
    barWrap.hidden = false;
    barEl.style.width = Math.max(2, Math.round(pct)) + "%";
  }
}

function ensureWorker() {
  if (worker) return worker;
  worker = new Worker("worker.js?v=20261026b", { type: "module" });
  worker.onmessage = (e) => {
    const d = e.data;
    if (d.type === "model") {
      if (step !== "model") setStep("model");
      prog[d.file] = d.progress;
      const v = Object.values(prog);
      setStatus("Downloading the AI model (one time, then it's cached) ...", v.reduce((a, b) => a + b, 0) / v.length);
    }
    else if (d.type === "status") {
      barWrap.hidden = true;
      setStatus(d.message);
      if (/^Transcribing/.test(d.message || "")) setStep("listen");
    }
    else if (d.type === "partial") { if (step !== "listen") setStep("listen"); showHeard(d.text || ""); }
    else if (d.type === "partial-reset") { heardText = ""; V.heard.hidden = true; }
    else if (d.type === "done") { busy = false; renderResult(d.text, d.chunks, d.backend); }
    else if (d.type === "error") {
      busy = false; stopWork(); barWrap.hidden = true; V.steps.hidden = true;
      setStatus("Something went wrong: " + d.message + ". Try a different file, or a Chrome/Edge browser.");
    }
  };
  worker.onerror = () => { busy = false; stopWork(); V.steps.hidden = true; setStatus("The AI engine couldn't start. Check your connection or an ad blocker, and try Chrome or Edge."); };
  return worker;
}

async function fileToAudio(file) {
  setStatus("Reading your file ...");
  const buf = await file.arrayBuffer();
  const Ctx = window.AudioContext || window.webkitAudioContext;
  const ctx = new Ctx();
  const decoded = await ctx.decodeAudioData(buf);
  ctx.close();

  const ch = decoded.numberOfChannels;
  const len = decoded.length;
  let mono = decoded.getChannelData(0);
  if (ch > 1) {
    mono = new Float32Array(len);
    for (let c = 0; c < ch; c++) {
      const data = decoded.getChannelData(c);
      for (let i = 0; i < len; i++) mono[i] += data[i] / ch;
    }
  }

  const targetRate = 16000;
  if (decoded.sampleRate === targetRate) return mono.slice();

  const off = new OfflineAudioContext(1, Math.ceil(len * targetRate / decoded.sampleRate), targetRate);
  const tmp = off.createBuffer(1, len, decoded.sampleRate);
  tmp.copyToChannel(mono, 0);
  const src = off.createBufferSource();
  src.buffer = tmp;
  src.connect(off.destination);
  src.start();
  const rendered = await off.startRendering();
  return rendered.getChannelData(0).slice();
}

function refuse(msg) {
  setStatus(msg);
  drop.classList.remove("shake"); void drop.offsetWidth; drop.classList.add("shake");
}

async function handleFile(file) {
  if (!file) return;
  if (!isMedia(file)) { refuse(`“${file.name}” is not a video or audio file. Try an MP4, MP3, WAV, M4A, or WEBM.`); return; }
  if (file.size > 300 * 1024 * 1024) { setStatus("That file is too big for the free browser demo. Try a clip under 300 MB. The desktop app handles the big ones."); return; }
  if (busy) { setStatus("Still working on the previous file, one at a time please ..."); return; }
  busy = true;
  lastName = (file.name || "transcript").replace(/\.[^.]+$/, "");
  outWrap.hidden = true;
  barWrap.hidden = true;
  const proNext = $("proNext");
  if (proNext) proNext.hidden = true;
  buildView();
  showCard(file);
  startWork();
  try {
    const audio = await fileToAudio(file);
    audioSecs = audio.length / 16000;
    cardMeta(file);
    setStatus("Starting the AI on your machine ...");
    ensureWorker().postMessage({ audio }, [audio.buffer]);
  } catch (e) {
    busy = false;
    stopWork();
    V.steps.hidden = true;
    setStatus("Couldn't read the sound in that file. It may have no sound track, or use a format "
      + "your browser can't open. Try an MP4, MP3, WAV, M4A, or WEBM. (" + e.message + ")");
  }
}

function fmt(t) {
  if (t == null) return "00:00";
  const m = Math.floor(t / 60), s = Math.floor(t % 60);
  return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
}
function escapeHtml(s) {
  return (s || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

// The free in-browser model is small (whisper-base). On music, silence, or a
// clip with no clear speech it does what every Whisper model does: it loops on
// one token, so the box fills with ">> >> >>" or a repeated word. That is not
// a real transcript and showing it as one makes the tool look broken. So we
// notice it and say plainly what happened, instead of printing the garbage.
function looksDegenerate(text) {
  const words = (text || "").trim().split(/\s+/).filter(Boolean);
  if (words.length < 12) return false;
  const counts = Object.create(null);
  let top = 0;
  for (const w of words) { counts[w] = (counts[w] || 0) + 1; if (counts[w] > top) top = counts[w]; }
  const unique = Object.keys(counts).length;
  // one token is most of the output, or almost nothing is unique
  return top / words.length > 0.4 || unique / words.length < 0.18;
}

function renderResult(text, chunks, backendUsed) {
  lastText = text || "";
  lastChunks = (chunks || []).filter((c) => c && c.text && c.text.trim());
  barWrap.hidden = true;
  stopWork();
  V.heard.hidden = true;

  const proNext = $("proNext");

  if (!lastText.trim() || looksDegenerate(lastText)) {
    setStatus("");
    V.steps.hidden = true;
    outEl.innerHTML =
      '<div class="emptyout">' +
      '<b>That clip did not have clear speech to transcribe.</b>' +
      '<span>The free in-browser model needs someone actually talking. If the clip was mostly music, silence, or background noise, it has nothing to write down. Try a clip with a clear voice, or use the desktop app, which handles tougher audio.</span>' +
      '</div>';
    lastChunks = []; lastText = "";
    outWrap.hidden = false;
    // No real transcript, so hide the download buttons and the Pro nudges.
    $("dlTxt").hidden = true; $("dlMd").hidden = true;
    if (proNext) proNext.hidden = true;
    return;
  }

  setStep("ready");
  setStatus("Done. Your transcript was made entirely on your own machine.");
  // What was made, in numbers: a small, honest moment of "it worked".
  const words = lastText.trim().split(/\s+/).filter(Boolean).length;
  const took = Math.max(1, Math.round((performance.now() - t0) / 1000));
  const chips = [`${words.toLocaleString()} words`];
  if (audioSecs) chips.push(`${fmtClock(audioSecs)} of audio`);
  chips.push(`made in ${took} s`);
  chips.push(backendUsed === "gpu" ? "on your GPU" : "on your CPU");
  V.done.querySelector(".vdt-chips").innerHTML = chips.map((c) => `<span class="vdt-chip">${escapeHtml(c)}</span>`).join("");
  V.done.hidden = false;
  $("dlTxt").hidden = false; $("dlMd").hidden = false;
  outEl.innerHTML = lastChunks.length
    ? lastChunks.map((c) => `<p><span class="ts">[${fmt(c.timestamp[0])}]</span> ${escapeHtml(c.text.trim())}</p>`).join("")
    : `<p>${escapeHtml(lastText)}</p>`;
  outWrap.hidden = false;
  if (proNext) proNext.hidden = false;
}

function plainText() {
  return lastChunks.length
    ? lastChunks.map((c) => `[${fmt(c.timestamp[0])}] ${c.text.trim()}`).join("\n")
    : lastText;
}
function markdown() {
  let md = `# ${lastName} transcript\n\nMade free with VideoDoc in your browser. Own the full app forever (YouTube, playlists, long videos, images): ${GUMROAD}\n\n`;
  md += lastChunks.length
    ? lastChunks.map((c) => `**[${fmt(c.timestamp[0])}]** ${c.text.trim()}`).join("\n\n")
    : lastText;
  return md;
}
function download(name, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1500);
}

$("dlTxt").onclick = () => download(lastName + ".txt", plainText());
$("dlMd").onclick = () => download(lastName + ".md", markdown());

// ---------- drag and drop: answers while you drag, never loses a drop ----------
const big = drop.querySelector(".big");
const BIG_DEFAULT = big ? big.textContent : "";
const hasFiles = (e) => !!e.dataTransfer && Array.from(e.dataTransfer.types || []).includes("Files");
function dragVerdict(dt) {
  // While dragging, a browser shows only the MIME types, never the names.
  const items = Array.from((dt && dt.items) || []).filter((i) => i.kind === "file");
  if (!items.length) return "";
  if (items.length > 1) return "many";
  const t = items[0].type || "";
  if (!t) return "ok";
  return /^(video|audio)\//.test(t) ? "ok" : "bad";
}
function dragState(v) {
  drop.classList.toggle("over", v === "ok" || v === "many");
  drop.classList.toggle("nope", v === "bad");
  if (big) big.textContent = v === "ok" ? "Let go to start"
    : v === "many" ? "One file at a time, please"
    : v === "bad" ? "That is not a video or audio file" : BIG_DEFAULT;
}
let depth = 0;   // enter/leave fire for every child: count, so it never flickers
drop.addEventListener("dragenter", (e) => { e.preventDefault(); depth++; dragState(dragVerdict(e.dataTransfer)); });
drop.addEventListener("dragover", (e) => {
  e.preventDefault();
  e.dataTransfer.dropEffect = dragVerdict(e.dataTransfer) === "bad" ? "none" : "copy";
});
drop.addEventListener("dragleave", () => { if (--depth <= 0) { depth = 0; dragState(""); } });
drop.addEventListener("drop", (e) => {
  e.preventDefault();
  e.stopPropagation();
  depth = 0; dragState("");
  document.documentElement.classList.remove("vdt-drag");
  const files = Array.from((e.dataTransfer && e.dataTransfer.files) || []);
  if (!files.length) return;
  const media = files.filter(isMedia);
  if (!media.length) { refuse(`“${files[0].name}” is not a video or audio file. Try an MP4, MP3, WAV, M4A, or WEBM.`); return; }
  handleFile(media[0]);
});
// Page-wide: a file dragged anywhere lights the box up, and one dropped next to
// it is caught instead of the browser opening it and leaving the page.
window.addEventListener("dragenter", (e) => { if (hasFiles(e)) document.documentElement.classList.add("vdt-drag"); });
window.addEventListener("dragleave", (e) => { if (!e.relatedTarget) document.documentElement.classList.remove("vdt-drag"); });
window.addEventListener("dragover", (e) => {
  if (!hasFiles(e)) return;
  e.preventDefault();
  if (!drop.contains(e.target)) e.dataTransfer.dropEffect = "none";
});
window.addEventListener("drop", (e) => {
  if (!hasFiles(e)) return;
  e.preventDefault();
  document.documentElement.classList.remove("vdt-drag");
  if (!drop.contains(e.target)) setStatus("Drop it inside the box to start.");
});

fileInput.onchange = (e) => { const f = e.target.files[0]; e.target.value = ""; handleFile(f); };
drop.addEventListener("click", () => fileInput.click());
drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); } });

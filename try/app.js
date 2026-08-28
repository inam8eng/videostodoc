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

function setStatus(msg, pct) {
  statusEl.textContent = msg || "";
  if (typeof pct === "number") {
    barWrap.hidden = false;
    barEl.style.width = Math.max(2, Math.round(pct)) + "%";
  }
}

function ensureWorker() {
  if (worker) return worker;
  worker = new Worker("worker.js", { type: "module" });
  worker.onmessage = (e) => {
    const d = e.data;
    if (d.type === "model") {
      prog[d.file] = d.progress;
      const v = Object.values(prog);
      setStatus("Downloading the AI model (one time, then it's cached) ...", v.reduce((a, b) => a + b, 0) / v.length);
    }
    else if (d.type === "status") { barWrap.hidden = true; setStatus(d.message); }
    else if (d.type === "done") { busy = false; renderResult(d.text, d.chunks); }
    else if (d.type === "error") { busy = false; barWrap.hidden = true; setStatus("Something went wrong: " + d.message + ". Try a different file, or a Chrome/Edge browser."); }
  };
  worker.onerror = () => setStatus("The AI engine couldn't start. Check your connection or an ad blocker, and try Chrome or Edge.");
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

async function handleFile(file) {
  if (!file) return;
  if (file.size > 300 * 1024 * 1024) { setStatus("That file is too big for the free browser demo. Try a clip under 300 MB. The desktop app handles the big ones."); return; }
  if (busy) { setStatus("Still working on the previous file, one at a time please ..."); return; }
  busy = true;
  lastName = (file.name || "transcript").replace(/\.[^.]+$/, "");
  outWrap.hidden = true;
  barWrap.hidden = true;
  try {
    const audio = await fileToAudio(file);
    setStatus("Starting the AI on your machine ...");
    ensureWorker().postMessage({ audio }, [audio.buffer]);
  } catch (e) {
    busy = false;
    setStatus("Couldn't read that file. Try an MP4, MP3, WAV, M4A, or WEBM. (" + e.message + ")");
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

function renderResult(text, chunks) {
  lastText = text || "";
  lastChunks = (chunks || []).filter((c) => c && c.text && c.text.trim());
  barWrap.hidden = true;

  const proNext = $("proNext");

  if (!lastText.trim() || looksDegenerate(lastText)) {
    setStatus("");
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

  setStatus("Done. Your transcript was made entirely on your own machine.");
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

fileInput.onchange = (e) => handleFile(e.target.files[0]);
drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); handleFile(e.dataTransfer.files[0]); });
drop.addEventListener("click", () => fileInput.click());
drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); } });

// Runs entirely in the visitor's browser. No upload, no server, $0 compute for us.
// Loads Whisper via transformers.js, tries WebGPU first, falls back to CPU (WASM).
// Imported as a namespace so an optional export (the live-text streamer) can be
// missing without breaking the import itself.
import * as T from "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1";

const { pipeline, env } = T;

// We pull the model from the HF hub (cached by the browser after first run).
env.allowLocalModels = false;
// onnxruntime prints routine placement notes ("Some nodes were not assigned
// to the preferred execution providers") through console.error. Keep the
// console for real problems only.
try { if (env.backends && env.backends.onnx) env.backends.onnx.logLevel = "error"; } catch (e) { /* older runtime */ }
// The same, per model session: the placement note is printed while a session
// is created, before the global level is applied on a first load.
const QUIET = { logSeverityLevel: 3 };

let transcriberPromise = null;
let backend = "cpu";

async function getTranscriber(progress_callback) {
  if (transcriberPromise) return transcriberPromise;
  transcriberPromise = (async () => {
    const hasGPU = typeof navigator !== "undefined" && "gpu" in navigator;
    if (hasGPU) {
      try {
        const t = await pipeline(
          "automatic-speech-recognition",
          "onnx-community/whisper-base",
          { device: "webgpu",
            // fp32, not fp16: on an NVIDIA card (Oct 2026 test) the fp16
            // encoder turned clear speech into one looping line ("I'm going
            // to be a good friend. ...") that the page then reported as "no
            // clear speech". fp32 gave the exact words, in 4 s for 27 s of
            // audio. It is about 40 MB more to download, once.
            dtype: { encoder_model: "fp32", decoder_model_merged: "q4" },
            session_options: QUIET,
            progress_callback }
        );
        backend = "gpu";
        return t;
      } catch (e) {
        postMessage({ type: "status", message: "Your GPU wasn't usable, switching to CPU (slower, still all on your machine) ..." });
      }
    }
    // Reliable CPU/WASM path — works in any modern browser.
    const t = await pipeline(
      "automatic-speech-recognition",
      "Xenova/whisper-base",
      { session_options: QUIET, progress_callback }
    );
    backend = "cpu";
    return t;
  })();
  transcriberPromise.catch(() => { transcriberPromise = null; });
  return transcriberPromise;
}

// The words as they are heard, sent to the page so the visitor sees the
// transcript forming. Purely a nicety: if anything about it fails, the plain
// call below runs exactly as before.
function liveStreamer(transcriber) {
  if (!T.WhisperTextStreamer || !transcriber.tokenizer) return null;
  try {
    return new T.WhisperTextStreamer(transcriber.tokenizer, {
      skip_prompt: true,
      callback_function: (text) => { if (text) postMessage({ type: "partial", text }); },
    });
  } catch (e) {
    return null;
  }
}

self.onmessage = async (e) => {
  const { audio } = e.data;
  try {
    const transcriber = await getTranscriber((p) => {
      if (p.status === "progress" && typeof p.progress === "number") {
        postMessage({ type: "model", file: p.file || "", progress: p.progress });
      } else if (p.status === "ready") {
        postMessage({ type: "status", message: "Model ready. Listening to your file ..." });
      }
    });

    postMessage({ type: "status", message: `Transcribing on your ${backend === "gpu" ? "GPU" : "CPU"} ... longer files take a little longer.` });

    const opts = { chunk_length_s: 30, stride_length_s: 5, return_timestamps: true };
    const streamer = liveStreamer(transcriber);
    let output;
    try {
      output = await transcriber(audio, streamer ? { ...opts, streamer } : opts);
    } catch (err) {
      if (!streamer) throw err;
      postMessage({ type: "partial-reset" });
      output = await transcriber(audio, opts);
    }

    postMessage({ type: "done", text: output.text || "", chunks: output.chunks || [], backend });
  } catch (err) {
    postMessage({ type: "error", message: String((err && err.message) || err) });
  }
};

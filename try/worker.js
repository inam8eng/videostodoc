// Runs entirely in the visitor's browser. No upload, no server, $0 compute for us.
// Loads Whisper via transformers.js, tries WebGPU first, falls back to CPU (WASM).
import { pipeline, env } from "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1";

// We pull the model from the HF hub (cached by the browser after first run).
env.allowLocalModels = false;

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
            dtype: { encoder_model: "fp16", decoder_model_merged: "q4" },
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
      { progress_callback }
    );
    backend = "cpu";
    return t;
  })();
  transcriberPromise.catch(() => { transcriberPromise = null; });
  return transcriberPromise;
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

    const output = await transcriber(audio, {
      chunk_length_s: 30,
      stride_length_s: 5,
      return_timestamps: true,
    });

    postMessage({ type: "done", text: output.text || "", chunks: output.chunks || [], backend });
  } catch (err) {
    postMessage({ type: "error", message: String((err && err.message) || err) });
  }
};

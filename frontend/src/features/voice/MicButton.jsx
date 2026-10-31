const LABEL = { idle: "Tap to start", connecting: "Connecting…", listening: "Listening… tap to send", processing: "Transcribing…" };

/** Tap to start, tap again to send. Presentational: all voice logic is in useWispr. */
export default function MicButton({ state, onStart, onStop }) {
  const busy = state === "connecting" || state === "processing";
  const live = state === "listening";
  return (
    <button
      type="button"
      onClick={live ? onStop : onStart}
      disabled={busy}
      aria-pressed={live}
      aria-label={live ? "Stop and send" : "Start voice command"}
      title={LABEL[state]}
      className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-white shadow disabled:opacity-60 ${live ? "animate-pulse bg-red-600" : "bg-emerald-600 hover:bg-emerald-700"}`}
    >
      <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2z" />
      </svg>
    </button>
  );
}

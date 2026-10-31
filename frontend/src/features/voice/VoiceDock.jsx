import { useCallback, useState } from "react";
import { api, notifyDataChanged } from "../../api";
import ConfirmationCard from "./ConfirmationCard.jsx";
import MicButton from "./MicButton.jsx";
import { useWispr } from "./useWispr.js";

/** Bottom bar on every page: mic + text fallback -> POST /voice/command -> confirmation card -> POST /voice/confirm. */
export default function VoiceDock() {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [outcome, setOutcome] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = useCallback(async (t) => {
    setErr(""); setOutcome(null); setBusy(true);
    try { setResult(await api("/voice/command", { method: "POST", body: { text: t } })); }
    catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }, []);

  const { state, partial, error, start, stop } = useWispr(submit);

  async function decide(accept) {
    setBusy(true);
    try {
      setOutcome(await api("/voice/confirm", { method: "POST", body: { log_id: result.log_id, accept } }));
      if (accept) notifyDataChanged();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  const close = () => { setResult(null); setOutcome(null); };
  const onSubmit = (e) => { e.preventDefault(); if (text.trim()) { submit(text.trim()); setText(""); } };

  return (
    <div className="fixed inset-x-0 bottom-0 border-t border-slate-200 bg-white/95 p-3 backdrop-blur">
      <div className="mx-auto max-w-4xl space-y-2">
        {result && <ConfirmationCard result={result} outcome={outcome} busy={busy} onConfirm={() => decide(true)} onCancel={() => decide(false)} onClose={close} />}
        {(partial || error || err) && (
          <p role="status" className={`text-sm ${error || err ? "text-red-600" : "text-slate-600"}`}>{error || err || `“${partial}”`}</p>
        )}
        <form onSubmit={onSubmit} className="flex items-center gap-2">
          <MicButton state={state} onStart={start} onStop={stop} />
          <input
            className="input" value={text} onChange={(e) => setText(e.target.value)} aria-label="Type a command"
            placeholder={state === "listening" ? "Listening…" : "Type or tap the mic: “What if I cut dining out by 30%?”"}
          />
          <button className="btn" type="submit" disabled={busy || !text.trim()}>Send</button>
        </form>
      </div>
    </div>
  );
}

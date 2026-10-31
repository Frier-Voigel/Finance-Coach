import { FOOTER } from "../../api";

/** Shows what was understood. Nothing is written until the user presses Confirm. */
export default function ConfirmationCard({ result, outcome, busy, onConfirm, onCancel, onClose }) {
  if (result.blocked) {
    return (
      <div className="card border-amber-300 bg-amber-50 text-sm" role="alert">
        <p>{result.reply}</p>
        <button className="btn-ghost mt-2" onClick={onClose}>Close</button>
      </div>
    );
  }
  const writes = result.intents.some((i) => i.writes);
  return (
    <div className="card text-sm" role="region" aria-label="Confirm voice command">
      <p className="mb-2 text-xs text-slate-500">You said: “{result.transcript}”</p>
      <ul className="space-y-2">
        {result.intents.map((i) => (
          <li key={i.index}>
            <span className="font-medium">{i.summary}</span>
            {i.answer && <p className={i.answer.ok ? "text-slate-700" : "text-red-600"}>{i.answer.message}</p>}
          </li>
        ))}
      </ul>
      {outcome ? (
        <div className="mt-3">
          {outcome.confirmed
            ? outcome.results.map((r, i) => <p key={i} className={r.ok ? "text-emerald-700" : "text-red-600"}>{r.message}</p>)
            : <p className="text-slate-600">Cancelled. Nothing was changed.</p>}
          <button className="btn-ghost mt-2" onClick={onClose}>Close</button>
        </div>
      ) : (
        <div className="mt-3 flex gap-2">
          {writes && <button className="btn" disabled={busy} onClick={onConfirm}>Confirm</button>}
          <button className="btn-ghost" disabled={busy} onClick={writes ? onCancel : onClose}>{writes ? "Cancel" : "Close"}</button>
        </div>
      )}
      <p className="mt-2 text-xs text-slate-500">{FOOTER}</p>
    </div>
  );
}

import { useEffect } from "react";
import { FOOTER, api, useLoader } from "../../api.js";

const TRIGGER = { upload: "Statement uploaded", sms: "SMS pasted", correction: "Category corrected", voice: "Voice command",
  profile: "Profile updated", goal: "Goal changed", subscription: "Subscription updated" };
const CHIP = { high: "bg-red-100 text-red-800", medium: "bg-amber-100 text-amber-800", good: "bg-emerald-100 text-emerald-800", info: "bg-slate-100 text-slate-700" };

function group(rows) {
  const by = new Map();
  rows.forEach((r) => by.set(r.batch_id, [...(by.get(r.batch_id) || []), r]));
  return [...by.values()];
}

export default function ChangesPage() {
  const { data, error, loading, reload } = useLoader(() => api("/changes", { params: { limit: 60 } }));
  useEffect(() => { window.addEventListener("changes-updated", reload); return () => window.removeEventListener("changes-updated", reload); }, [reload]);
  if (error) return <p className="text-red-600">{error.message}</p>;
  if (loading || !data) return <p>Loading…</p>;

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">What changed</h1>
      {data.length === 0 && <p className="text-slate-600">Nothing yet. Upload a statement or correct a category and the plan's movement shows up here.</p>}
      {group(data).map((batch) => (
        <div key={batch[0].batch_id} className="card space-y-2">
          <p className="text-xs text-slate-500">{TRIGGER[batch[0].trigger] || batch[0].trigger} · {new Date(batch[0].created_at + "Z").toLocaleString("en-IN")}</p>
          {batch.map((e) => (
            <p key={e.id}><span className={`mr-2 rounded px-1.5 py-0.5 text-xs ${CHIP[e.severity] || CHIP.info}`}>{e.severity}</span>{e.headline}</p>
          ))}
        </div>
      ))}
      <p className="text-xs text-slate-500">{FOOTER}</p>
    </div>
  );
}

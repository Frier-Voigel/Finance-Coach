import { api, useLoader } from "../../api";

const BADGE = { high: "bg-red-100 text-red-800", medium: "bg-amber-100 text-amber-800" };

export default function NudgesPage() {
  const { data, error, loading, reload } = useLoader(() => api("/nudges"));
  if (error) return <p className="text-red-600">{error.message}</p>;
  if (loading || !data) return <p>Loading…</p>;
  const dismiss = (id) => api(`/nudges/${id}/dismiss`, { method: "POST" }).then(reload);

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Nudges</h1>
      {data.length === 0 && <p className="text-slate-600">All quiet: spending is in line with your usual pace.</p>}
      {data.map((n) => (
        <div key={n.id} className="card flex items-start justify-between gap-3">
          <p><span className={`mr-2 rounded px-1.5 py-0.5 text-xs ${BADGE[n.severity] || BADGE.medium}`}>{n.severity}</span>{n.message}</p>
          <button className="btn-ghost shrink-0" onClick={() => dismiss(n.id)}>Dismiss</button>
        </div>
      ))}
    </div>
  );
}

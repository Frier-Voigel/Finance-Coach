import { FOOTER, api, inr, notifyDataChanged, useLoader } from "../../api.js";

const STATUS_BADGE = {
  active: "bg-emerald-100 text-emerald-800",
  changed: "bg-amber-100 text-amber-800",
  unused: "bg-red-100 text-red-800",
  cancelled: "bg-slate-100 text-slate-600",
};

export default function SubscriptionsPage() {
  const { data: subs, error, loading, reload } = useLoader(() => api("/recurring"));

  async function handleMarkUnused(id) {
    try {
      await api(`/recurring/${id}/mark-unused`, { method: "POST" });
      reload();
      notifyDataChanged();
    } catch (err) {
      alert(`Could not mark unused: ${err.message}`);
    }
  }

  if (loading) return <p className="animate-pulse text-slate-400">Loading subscriptions…</p>;
  if (error) return <p className="text-red-600">{error.message}</p>;

  const monthlyTotal = subs
    ?.filter((s) => s.status === "active" || s.status === "changed")
    .reduce((sum, s) => {
      const amt = s.amount;
      if (s.cadence === "yearly") return sum + Math.round(amt / 12);
      if (s.cadence === "weekly") return sum + Math.round((amt * 52) / 12);
      return sum + amt;
    }, 0) ?? 0;

  const alerts = subs?.filter((s) => s.status === "changed" || s.status === "unused") ?? [];

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Recurring & Subscriptions</h1>
        <p className="text-sm text-slate-500">
          Detected active subscriptions and scheduled recurring payments.
        </p>
      </div>

      {/* Overview Stat */}
      <div className="card flex items-center justify-between">
        <div>
          <p className="text-xs text-slate-500">Estimated Monthly Cost</p>
          <p className="text-2xl font-bold text-emerald-700">{inr(monthlyTotal)}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500">Tracked Services</p>
          <p className="text-lg font-semibold text-slate-700">{subs?.length ?? 0}</p>
        </div>
      </div>

      {/* Subscription Alerts */}
      {alerts.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 space-y-2">
          <h2 className="text-sm font-semibold text-amber-900">⚠️ Subscription Alerts</h2>
          {alerts.map((a) => (
            <div key={a.id} className="text-xs text-amber-800 flex justify-between items-center">
              <span>
                <strong>{a.merchant}</strong>: {a.status === "changed" ? "Price change detected vs usual amount." : "Flagged as unused recently."}
              </span>
              <span className={`rounded px-1.5 py-0.5 text-[10px] ${STATUS_BADGE[a.status]}`}>
                {a.status}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Subscriptions List */}
      <div className="card space-y-3">
        <h2 className="font-medium text-slate-800">All Subscriptions</h2>
        {(!subs || subs.length === 0) && (
          <p className="text-sm text-slate-400">No recurring payments detected yet.</p>
        )}
        <div className="space-y-2">
          {subs?.map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between rounded-lg border border-slate-100 p-3 hover:bg-slate-50 transition-colors"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-slate-800">{s.merchant}</span>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_BADGE[s.status] || "bg-slate-100 text-slate-600"}`}>
                    {s.status}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  {inr(s.amount)} · billed {s.cadence}
                  {s.last_seen && ` · last seen ${s.last_seen}`}
                </p>
              </div>

              <div className="flex items-center gap-2">
                {s.status !== "unused" && (
                  <button
                    onClick={() => handleMarkUnused(s.id)}
                    className="text-xs text-slate-500 hover:text-red-600 transition-colors"
                  >
                    Mark unused
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <p className="mt-6 text-center text-xs text-slate-400">{FOOTER}</p>
    </section>
  );
}

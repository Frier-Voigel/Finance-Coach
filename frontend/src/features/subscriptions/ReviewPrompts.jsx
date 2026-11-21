import { useState } from "react";
import { FOOTER, api, inr, notifyDataChanged, useLoader } from "../../api.js";

const pct = (n) => (n == null ? "" : ` (${n}% of income)`);

/** "Subscription check-in": cost as a share of income, overlap flags and a one-tap "still using this?". */
export default function ReviewPrompts() {
  const { data, error, loading, reload } = useLoader(() => api("/subscriptions/review"));
  const [busy, setBusy] = useState("");

  async function answer(item, choice) {
    setBusy(item.merchant_hash);
    try {
      await api(`/subscriptions/review/${item.merchant_hash}/answer`, { method: "POST", body: { answer: choice } });
      notifyDataChanged(); // refreshes the subscriptions list below and this card
    } catch (e) {
      window.alert(`Could not save your answer: ${e.message}`);
    } finally {
      setBusy("");
    }
  }

  if (loading || error || !data || data.items.length === 0) return null; // never get in the way of the page
  const ask = data.items.filter((i) => i.ask);

  return (
    <section className="card space-y-3" aria-label="Subscription check-in">
      <div>
        <h2 className="text-base font-semibold">Subscription check-in</h2>
        <p className="text-sm text-slate-600">{data.disclaimer}</p>
      </div>

      <p className="text-sm">
        Your subscriptions cost <strong>{inr(data.total_yearly_cost)}</strong> a year{pct(data.total_pct_of_income)}.
        {data.potential_yearly_savings > 0 && <> You've told us <strong>{inr(data.potential_yearly_savings)}</strong> a year of that isn't being used.</>}
      </p>

      {data.overlaps.map((o) => (
        <p key={o.group} className="rounded-lg bg-amber-50 p-2 text-sm text-amber-900">
          <strong>Overlap:</strong> {o.message} Together {inr(o.yearly_cost)} a year.
        </p>
      ))}

      {ask.length === 0 && <p className="text-sm text-slate-600">Nothing to review right now. We'll ask again in a few months.</p>}
      {ask.map((i) => (
        <div key={i.merchant_hash} className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-2">
          <div className="min-w-0">
            <p className="text-sm font-medium">Still using {i.merchant}?</p>
            <p className="text-xs text-slate-500">
              {inr(i.amount)} {i.cadence} · {inr(i.yearly_cost)} a year{pct(i.pct_of_income)}
              {i.reasons.length > 0 && <> · {i.reasons.filter((r) => !r.includes("of your income")).join(" · ")}</>}
            </p>
          </div>
          <div className="flex gap-2">
            <button className="btn" disabled={busy === i.merchant_hash} onClick={() => answer(i, "using")}>Yes, still using</button>
            <button className="btn-ghost" disabled={busy === i.merchant_hash} onClick={() => answer(i, "not_using")}>Not really</button>
          </div>
        </div>
      ))}
      <p className="text-xs text-slate-500">{FOOTER}</p>
    </section>
  );
}

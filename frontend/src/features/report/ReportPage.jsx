import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BASE, api, inr, monthYear, useLoader } from "../../api";

const thisMonth = () => new Date().toISOString().slice(0, 7);

export default function ReportPage() {
  const [month, setMonth] = useState(import.meta.env.VITE_AS_OF?.slice(0, 7) || thisMonth());
  const { data: r, error, loading } = useLoader(() => api(`/reports/${month}`), [month]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-xl font-semibold">Monthly review</h1>
        <div className="flex items-end gap-3">
          <div><label className="label" htmlFor="m">Month</label><input id="m" type="month" className="input" value={month} onChange={(e) => e.target.value && setMonth(e.target.value)} /></div>
          <a className="btn-ghost" href={`${BASE}/reports/${month}?format=html`} target="_blank" rel="noreferrer">Open printable HTML</a>
        </div>
      </div>
      {error && <p role="alert" className="text-red-600">{error.message}</p>}
      {loading && !r && <p>Loading…</p>}
      {r && (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            {[["Income", inr(r.income)], ["Spent", inr(r.total_spent)], ["Savings rate", `${r.savings_rate_pct}%`], ["vs last month", `${r.vs_last_month >= 0 ? "+" : "−"}${inr(Math.abs(r.vs_last_month))}`]].map(([k, v]) => (
              <div key={k} className="card"><p className="text-xs text-slate-500">{k}</p><p className="text-lg font-semibold">{v}</p></div>
            ))}
          </div>
          <div className="card h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={r.by_category.map((c) => ({ name: c.category, "This month": c.spent, "Last month": c.last_month }))}>
                <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip formatter={(v) => inr(v)} /><Legend />
                <Bar dataKey="Last month" fill="#94a3b8" /><Bar dataKey="This month" fill="#059669" /></BarChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <h2 className="mb-2 font-medium">Subscriptions · {inr(r.subscriptions_monthly_total)}/month</h2>
            {r.subscriptions.length === 0 && <p className="text-sm text-slate-600">None detected yet.</p>}
            <ul className="space-y-1 text-sm">
              {r.subscriptions.map((s, i) => <li key={`${s.merchant}-${i}`}>{s.merchant}: {inr(s.amount)} {s.cadence}{s.status !== "active" && <span className="ml-1 rounded bg-amber-100 px-1.5 text-xs text-amber-800">{s.status}</span>}</li>)}
            </ul>
          </div>
          <div className="card">
            <h2 className="mb-2 font-medium">Goals</h2>
            {r.goals.length === 0 && <p className="text-sm text-slate-600">No goals yet.</p>}
            <ul className="space-y-1 text-sm">
              {r.goals.map((g, i) => <li key={`${g.name}-${i}`}>{g.name}: {g.projected_date ? monthYear(g.projected_date) : "not reachable at the current surplus"}{g.on_track ? " (on track)" : ""}</li>)}
            </ul>
          </div>
          <div className="card">
            <h2 className="mb-2 font-medium">Nudges</h2>
            {r.nudges.length === 0 && <p className="text-sm text-slate-600">None for this month.</p>}
            <ul className="list-disc space-y-1 pl-5 text-sm">{r.nudges.map((n, i) => <li key={i}>{n.message}</li>)}</ul>
          </div>
          <p className="text-xs text-slate-500">{r.footer}</p>
        </>
      )}
    </div>
  );
}

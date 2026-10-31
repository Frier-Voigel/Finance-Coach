import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { FOOTER, api, inr, monthYear, useLoader } from "../../api";

export default function WhatIfPage() {
  const { data: plan, error } = useLoader(() => api("/plan"));
  const [kind, setKind] = useState("category_pct");
  const [target, setTarget] = useState("");
  const [value, setValue] = useState(-30);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");

  const categories = plan ? Object.keys(plan.variable) : [];
  const fixed = plan ? Object.keys(plan.profile.fixed_costs) : [];
  const options = kind === "fixed_abs" ? fixed : kind === "category_pct" ? categories : [];

  useEffect(() => { setTarget(options[0] || ""); setValue(kind === "category_pct" ? -30 : 0); }, [kind, plan]); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-run the simulation shortly after any control changes.
  useEffect(() => {
    if (!plan || (kind !== "income_abs" && !target)) return undefined;
    const body = kind === "category_pct" ? { kind, category: target, pct: Number(value) }
      : kind === "fixed_abs" ? { kind, name: target, delta: Number(value) || 0 } : { kind, delta: Number(value) || 0 };
    const t = setTimeout(() => api("/whatif", { method: "POST", body }).then((r) => { setResult(r); setErr(""); }, (e) => setErr(e.message)), 250);
    return () => clearTimeout(t);
  }, [plan, kind, target, value]);

  if (error) return <p className="text-red-600">{error.message}</p>;
  if (!plan) return <p>Loading…</p>;

  const chart = result?.before.map((b, i) => ({ name: b.name, Before: b.months_needed, After: result.after[i].months_needed }));

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">What if…</h1>
      <div className="card grid gap-3 sm:grid-cols-3">
        <div>
          <label className="label" htmlFor="kind">Change</label>
          <select id="kind" className="input" value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="category_pct">Spending in a category (%)</option>
            <option value="fixed_abs">A fixed cost (₹/month)</option>
            <option value="income_abs">Income (₹/month)</option>
          </select>
        </div>
        {kind !== "income_abs" && (
          <div>
            <label className="label" htmlFor="target">{kind === "fixed_abs" ? "Cost" : "Category"}</label>
            <select id="target" className="input" value={target} onChange={(e) => setTarget(e.target.value)}>
              {options.map((o) => <option key={o}>{o}</option>)}
            </select>
          </div>
        )}
        <div>
          <label className="label" htmlFor="val">{kind === "category_pct" ? `Change: ${value}%` : "Change (₹)"}</label>
          {kind === "category_pct"
            ? <input id="val" className="w-full" type="range" min="-100" max="100" step="5" value={value} onChange={(e) => setValue(e.target.value)} />
            : <input id="val" className="input" type="number" value={value} onChange={(e) => setValue(e.target.value)} />}
        </div>
      </div>
      {err && <p role="alert" className="text-red-600">{err}</p>}
      {result && (
        <>
          <div className="card">
            <p>Monthly surplus: <strong>{inr(result.surplus_before)}</strong> → <strong>{inr(result.surplus_after)}</strong>
              <span className={result.surplus_delta >= 0 ? "ml-2 text-emerald-700" : "ml-2 text-red-600"}>
                ({result.surplus_delta >= 0 ? "+" : ""}{inr(result.surplus_delta)})</span></p>
            <ul className="mt-2 space-y-1 text-sm">
              {result.before.map((b, i) => {
                const a = result.after[i];
                return <li key={`${a.name}-${i}`}>{a.name}: {monthYear(b.projected_date)} → <strong>{monthYear(a.projected_date)}</strong>
                  {a.months_saved ? <span className="text-slate-500"> ({Math.abs(a.months_saved)} month{Math.abs(a.months_saved) === 1 ? "" : "s"} {a.months_saved > 0 ? "earlier" : "later"})</span> : null}</li>;
              })}
            </ul>
          </div>
          {chart.length > 0 && (
            <div className="card h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chart}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis allowDecimals={false} label={{ value: "months", angle: -90, position: "insideLeft" }} /><Tooltip /><Legend />
                  <Bar dataKey="Before" fill="#94a3b8" /><Bar dataKey="After" fill="#059669" /></BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
      <p className="text-xs text-slate-500">{FOOTER}</p>
    </div>
  );
}

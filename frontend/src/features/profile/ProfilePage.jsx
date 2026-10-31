import { useEffect, useState } from "react";
import { api, notifyDataChanged, useLoader } from "../../api";

const toInt = (v) => Math.max(0, parseInt(v, 10) || 0);

export default function ProfilePage() {
  const { data, error, loading } = useLoader(() => api("/profile"));
  const [form, setForm] = useState(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (data) setForm({ ...data, rows: Object.entries(data.fixed_costs).map(([name, amount]) => ({ name, amount })) });
  }, [data]);

  if (error) return <p className="text-red-600">{error.message}</p>;
  if (loading || !form) return <p>Loading…</p>;

  const set = (k, v) => setForm({ ...form, [k]: v });
  const setRow = (i, patch) => set("rows", form.rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  async function save(e) {
    e.preventDefault();
    const fixed_costs = Object.fromEntries(form.rows.filter((r) => r.name.trim()).map((r) => [r.name.trim().toLowerCase(), toInt(r.amount)]));
    try {
      await api("/profile", { method: "PUT", body: {
        monthly_income: toInt(form.monthly_income), fixed_costs,
        emergency_fund_current: toInt(form.emergency_fund_current), emergency_fund_target: toInt(form.emergency_fund_target) } });
      setMsg("Saved."); notifyDataChanged();
    } catch (err) { setMsg(err.message); }
  }

  return (
    <form onSubmit={save} className="card space-y-4">
      <h1 className="text-xl font-semibold">Your profile</h1>
      <div>
        <label className="label" htmlFor="income">Monthly income (₹)</label>
        <input id="income" className="input" type="number" min="0" value={form.monthly_income} onChange={(e) => set("monthly_income", e.target.value)} />
      </div>
      <div>
        <span className="label">Fixed monthly costs</span>
        {form.rows.map((r, i) => (
          <div key={i} className="mb-2 flex gap-2">
            <input aria-label="Cost name" className="input" placeholder="rent" value={r.name} onChange={(e) => setRow(i, { name: e.target.value })} />
            <input aria-label="Cost amount" className="input" type="number" min="0" value={r.amount} onChange={(e) => setRow(i, { amount: e.target.value })} />
            <button type="button" className="btn-ghost" onClick={() => set("rows", form.rows.filter((_, j) => j !== i))}>Remove</button>
          </div>
        ))}
        <button type="button" className="btn-ghost" onClick={() => set("rows", [...form.rows, { name: "", amount: 0 }])}>Add cost</button>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label" htmlFor="efc">Emergency fund saved (₹)</label>
          <input id="efc" className="input" type="number" min="0" value={form.emergency_fund_current} onChange={(e) => set("emergency_fund_current", e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="eft">Emergency fund target (₹)</label>
          <input id="eft" className="input" type="number" min="0" value={form.emergency_fund_target} onChange={(e) => set("emergency_fund_target", e.target.value)} />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <button className="btn" type="submit">Save profile</button>
        <span role="status" className="text-sm text-slate-600">{msg}</span>
      </div>
    </form>
  );
}

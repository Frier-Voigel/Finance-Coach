import { useState } from "react";
import { api, inr, monthYear, notifyDataChanged, useLoader } from "../../api";

function Projection({ p }) {
  if (!p) return null;
  return (
    <p className="text-sm text-slate-600">
      {p.projected_date ? `Projected ${monthYear(p.projected_date)}` : "Not reachable at the current surplus"}
      {p.target_date && <> · target {monthYear(p.target_date)}</>}
      {p.required_monthly != null && <> · needs {inr(p.required_monthly)}/month to hit the target</>}
      <span className={`ml-2 rounded px-1.5 py-0.5 text-xs ${p.on_track ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
        {p.on_track ? "on track" : "behind"}
      </span>
    </p>
  );
}

const EMPTY = { name: "", target_amount: "", current_amount: "", target_date: "" };

export default function GoalsPage() {
  const { data, error, loading, reload } = useLoader(() => api("/goals"));
  const [form, setForm] = useState(EMPTY);
  const [msg, setMsg] = useState("");

  async function add(e) {
    e.preventDefault();
    try {
      await api("/goals", { method: "POST", body: {
        name: form.name, target_amount: parseInt(form.target_amount, 10),
        current_amount: parseInt(form.current_amount, 10) || 0, target_date: form.target_date || null } });
      setForm(EMPTY); setMsg(""); reload(); notifyDataChanged();
    } catch (err) { setMsg(err.message); }
  }

  async function saved(goal) {
    const v = window.prompt(`Amount saved so far for "${goal.name}" (₹)`, goal.current_amount);
    if (v === null) return;
    try { await api(`/goals/${goal.id}`, { method: "PATCH", body: { current_amount: parseInt(v, 10) || 0 } }); reload(); notifyDataChanged(); }
    catch (err) { setMsg(err.message); }
  }

  if (error) return <p className="text-red-600">{error.message}</p>;
  if (loading || !data) return <p>Loading…</p>;
  const f = (k) => ({ value: form[k], onChange: (e) => setForm({ ...form, [k]: e.target.value }) });

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Goals</h1>
      <p className="text-sm text-slate-600">Monthly surplus used for planning: <strong>{inr(data.surplus)}</strong>. Goals are funded in priority order.</p>
      {data.emergency_fund && (
        <div className="card"><h2 className="font-medium">{data.emergency_fund.name} (from your profile)</h2><Projection p={data.emergency_fund} /></div>
      )}
      {data.goals.map((g) => (
        <div key={g.id} className="card flex items-start justify-between gap-3">
          <div>
            <h2 className="font-medium">{g.name}</h2>
            <p className="text-sm">{inr(g.current_amount)} of {inr(g.target_amount)} · priority {g.priority}</p>
            <Projection p={g.projection} />
          </div>
          <button className="btn-ghost" onClick={() => saved(g)}>Update saved</button>
        </div>
      ))}
      {data.goals.length === 0 && !data.emergency_fund && <p className="text-slate-600">No goals yet. Add one below or say it out loud.</p>}
      <form onSubmit={add} className="card grid gap-3 sm:grid-cols-4">
        <div className="sm:col-span-4 font-medium">Add a goal</div>
        <div><label className="label" htmlFor="gn">Name</label><input id="gn" required className="input" {...f("name")} /></div>
        <div><label className="label" htmlFor="gt">Target (₹)</label><input id="gt" required min="1" type="number" className="input" {...f("target_amount")} /></div>
        <div><label className="label" htmlFor="gc">Saved so far (₹)</label><input id="gc" min="0" type="number" className="input" {...f("current_amount")} /></div>
        <div><label className="label" htmlFor="gd">Target date</label><input id="gd" type="date" className="input" {...f("target_date")} /></div>
        <div className="sm:col-span-4 flex items-center gap-3"><button className="btn" type="submit">Add goal</button><span role="alert" className="text-sm text-red-600">{msg}</span></div>
      </form>
    </div>
  );
}

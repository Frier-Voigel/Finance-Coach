import { useState } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, useLoader } from "../../api";

/** Proof of the learning loop: accuracy on labelled synthetic data before and after the user corrects merchants. */
export default function AccuracyPage() {
  const [withAi, setWithAi] = useState(false);
  const { data, error, loading } = useLoader(() => api("/categorize/accuracy", { params: withAi ? { llm: "true" } : {} }), [withAi]);

  if (error) return <p className="text-red-600">{error.message}</p>;
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Does it learn from corrections?</h1>
      <p className="text-sm text-slate-600">
        {data ? `${data.total} synthetic transactions` : "Synthetic transactions"} whose true categories are known, including merchants the built-in list has
        never seen. Each correction creates a rule, exactly as when you change a category on the Transactions page.
      </p>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={withAi} onChange={(e) => setWithAi(e.target.checked)} />
        Also ask Gemini (uses your API key; sends merchant names only)
      </label>
      {loading || !data ? <p>Measuring…</p> : (
        <>
          {withAi && !data.llm_used && <p role="alert" className="text-amber-700">No Gemini key is set on the server, so the AI stages are skipped.</p>}
          <div className="card h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.stages} margin={{ top: 16 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="stage" tick={{ fontSize: 11 }} interval={0} />
                <YAxis domain={[0, 100]} unit="%" />
                <Tooltip formatter={(v) => `${v}%`} />
                <Bar dataKey="accuracy" fill="#059669"><LabelList dataKey="accuracy" position="top" formatter={(v) => `${v}%`} /></Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <table className="card w-full text-sm">
            <thead><tr className="text-left"><th>Stage</th><th>Accuracy</th><th>Notes</th></tr></thead>
            <tbody>
              {data.stages.map((s) => (
                <tr key={s.stage}><td>{s.stage}</td><td>{s.accuracy}%</td>
                  <td className="text-slate-500">{s.ai_answered != null ? `Gemini answered ${s.ai_answered} transactions` : ""}</td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      <p className="text-xs text-slate-500">Measured on synthetic data, so treat it as a demonstration of the learning loop, not a promise about your own statements.</p>
    </div>
  );
}

import { useState } from "react";
import { FOOTER, api, inr, notifyDataChanged, useLoader } from "../../api.js";

const DEFAULT_CATEGORIES = [
  "Food",
  "Groceries",
  "Transport",
  "Shopping",
  "Entertainment",
  "Bills",
  "Health",
  "Education",
  "Travel",
  "Transfers",
  "Salary",
  "Income",
  "ATM",
  "Other",
];

export default function TransactionsPage() {
  const { data: transactions, error, loading, reload } = useLoader(() => api("/transactions"));
  const [editingId, setEditingId] = useState(null);
  const [newCategory, setNewCategory] = useState("");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState(null);

  async function handleSaveCategory(id) {
    if (!newCategory.trim()) return;
    setSaving(true);
    try {
      const res = await api(`/transactions/${id}`, {
        method: "PATCH",
        body: { category: newCategory },
      });
      setEditingId(null);
      setNewCategory("");
      if (res.rule_created) {
        setToast(`Rule learned: "${res.transaction.merchant}" → ${res.transaction.category}. Updated ${res.updated} transaction(s).`);
      } else {
        setToast(`Updated category to ${res.transaction.category}.`);
      }
      setTimeout(() => setToast(null), 5000);
      reload();
      notifyDataChanged();
    } catch (err) {
      alert(`Failed to update category: ${err.message}`);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="animate-pulse text-slate-400">Loading transactions…</p>;
  if (error) return <p className="text-red-600">{error.message}</p>;

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Transactions</h1>
          <p className="text-sm text-slate-500">
            Review parsed transactions. Edit any category to teach the categorization engine.
          </p>
        </div>
      </div>

      {toast && (
        <div className="rounded-lg bg-emerald-100 p-3 text-sm text-emerald-900 shadow-sm border border-emerald-300">
          ✨ {toast}
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold text-slate-600">
            <tr>
              <th className="py-2.5 px-3">Date</th>
              <th className="py-2.5 px-3">Description</th>
              <th className="py-2.5 px-3">Category</th>
              <th className="py-2.5 px-3 text-right">Amount</th>
              <th className="py-2.5 px-3 text-center">Source</th>
              <th className="py-2.5 px-3 text-center">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(!transactions || transactions.length === 0) && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-400">
                  No transactions found. Upload a statement or run the seed script!
                </td>
              </tr>
            )}
            {transactions?.map((t) => (
              <tr key={t.id} className="hover:bg-slate-50/75">
                <td className="py-2 px-3 text-xs text-slate-500 whitespace-nowrap">{t.date}</td>
                <td className="py-2 px-3 font-medium text-slate-800">
                  {t.description}
                  {t.merchant && t.merchant !== t.description && (
                    <span className="block text-xs text-slate-400 font-normal">Merchant: {t.merchant}</span>
                  )}
                </td>
                <td className="py-2 px-3">
                  {editingId === t.id ? (
                    <div className="flex items-center gap-1">
                      <input
                        list="categories"
                        className="rounded border px-2 py-0.5 text-xs w-28"
                        value={newCategory}
                        onChange={(e) => setNewCategory(e.target.value)}
                        placeholder="Category"
                        autoFocus
                      />
                      <datalist id="categories">
                        {DEFAULT_CATEGORIES.map((c) => (
                          <option key={c} value={c} />
                        ))}
                      </datalist>
                      <button
                        onClick={() => handleSaveCategory(t.id)}
                        disabled={saving}
                        className="rounded bg-emerald-600 px-2 py-0.5 text-xs text-white hover:bg-emerald-700"
                      >
                        ✓
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="rounded bg-slate-200 px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-300"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <span
                      onClick={() => {
                        setEditingId(t.id);
                        setNewCategory(t.category || "");
                      }}
                      className="cursor-pointer rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-700 hover:bg-slate-200 inline-flex items-center gap-1"
                      title="Click to edit category"
                    >
                      {t.category || "Uncategorised"}
                      <span className="text-[10px] text-slate-400">✎</span>
                    </span>
                  )}
                </td>
                <td className={`py-2 px-3 text-right font-medium whitespace-nowrap ${t.direction === "credit" ? "text-emerald-700" : "text-slate-800"}`}>
                  {t.direction === "credit" ? "+" : "−"}{inr(t.amount)}
                </td>
                <td className="py-2 px-3 text-center">
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-500 uppercase">
                    {t.source}
                  </span>
                </td>
                <td className="py-2 px-3 text-center">
                  <button
                    onClick={() => {
                      setEditingId(t.id);
                      setNewCategory(t.category || "");
                    }}
                    className="text-xs text-emerald-600 hover:underline"
                  >
                    Edit
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-6 text-center text-xs text-slate-400">{FOOTER}</p>
    </section>
  );
}

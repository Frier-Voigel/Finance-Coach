import { useState } from "react";
import { BASE, FOOTER, notifyDataChanged } from "../../api.js";

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [smsText, setSmsText] = useState("");
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function handleFileUpload(e) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setStatus("");
    setError("");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${BASE}/ingest/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Upload failed");
      setStatus(`Success! Parsed ${data.parsed ?? 0} transactions from ${data.filename || file.name}.`);
      setFile(null);
      notifyDataChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleSmsSubmit(e) {
    e.preventDefault();
    if (!smsText.trim()) return;
    setUploading(true);
    setStatus("");
    setError("");

    try {
      const res = await fetch(`${BASE}/ingest/sms`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: smsText }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "SMS parsing failed");
      setStatus(`Success! Parsed ${data.parsed ?? 0} transactions from SMS text.`);
      setSmsText("");
      notifyDataChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Upload Statements</h1>
        <p className="text-sm text-slate-500">
          Ingest your bank statements (CSV or PDF) or paste transactional SMS alerts.
        </p>
      </div>

      {status && (
        <div className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800 border border-emerald-200">
          {status}
        </div>
      )}
      {error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700 border border-red-200">
          {error}
        </div>
      )}

      {/* CSV / PDF Upload Card */}
      <div className="card space-y-4">
        <h2 className="font-medium text-slate-800">1. Bank Statement File (CSV / PDF)</h2>
        <form onSubmit={handleFileUpload} className="space-y-3">
          <div>
            <label className="label" htmlFor="file-input">Select Statement File</label>
            <input
              id="file-input"
              type="file"
              accept=".csv,.pdf"
              onChange={(e) => setFile(e.target.files[0] || null)}
              className="input text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-emerald-50 file:px-3 file:py-1 file:text-sm file:font-medium file:text-emerald-700 hover:file:bg-emerald-100"
            />
          </div>
          <button
            type="submit"
            disabled={uploading || !file}
            className="btn"
          >
            {uploading ? "Uploading & Parsing…" : "Upload Statement"}
          </button>
        </form>
      </div>

      {/* SMS Ingest Card */}
      <div className="card space-y-4">
        <h2 className="font-medium text-slate-800">2. Transaction SMS Parser</h2>
        <form onSubmit={handleSmsSubmit} className="space-y-3">
          <div>
            <label className="label" htmlFor="sms-input">Paste Bank SMS text</label>
            <textarea
              id="sms-input"
              rows={4}
              placeholder="e.g. INR 450 debited from A/c XX1234 on 15-10-2026 to Swiggy. Avl Bal: INR 45200. -HDFC Bank"
              value={smsText}
              onChange={(e) => setSmsText(e.target.value)}
              className="input font-mono text-xs"
            />
          </div>
          <button
            type="submit"
            disabled={uploading || !smsText.trim()}
            className="btn"
          >
            {uploading ? "Parsing SMS…" : "Parse SMS"}
          </button>
        </form>
      </div>

      <p className="mt-6 text-center text-xs text-slate-400">{FOOTER}</p>
    </section>
  );
}

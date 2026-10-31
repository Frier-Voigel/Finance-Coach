import { useCallback, useEffect, useState } from "react";

export const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const AS_OF = import.meta.env.VITE_AS_OF || "";

/** fetch wrapper: JSON in/out, errors shaped {error, message} from the backend become Error(message). */
export async function api(path, { method = "GET", body, params = {} } = {}) {
  const q = new URLSearchParams({ ...(AS_OF ? { as_of: AS_OF } : {}), ...params }).toString();
  const res = await fetch(`${BASE}${path}${q ? `?${q}` : ""}`, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw Object.assign(new Error(data?.message || res.statusText), { code: data?.error, status: res.status });
  return data;
}

/** Tell every page to reload (called after a voice command changed data). */
export const notifyDataChanged = () => window.dispatchEvent(new Event("data-changed"));

/** Load data on mount and whenever the app signals a change. */
export function useLoader(fn, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(() => {
    setState((s) => ({ ...s, loading: true }));
    fn().then((data) => setState({ data, error: null, loading: false }), (error) => setState({ data: null, error, loading: false }));
  }, deps);
  useEffect(() => {
    load();
    window.addEventListener("data-changed", load);
    return () => window.removeEventListener("data-changed", load);
  }, [load]);
  return { ...state, reload: load };
}

export const inr = (n) => (n == null ? "–" : `₹${Number(n).toLocaleString("en-IN")}`);
export const monthYear = (d) => (d ? new Date(d).toLocaleDateString("en-IN", { month: "short", year: "numeric" }) : "Not reachable yet");
export const FOOTER = "Educational modelling only, not financial advice.";

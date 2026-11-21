import { useEffect, useRef } from "react";
import { api } from "../../api.js";
import { useToast } from "../../components/Toast";

/** Invisible. Polls GET /changes; when new events appear (after an upload, a correction, a voice command...) it toasts them. */
export default function ChangesDock() {
  const { addToast } = useToast();
  const lastId = useRef(null); // null = first poll: remember where we are, don't toast old events

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const rows = await api("/changes", { params: { limit: 20 } });
        if (!alive) return;
        const newest = rows[0]?.id ?? 0;
        if (lastId.current === null) { lastId.current = newest; return; }
        const fresh = rows.filter((r) => r.id > lastId.current).reverse();
        if (!fresh.length) return;
        lastId.current = newest;
        addToast({ type: "info", title: "What changed", duration: 12000, message: fresh.slice(0, 3).map((r) => r.headline).join(" · ") });
        window.dispatchEvent(new Event("changes-updated"));
      } catch { /* the feed must never disturb the page */ }
    };
    poll();
    const timer = setInterval(poll, 4000);
    const soon = () => setTimeout(poll, 700);
    window.addEventListener("data-changed", soon);
    return () => { alive = false; clearInterval(timer); window.removeEventListener("data-changed", soon); };
  }, [addToast]);

  return null;
}

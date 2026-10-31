import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api";

const RATE = 16000;

/** One-second int16 PCM -> base64 WAV (44-byte header + samples). */
function wavBase64(pcm) {
  const buf = new ArrayBuffer(44 + pcm.length * 2);
  const v = new DataView(buf);
  const tag = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  tag(0, "RIFF"); v.setUint32(4, 36 + pcm.length * 2, true); tag(8, "WAVE"); tag(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, RATE, true); v.setUint32(28, RATE * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  tag(36, "data"); v.setUint32(40, pcm.length * 2, true);
  new Int16Array(buf, 44).set(pcm);
  const bytes = new Uint8Array(buf);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}

/**
 * Mic -> Wispr Flow WebSocket -> transcript. The browser only ever sees the short-lived token from POST /voice/token.
 * Protocol per https://api-docs.wisprflow.ai/websocket_api: auth, then append (equal 1 s wav packets), then commit.
 * state: idle | connecting | listening | processing. Any failure sets `error`; the text box keeps working.
 */
export function useWispr(onFinal) {
  const [state, setState] = useState("idle");
  const [partial, setPartial] = useState("");
  const [error, setError] = useState("");
  const s = useRef(null);

  const cleanup = useCallback(() => {
    const r = s.current;
    if (!r) return;
    clearTimeout(r.timer);
    r.stream?.getTracks().forEach((t) => t.stop());
    r.ctx?.close().catch(() => {});
    if (r.ws && r.ws.readyState <= 1) r.ws.close();
    s.current = null;
  }, []);

  const finish = useCallback(() => {
    const r = s.current;
    if (!r || r.done) return;
    r.done = true;
    const text = r.text.trim();
    cleanup(); setState("idle"); setPartial("");
    if (text) onFinal(text); else setError("I didn't catch any speech. Try again or type it.");
  }, [cleanup, onFinal]);

  const fail = useCallback((msg) => {
    if (s.current) s.current.done = true; // closing the socket below must not trigger a second, vaguer error
    cleanup(); setState("idle"); setPartial(""); setError(msg);
  }, [cleanup]);

  const start = useCallback(async () => {
    setError(""); setPartial(""); setState("connecting");
    try {
      const tok = await api("/voice/token", { method: "POST", body: {} });
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true } });
      const ctx = new AudioContext();
      await ctx.audioWorklet.addModule("/pcm-worklet.js");
      const ws = new WebSocket(tok.ws_url);
      const r = (s.current = { stream, ctx, ws, sent: 0, ready: false, queue: [], text: "", done: false, timer: null });
      const send = (m) => (r.ready ? ws.send(JSON.stringify(m)) : r.queue.push(m));

      ws.onopen = () => ws.send(JSON.stringify({ type: "auth", access_token: tok.access_token, language: ["en"] }));
      ws.onmessage = (ev) => {
        const m = JSON.parse(ev.data);
        if (m.status === "auth") { r.ready = true; r.queue.splice(0).forEach((q) => ws.send(JSON.stringify(q))); setState("listening"); }
        else if (m.status === "text") { r.text = m.body?.text ?? r.text; setPartial(r.text); if (m.final) finish(); }
        else if (m.status === "error") fail("Voice service returned an error. Type your command instead.");
      };
      ws.onerror = () => fail("Could not reach the voice service. Type your command instead.");
      ws.onclose = () => { if (r.committed) finish(); else if (!r.done) fail("Voice connection closed. Type your command instead."); };

      const node = new AudioWorkletNode(ctx, "pcm-chunker");
      const mute = ctx.createGain(); mute.gain.value = 0; // keeps the graph alive without playing the mic back
      ctx.createMediaStreamSource(stream).connect(node); node.connect(mute).connect(ctx.destination);
      node.port.onmessage = (e) => {
        if (e.data.pcm) {
          send({ type: "append", position: r.sent++, audio_packets: { packets: [wavBase64(e.data.pcm)], volumes: [e.data.volume],
            packet_duration: 1.0, audio_encoding: "wav", byte_encoding: "base64" } });
        } else if (e.data.done) {
          r.committed = true; send({ type: "commit", total_packets: r.sent });
          r.timer = setTimeout(finish, 15000); // docs: socket closes after the final result; do not hang if it never comes
        }
      };
      r.node = node;
    } catch (e) {
      fail(e.status === 503 || e.status === 502 ? e.message : "Microphone or voice service unavailable. Type your command instead.");
    }
  }, [fail, finish]);

  const stop = useCallback(() => {
    const r = s.current;
    if (!r) return;
    setState("processing");
    r.stream.getTracks().forEach((t) => t.stop());
    r.node.port.postMessage("flush");
  }, []);

  useEffect(() => cleanup, [cleanup]);
  return { state, partial, error, start, stop };
}

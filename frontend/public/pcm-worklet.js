// AudioWorklet: mic audio -> 16 kHz mono int16 chunks of exactly 1 second (what Wispr Flow's WebSocket expects).
// Sends {pcm, volume} per full second; on "flush" sends the last partial second zero-padded (all chunks must be equal length).
const RATE = 16000;

class PcmChunker extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ratio = sampleRate / RATE; // input samples per output sample
    this.acc = 0; this.sum = 0; this.cnt = 0;
    this.reset();
    this.port.onmessage = (e) => {
      if (e.data !== "flush") return;
      if (this.n > 0) this.emit();
      this.port.postMessage({ done: true });
    };
  }

  reset() { this.out = new Int16Array(RATE); this.n = 0; this.sumsq = 0; }

  emit() {
    this.port.postMessage({ pcm: this.out, volume: Math.sqrt(this.sumsq / Math.max(this.n, 1)) }, [this.out.buffer]);
    this.reset();
  }

  process(inputs) {
    const ch = inputs[0][0];
    if (!ch) return true;
    for (let i = 0; i < ch.length; i++) {
      this.sum += ch[i]; this.cnt++; this.acc++;
      if (this.acc < this.ratio) continue;
      this.acc -= this.ratio;
      const s = Math.max(-1, Math.min(1, this.sum / this.cnt));
      this.sum = 0; this.cnt = 0;
      this.out[this.n++] = s < 0 ? s * 0x8000 : s * 0x7fff;
      this.sumsq += s * s;
      if (this.n === RATE) this.emit();
    }
    return true;
  }
}
registerProcessor("pcm-chunker", PcmChunker);

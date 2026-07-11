/** WebAudio synth only (no assets). One master gain node keeps levels
 *  consistent; the context suspends when the tab goes to background and
 *  resumes on return (CLAUDE.md absolute rules).
 *
 *  Sound design (ui-spec §4 + "dopamine layer"): placement = cute pluck with
 *  a tiny upward pitch bend, clear = rising arpeggio + noise sparkle with the
 *  combo pitch-up (440Hz × 2^(combo/12), capped at 12), nova = sub boom +
 *  riser + glitter cascade, new best = 3-note fanfare. */

export class SoundEngine {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private noiseBuf: AudioBuffer | null = null;
  private placeAlt = 0;
  muted: boolean;

  constructor(muted = false) {
    this.muted = muted;
    document.addEventListener('visibilitychange', () => {
      if (!this.ctx) return;
      if (document.hidden) void this.ctx.suspend();
      else if (!this.muted) void this.ctx.resume();
    });
    // Audio watchdog (permanent): mobile browsers kill or interrupt the
    // context mid-session (calls, app switches, screen lock — iOS reports a
    // non-standard 'interrupted' state, and can even 'close' the context).
    // Every qualifying gesture nudges it back to 'running'; a closed context
    // is recreated on the next sound. This also covers the initial unlock.
    const poke = () => {
      if (this.muted) return;
      const ctx = this.ensure(); // ensure() resumes any non-running state
      if (ctx && ctx.state !== 'running') {
        void ctx.resume().then(() => {
          try {
            // silent one-sample blip fully unlocks iOS output
            const buf = ctx.createBuffer(1, 1, 22050);
            const src = ctx.createBufferSource();
            src.buffer = buf;
            src.connect(ctx.destination);
            src.start(0);
          } catch {
            /* already unlocked */
          }
        });
      }
    };
    window.addEventListener('pointerdown', poke, { passive: true });
    window.addEventListener('touchend', poke, { passive: true });
    window.addEventListener('keydown', poke);
    window.addEventListener('click', poke);
    window.addEventListener('pageshow', poke); // back-forward cache restore
  }

  /** QA hook: current audio pipeline state. */
  debug(): { state: string; muted: boolean } {
    return { state: this.ctx?.state ?? 'no-context', muted: this.muted };
  }

  /** Must be called from a user gesture at least once. */
  private ensure(): AudioContext | null {
    if (this.muted) return null;
    try {
      // a context the browser force-closed is dead — rebuild from scratch
      if (this.ctx && (this.ctx.state as string) === 'closed') {
        this.ctx = null;
        this.master = null;
        this.noiseBuf = null;
      }
      if (!this.ctx) {
        this.ctx = new AudioContext();
        this.master = this.ctx.createGain();
        this.master.gain.value = 0.32; // single master level for consistency
        this.master.connect(this.ctx.destination);
      }
      // recover from ANY non-running state ('suspended', iOS 'interrupted')
      if ((this.ctx.state as string) !== 'running' && !document.hidden) {
        void this.ctx.resume().catch(() => {});
      }
      return this.ctx;
    } catch {
      return null;
    }
  }

  setMuted(m: boolean): void {
    this.muted = m;
    if (this.ctx) {
      if (m) void this.ctx.suspend();
      else if (!document.hidden) void this.ctx.resume();
    }
  }

  private tone(
    freq: number,
    dur: number,
    at = 0,
    type: OscillatorType = 'sine',
    gain = 1,
    bendTo?: number,
  ): void {
    const ctx = this.ensure();
    if (!ctx || !this.master) return;
    const t0 = ctx.currentTime + at;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (bendTo) osc.frequency.exponentialRampToValueAtTime(bendTo, t0 + dur * 0.7);
    g.gain.setValueAtTime(0, t0);
    g.gain.linearRampToValueAtTime(gain, t0 + 0.008);
    g.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
    osc.connect(g).connect(this.master);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
  }

  /** Short filtered-noise burst (sparkle/crash). */
  private noise(dur: number, at = 0, freq = 4000, q = 1, gain = 0.3): void {
    const ctx = this.ensure();
    if (!ctx || !this.master) return;
    if (!this.noiseBuf) {
      const len = Math.floor(ctx.sampleRate * 0.5);
      this.noiseBuf = ctx.createBuffer(1, len, ctx.sampleRate);
      const data = this.noiseBuf.getChannelData(0);
      for (let i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    }
    const t0 = ctx.currentTime + at;
    const src = ctx.createBufferSource();
    src.buffer = this.noiseBuf;
    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.value = freq;
    filter.Q.value = q;
    const g = ctx.createGain();
    g.gain.setValueAtTime(gain, t0);
    g.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
    src.connect(filter).connect(g).connect(this.master);
    src.start(t0);
    src.stop(t0 + dur + 0.02);
  }

  /** Placement: cute two-alternating pluck with a tiny upward bend. */
  place(): void {
    this.placeAlt = (this.placeAlt + 1) % 4;
    const base = [523, 587, 659, 587][this.placeAlt]; // C5 D5 E5 D5 — playful
    this.tone(base * 0.75, 0.1, 0, 'sine', 0.9, base * 1.1);
    this.tone(base * 2, 0.05, 0.01, 'triangle', 0.22);
    this.noise(0.04, 0, 5200, 2, 0.1); // soft tick
  }

  /** Clear: rising arpeggio + sparkle; combo pitch-up 440 × 2^(combo/12), cap 12. */
  clear(combo: number): void {
    const base = 440 * Math.pow(2, Math.min(combo, 12) / 12);
    this.tone(base, 0.14, 0, 'triangle', 0.85);
    this.tone(base * 1.26, 0.14, 0.055, 'triangle', 0.85);
    this.tone(base * 1.5, 0.2, 0.11, 'triangle', 0.9);
    this.tone(base * 2, 0.24, 0.165, 'sine', 0.55);
    this.noise(0.22, 0.05, 6500, 1.2, 0.22); // glittery sweep
  }

  /** Big multi-line clear accent (2+ lines). */
  bigClear(): void {
    this.tone(196, 0.3, 0, 'sawtooth', 0.25, 392);
    this.noise(0.3, 0, 2400, 0.8, 0.28);
  }

  /** Nova: sub drop + impact crash + riser + long glitter cascade + ting. */
  nova(): void {
    // pitch-dropping sub hits harder than a flat boom
    this.tone(130, 0.8, 0, 'sine', 1.5, 42);
    this.tone(65, 0.55, 0.02, 'sine', 0.9);
    this.tone(220, 0.5, 0.02, 'sawtooth', 0.22, 1100); // riser
    this.noise(0.55, 0.0, 1600, 0.6, 0.5); // main crash
    this.noise(0.35, 0.12, 5200, 0.9, 0.3); // bright splash
    // cascading gold glitter (major pentatonic climb)
    const glitter = [1046, 1318, 1568, 1760, 2093, 2637, 3136];
    glitter.forEach((f, i) => this.tone(f, 0.16, 0.14 + i * 0.05, 'sine', 0.3 - i * 0.02));
    // finishing high "ting"
    this.tone(4186, 0.3, 0.55, 'sine', 0.22);
    this.noise(0.25, 0.55, 8000, 1.4, 0.12);
  }

  /** New best / perfect: 3-note fanfare + shimmer. */
  fanfare(): void {
    this.tone(523, 0.15, 0, 'triangle', 0.95);
    this.tone(659, 0.15, 0.12, 'triangle', 0.95);
    this.tone(784, 0.34, 0.24, 'triangle', 1.0);
    this.tone(1046, 0.3, 0.3, 'sine', 0.5);
    this.noise(0.35, 0.24, 7000, 1, 0.2);
  }

  invalid(): void {
    this.tone(150, 0.09, 0, 'square', 0.22, 120);
  }

  /** Cute pickup blip when a piece is lifted from the tray. */
  pickup(): void {
    this.tone(330, 0.07, 0, 'sine', 0.4, 560);
  }

  private lastSnap = 0;

  /** Tiny snap tick as the ghost lands on a new valid cell (throttled). */
  snapTick(): void {
    const now = performance.now();
    if (now - this.lastSnap < 70) return;
    this.lastSnap = now;
    this.tone(950, 0.03, 0, 'sine', 0.14);
  }

  /** Egg hatch: crack-crack → sparkle → happy major triad. */
  hatch(): void {
    this.noise(0.05, 0, 3000, 3, 0.3);
    this.noise(0.05, 0.12, 2600, 3, 0.32);
    this.tone(880, 0.1, 0.24, 'sine', 0.3);
    this.tone(1174, 0.1, 0.3, 'sine', 0.3);
    this.tone(523, 0.22, 0.38, 'triangle', 0.8);
    this.tone(659, 0.22, 0.38, 'triangle', 0.7);
    this.tone(784, 0.3, 0.38, 'triangle', 0.7);
    this.tone(1568, 0.25, 0.46, 'sine', 0.3);
  }

  gameOver(): void {
    this.tone(392, 0.18, 0, 'triangle', 0.8);
    this.tone(311, 0.18, 0.16, 'triangle', 0.8);
    this.tone(233, 0.36, 0.32, 'triangle', 0.8);
  }
}

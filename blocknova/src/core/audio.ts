/** WebAudio synth only (no assets). One master gain node keeps levels
 *  consistent; the context suspends when the tab goes to background and
 *  resumes on return (CLAUDE.md absolute rules). */

export class SoundEngine {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  muted: boolean;

  constructor(muted = false) {
    this.muted = muted;
    document.addEventListener('visibilitychange', () => {
      if (!this.ctx) return;
      if (document.hidden) void this.ctx.suspend();
      else if (!this.muted) void this.ctx.resume();
    });
  }

  /** Must be called from a user gesture at least once. */
  private ensure(): AudioContext | null {
    if (this.muted) return null;
    try {
      if (!this.ctx) {
        this.ctx = new AudioContext();
        this.master = this.ctx.createGain();
        this.master.gain.value = 0.35; // single master level for consistency
        this.master.connect(this.ctx.destination);
      }
      if (this.ctx.state === 'suspended' && !document.hidden) void this.ctx.resume();
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
  ): void {
    const ctx = this.ensure();
    if (!ctx || !this.master) return;
    const t0 = ctx.currentTime + at;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    g.gain.setValueAtTime(0, t0);
    g.gain.linearRampToValueAtTime(gain, t0 + 0.008);
    g.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
    osc.connect(g).connect(this.master);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
  }

  /** Placement: short woodblock-ish tick (~120ms). */
  place(): void {
    this.tone(660, 0.09, 0, 'triangle', 0.9);
    this.tone(1320, 0.05, 0, 'sine', 0.25);
  }

  /** Clear: rising arpeggio; combo pitch-up 440Hz × 2^(combo/12), capped at 12. */
  clear(combo: number): void {
    const base = 440 * Math.pow(2, Math.min(combo, 12) / 12);
    this.tone(base, 0.12, 0, 'triangle', 0.8);
    this.tone(base * 1.26, 0.12, 0.06, 'triangle', 0.8);
    this.tone(base * 1.5, 0.16, 0.12, 'triangle', 0.8);
  }

  /** Nova: low boom + glitter. */
  nova(): void {
    this.tone(70, 0.5, 0, 'sine', 1.2);
    this.tone(140, 0.35, 0.02, 'sine', 0.6);
    for (let i = 0; i < 5; i++) {
      this.tone(1200 + i * 320, 0.1, 0.1 + i * 0.05, 'sine', 0.2);
    }
  }

  /** New best: 3-note fanfare. */
  fanfare(): void {
    this.tone(523, 0.14, 0, 'triangle', 0.9);
    this.tone(659, 0.14, 0.12, 'triangle', 0.9);
    this.tone(784, 0.28, 0.24, 'triangle', 0.9);
  }

  invalid(): void {
    this.tone(160, 0.1, 0, 'square', 0.25);
  }

  gameOver(): void {
    this.tone(392, 0.18, 0, 'triangle', 0.8);
    this.tone(311, 0.18, 0.16, 'triangle', 0.8);
    this.tone(233, 0.32, 0.32, 'triangle', 0.8);
  }
}

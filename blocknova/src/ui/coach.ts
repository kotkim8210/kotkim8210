import { t } from '../core/i18n';

/** Coach marks (game-design §11): dim + cutout spotlight + bouncing arrow,
 *  ≤8 words of text, Skip top-right, shown inside real gameplay. The overlay
 *  never blocks input (pointer-events: none) except for the Skip button. */
export class Coach {
  private root: HTMLElement;
  private spot: HTMLElement;
  private tip: HTMLElement;
  private arrow: HTMLElement;

  constructor(onSkip: () => void) {
    this.root = document.createElement('div');
    this.root.className = 'coach';
    this.spot = document.createElement('div');
    this.spot.className = 'spot';
    this.tip = document.createElement('div');
    this.tip.className = 'tip';
    this.arrow = document.createElement('div');
    this.arrow.className = 'arrow';
    this.arrow.textContent = '↓';
    const skip = document.createElement('button');
    skip.className = 'skip';
    skip.textContent = t('skip');
    skip.addEventListener('click', onSkip);
    this.root.append(this.spot, this.tip, this.arrow, skip);
    document.body.appendChild(this.root);
  }

  /** Spotlight a screen rect and place the tip + arrow above or below it.
   *  dim=false keeps the gold ring + tip but leaves the screen bright —
   *  used for informational steps shown DURING live play. */
  show(rect: DOMRect, text: string, pad = 8, dim = true): void {
    const top = rect.top - pad;
    const left = rect.left - pad;
    const w = rect.width + pad * 2;
    const h = rect.height + pad * 2;
    this.spot.style.top = `${top}px`;
    this.spot.style.left = `${left}px`;
    this.spot.style.width = `${w}px`;
    this.spot.style.height = `${h}px`;
    this.spot.style.boxShadow = dim ? '' : 'none';

    const above = rect.top > innerHeight * 0.45;
    this.arrow.textContent = above ? '↓' : '↑';
    const cx = Math.max(16, Math.min(innerWidth - 16, rect.left + rect.width / 2));
    this.arrow.style.left = `${cx - 13}px`;
    this.arrow.style.top = above ? `${top - 40}px` : `${top + h + 8}px`;

    this.tip.textContent = text;
    // measure after setting text
    this.tip.style.left = '0px';
    this.tip.style.top = '0px';
    const tw = this.tip.offsetWidth;
    const tipLeft = Math.max(12, Math.min(innerWidth - tw - 12, cx - tw / 2));
    this.tip.style.left = `${tipLeft}px`;
    this.tip.style.top = above ? `${top - 40 - this.tip.offsetHeight - 8}px` : `${top + h + 44}px`;
    this.root.style.display = 'block';
  }

  hide(): void {
    this.root.style.display = 'none';
  }

  destroy(): void {
    this.root.remove();
  }
}

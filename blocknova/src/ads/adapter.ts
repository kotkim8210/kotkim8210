/** Ad adapter (CLAUDE.md §광고 어댑터). All ad traffic goes through this
 *  interface; game code never talks to a portal SDK directly.
 *
 *  Modes via VITE_ADS:
 *   - 'off' (default): console log + immediate success callback.
 *   - 'crazygames': SDK insertion points are marked below — the snippet from
 *     docs/monetization.md §SDK is pasted by the publisher at Phase 4; until
 *     then the adapter behaves like 'off'.
 */

export interface AdsAdapter {
  init(): void;
  loadingStart(): void;
  loadingStop(): void;
  gameplayStart(): void;
  gameplayStop(): void;
  /** Celebration moments only: nova explosion, perfect clear, new best. */
  happytime(): void;
  showInterstitial(done?: () => void): void;
  showRewarded(done: (success: boolean) => void): void;
}

const MODE = (import.meta.env?.VITE_ADS as string | undefined) ?? 'off';

const offAdapter: AdsAdapter = {
  init: () => console.debug('[ads:off] init'),
  loadingStart: () => console.debug('[ads:off] loadingStart'),
  loadingStop: () => console.debug('[ads:off] loadingStop'),
  gameplayStart: () => console.debug('[ads:off] gameplayStart'),
  gameplayStop: () => console.debug('[ads:off] gameplayStop'),
  happytime: () => console.debug('[ads:off] happytime'),
  showInterstitial: (done) => {
    console.debug('[ads:off] interstitial (skipped)');
    done?.();
  },
  showRewarded: (done) => {
    console.debug('[ads:off] rewarded (auto-success)');
    done(true);
  },
};

const crazyGamesAdapter: AdsAdapter = {
  init: () => {
    // [CrazyGames SDK] paste snippet #1 here (SDK <script> goes in index.html):
    // window.CrazyGames.SDK.init()
    console.debug('[ads:cg] init (SDK snippet not yet pasted)');
  },
  loadingStart: () => {
    // [CrazyGames SDK] window.CrazyGames.SDK.game.loadingStart()
    console.debug('[ads:cg] loadingStart');
  },
  loadingStop: () => {
    // [CrazyGames SDK] window.CrazyGames.SDK.game.loadingStop()
    console.debug('[ads:cg] loadingStop');
  },
  gameplayStart: () => {
    // [CrazyGames SDK] window.CrazyGames.SDK.game.gameplayStart()
    console.debug('[ads:cg] gameplayStart');
  },
  gameplayStop: () => {
    // [CrazyGames SDK] window.CrazyGames.SDK.game.gameplayStop()
    console.debug('[ads:cg] gameplayStop');
  },
  happytime: () => {
    // [CrazyGames SDK] window.CrazyGames.SDK.game.happytime()
    console.debug('[ads:cg] happytime');
  },
  showInterstitial: (done) => {
    // [CrazyGames SDK] paste snippet #2 here: requestAd('midgame', callbacks)
    console.debug('[ads:cg] interstitial (SDK snippet not yet pasted)');
    done?.();
  },
  showRewarded: (done) => {
    // [CrazyGames SDK] paste snippet #3 here: requestAd('rewarded', callbacks)
    console.debug('[ads:cg] rewarded (SDK snippet not yet pasted)');
    done(true);
  },
};

export const ads: AdsAdapter = MODE === 'crazygames' ? crazyGamesAdapter : offAdapter;

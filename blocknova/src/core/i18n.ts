import { isCoarsePointer } from './device';

/** English UI by default, Korean via `?lang=ko` (CLAUDE.md stack rules).
 *  `{action}` / `{action_lc}` expand to Tap/Click per device. */

type Dict = Record<string, string>;

const en: Dict = {
  score: 'SCORE',
  best: 'BEST',
  combo: 'COMBO',
  nova_ready: 'NOVA READY',
  pause: 'Pause',
  resume: 'Resume',
  restart: 'Restart',
  paused: 'Paused',
  mute: 'Sound',
  effects: 'Effects',
  fx_full: 'Full',
  fx_lite: 'Lite',
  game_over: 'Game Over',
  play_again: 'Play Again',
  new_best: 'NEW BEST!',
  touch_hint: '{action} a piece, then {action_lc} the board — or drag',
  keyboard_hint: '← → move · 1/2/3 select · Enter place · P pause',
  nova_boom: 'NOVA!',
  perfect: 'PERFECT CLEAR!',
};

const ko: Dict = {
  score: '점수',
  best: '최고',
  combo: '콤보',
  nova_ready: '노바 준비!',
  pause: '일시정지',
  resume: '계속하기',
  restart: '다시 시작',
  paused: '일시정지',
  mute: '소리',
  effects: '이펙트',
  fx_full: '전체',
  fx_lite: '라이트',
  game_over: '게임 오버',
  play_again: '다시 하기',
  new_best: '신기록!',
  touch_hint: '조각을 {action_lc}한 뒤 보드를 {action_lc} — 드래그도 가능',
  keyboard_hint: '← → 이동 · 1/2/3 선택 · Enter 배치 · P 일시정지',
  nova_boom: '노바!',
  perfect: '퍼펙트 클리어!',
};

function currentLang(): 'en' | 'ko' {
  try {
    return new URLSearchParams(location.search).get('lang') === 'ko' ? 'ko' : 'en';
  } catch {
    return 'en';
  }
}

export const lang = currentLang();

export function t(key: string): string {
  const dict = lang === 'ko' ? ko : en;
  let s = dict[key] ?? en[key] ?? key;
  const coarse = isCoarsePointer();
  const action = lang === 'ko' ? (coarse ? '탭' : '클릭') : coarse ? 'Tap' : 'Click';
  s = s.replaceAll('{action}', action);
  s = s.replaceAll('{action_lc}', lang === 'ko' ? action : action.toLowerCase());
  return s;
}

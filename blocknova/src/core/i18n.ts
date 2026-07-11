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
  skip: 'Skip',
  coach_drag: '{action} & drag this piece',
  coach_drop: 'Drop it here!',
  coach_nova: 'Fill the bar → NOVA!',
  bonus_charge: 'Bonus charge ⚡',
  daily: 'Daily',
  daily_title: 'Daily #{n}',
  daily_left: '{k} left',
  daily_survived: 'SURVIVED ALL 50!',
  daily_done: 'Run Complete',
  share: 'Share',
  copied: 'Copied!',
  retry_ad: 'Retry (Ad)',
  retry_used: 'Retry used',
  classic: 'Classic',
  daily_recorded: 'First run counts',
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
  skip: '건너뛰기',
  coach_drag: '이 조각을 드래그!',
  coach_drop: '여기에 놓아요!',
  coach_nova: '바가 차면 → 노바!',
  bonus_charge: '보너스 충전 ⚡',
  daily: '데일리',
  daily_title: '데일리 #{n}',
  daily_left: '{k}개 남음',
  daily_survived: '50조각 서바이벌 성공!',
  daily_done: '러닝 종료',
  share: '공유',
  copied: '복사됐어요!',
  retry_ad: '재도전 (광고)',
  retry_used: '재도전 사용됨',
  classic: '클래식',
  daily_recorded: '기록은 첫 판만 인정',
};

function currentLang(): 'en' | 'ko' {
  try {
    return new URLSearchParams(location.search).get('lang') === 'ko' ? 'ko' : 'en';
  } catch {
    return 'en';
  }
}

export const lang = currentLang();

export function t(key: string, vars: Record<string, string | number> = {}): string {
  const dict = lang === 'ko' ? ko : en;
  let s = dict[key] ?? en[key] ?? key;
  const coarse = isCoarsePointer();
  const action = lang === 'ko' ? (coarse ? '탭' : '클릭') : coarse ? 'Tap' : 'Click';
  s = s.replaceAll('{action}', action);
  s = s.replaceAll('{action_lc}', lang === 'ko' ? action : action.toLowerCase());
  for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v));
  return s;
}

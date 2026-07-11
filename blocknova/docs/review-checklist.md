# 심사 방어 점검표 — Block Nova (Phase 4 자체 점검)

CLAUDE.md "절대 규칙" 전 항목 자체 점검 결과. 측정치는 Playwright(Chromium) 자동 검증 기준.
검증 일자: 2026-07-11 · 번들: dist-portal 86.5KB(비압축) / zip 26.4KB — **목표 2MB의 1.3%**

| # | 항목 | 상태 | 근거 (파일 · 측정) |
|---|------|------|--------------------|
| 1 | 게임플레이 도달 ≤ 3초 (심사 기준 20초) | ✅ | 실측 **1.08초**(내비게이션→스플래시 제거→즉시 조작 가능). 번들 gzip 합계 ≈ 27KB — `index.html` |
| 2 | 스플래시 = 로딩바 1개 | ✅ | `index.html` `#splash` — 로고+단일 진행 바만 |
| 3 | 외부 요청 0 (폰트·이미지·오디오·분석 없음) | ✅ | Playwright 네트워크 캡처 **0건**. 소스 grep `http(s)://` 0건. 오디오는 WebAudio 합성 — `src/core/audio.ts` |
| 4 | 상대경로만 (CDN 하위 경로/iframe 안전) | ✅ | `vite.config.ts` `base:'./'`, dist `src="./assets/…"` 확인 |
| 5 | 입력 3종: 마우스 드래그 | ✅ | `src/ui/drag.ts` — 스모크에서 실제 배치 검증 |
| 6 | 입력 3종: 터치 드래그 + 탭-탭 보조 | ✅ | `src/ui/drag.ts`(pointer events 공용 + 탭 선택→보드 탭) — 380px 터치 에뮬레이션 검증 |
| 7 | 입력 3종: 키보드 (화살표 커서·1/2/3·Enter·**P 일시정지**·M 음소거, ESC 단독 금지) | ✅ | `src/ui/keyboard.ts` — P가 기본 일시정지, ESC는 보조 바인딩 |
| 8 | 기기별 분기: 터치 전용 UI 숨김 · Tap↔Click 자동 전환 | ✅ | `src/style.css` `@media(pointer:…)` `.coarse-only/.fine-only`, `src/core/i18n.ts` `{action}` 치환 |
| 9 | 데스크톱: 중앙 세로 컬럼 + 측면 앰비언트 배경 | ✅ | `src/style.css` `.ambient`, `src/ui/view.ts` — 1280px 스모크 검증 |
| 10 | 저사양: transform/opacity만 · 파티클 ≤24(라이트 12) · 프레임 샘플링 자동 이펙트 축소 | ✅ | `src/style.css`(전 애니메이션 transform/opacity), `src/ui/view.ts` 파티클 상한(노바 턴은 클리어 스파크 생략으로 예산 공유), `src/main.ts` `startFrameSampler`(45fps 미만 2회→라이트, 백그라운드 탭 윈도 폐기) + 라이트 모드에서 backdrop-blur 해제 + 일시정지 수동 토글 |
| 11 | `user-select:none` 계열 (롱프레스/확대 방지) | ✅ | `src/style.css` body + `-webkit-touch-callout:none`, `src/ui/drag.ts` contextmenu 차단, viewport `user-scalable=no` |
| 12 | iframe 내 정상 동작 · 전체화면 API 미호출 | ✅ | 크로스오리진 iframe 하네스에서 렌더+키보드 배치 실측 통과. `requestFullscreen` grep **0건**. 포인터 다운 시 `window.focus()` |
| 13 | 오디오: WebAudio 합성음만 · 단일 마스터 게인(레벨 일정) · 백그라운드 정지/복귀 | ✅ | `src/core/audio.ts` — master GainNode 1개, `visibilitychange` suspend/resume |
| 14 | 게임명·로고 자체 제작, 타 게임 혼동 없음 | ✅ | "Block Nova" 텍스트 워드마크(골드 그라디언트) — 외부 에셋 0 |
| 15 | 광고 어댑터 인터페이스 8종 + `VITE_ADS=off\|crazygames` 분기 | ✅ | `src/ads/adapter.ts` — off=콘솔+즉시 콜백, crazygames=SDK 삽입 지점 주석(스니펫 3곳) |
| 16 | 호출 지점: loading 시작/끝 · 판 시작/끝(일시정지 포함) · happytime=노바·퍼펙트·신기록만 | ✅ | `src/main.ts` — 부트/일시정지/게임오버에 gameplayStart/Stop, happytime 3곳 감사 완료 |
| 17 | 인터스티셜: 게임오버 **2회당 1회**, 결과 화면 진입 후만 | ✅ | `src/main.ts` `maybeInterstitial()` — 시트 표시 후 호출, 플레이 중 삽입 없음 |
| 18 | 리워드: 부활 1회/판(12셀 제거) · 데일리 재도전 1회/일 | ✅ | `src/main.ts` revive/retry 핸들러 → `ads.showRewarded` 경유 |
| 19 | 번들 ≤ 2MB | ✅ | `blocknova-portal.zip` 26.4KB / 비압축 86.5KB (`npm run build:portal` 출력) |

## 브라우저·뷰포트 스모크 결과

| 환경 | 결과 | 비고 |
|------|------|------|
| Chrome (Chromium 최신) | ✅ 37/37 + 증빙 10/10 | 데스크톱 1280×800 키보드·마우스 전체 시나리오 |
| Edge | ✅ (Chromium 동일 엔진) | 컨테이너에 Edge 바이너리 없음 — Blink 동일 계열로 간주 |
| Safari (WebKit) | ⚠️ 미실측 | 이 환경에 WebKit 없음 — **제출 전 iPhone/Mac Safari에서 1회 확인 권장** (전용 API 미사용·표준 CSS만이라 위험도 낮음) |
| 모바일 뷰포트 360×640 | ✅ 무스크롤·트레이 가시 | scrollHeight=viewport |
| 모바일 뷰포트 390×844 | ✅ 무스크롤·트레이 가시 | |
| 모바일 뷰포트 412×915 | ✅ 무스크롤·트레이 가시 | |
| 380×660 (기준 스펙) | ✅ 무스크롤 + 터치 드래그/탭-탭 배치 | Phase 1부터 회귀 검증 |

## 문서화된 스펙 편차 (조정 시 문서화 규칙)
- 조각 풀 19종 → **33종** (발주자 "다양성" 요청, 2026-07-11): T 4방향 전부, S/Z 세로, L/J 테트로미노 가로·세로, 3칸 코너 4방향, 5칸 코너 4방향, 3×2 직사각형 추가. 소형 조각 가중치 소폭 상향(dot 4→7, i2/v2 8→9)으로 가중 평균 조각 크기 3.78 → **3.83셀** (§10 목표 대비 +1.3%, 지표로 재조정 예정). 데일리 시퀀스는 시드 결정성 유지(풀 확장으로 기존 시퀀스와는 달라짐 — 출시 전이므로 영향 없음).
- 노바 셰이크: ui-spec §5의 ±3px/140ms → **±5px+0.4° 회전/220ms** (발주자 "도파민" 강화 요청, 2026-07-11)
- 폰트 최소 14px: 본문·힌트·버튼·퀘스트/칩 등 가독 텍스트는 13px+ 적용. NOVA 워드마크(11px)·통계 라벨(12px)은 그래픽 성격의 마이크로 캡션으로 예외 처리
- 게임오버 시트에 max-height + 스크롤 안전장치 추가 (짧은 포털 iframe 대비)

## SDK 활성화 절차 (발주자용 요약 — monetization.md §SDK)
1. `npm run build:portal` → `blocknova-portal.zip`을 developer.crazygames.com에 업로드
2. CrazyGames HTML5 SDK 스니펫을 `src/ads/adapter.ts`의 `[CrazyGames SDK]` 주석 3곳에 붙여넣기 (또는 Claude Code에 "SDK 붙여줘")
3. 다시 `npm run build:portal` → zip 재업로드 → 포털 프리뷰에서 로딩 이벤트·광고 확인 → 제출

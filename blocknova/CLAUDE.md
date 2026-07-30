# CLAUDE.md — Block Nova 빌드 지침 (v1.1)

9×9 블록 퍼즐 웹게임 "Block Nova" 스펙 패키지. 발주자는 비개발자 — 완료 보고는 실행 명령어까지 포함.
**v1.1 목표: CrazyGames 공개 심사 기준 전 항목 방어 + 프리미엄 비주얼 + 심리학 기반 후킹·리텐션.**

## 문서 우선순위
1. `docs/game-design.md`(규칙·후킹 스크립트·리텐션 시스템) 2. `docs/ui-spec.md`(프리미엄 토큰·주스)
3. `PRD.md` 4. `docs/monetization.md`(SDK 이벤트·광고) 5. `docs/wireframes.html`(시각 참조)

## 스택 (고정)
Vite + TypeScript + Tailwind, vanilla TS, 백엔드·로그인 금지, `localStorage`(`bn:`)만,
`data/pieces.json` import 번들. 영어 UI 기본 + `?lang=ko`. `npm run build` → dist.

## 절대 규칙 — 심사 방어 (전부 필수, Phase 4에서 자동 점검표 출력)
- **게임플레이 도달 ≤ 3초** (기준은 20초 — 마진 확보). 스플래시=로딩바 1개, 외부 요청 0, 상대경로만.
- **입력 3종**: 마우스 드래그 + 터치 드래그/탭-탭 + **키보드**(화살표로 셀 커서, 1/2/3 조각 선택, Enter 배치, **P=일시정지**, M=음소거). ESC 단독 일시정지 금지.
- **기기별 분기**: 데스크톱에서 터치 전용 UI 숨김, 문구 "Tap"↔"Click" 자동 전환, 데스크톱은 가로 화면에서 중앙 세로 컬럼 + 측면 앰비언트 배경(ui-spec §2).
- **저사양 보장**: 4GB 크롬북 기준 60fps — transform/opacity만, 파티클 ≤24, 프레임타임 샘플링으로 자동 이펙트 축소 모드. Chrome·Edge·Safari 3종 스모크 체크.
- body에 `user-select:none` 계열 CSS(롱프레스 확대 방지), iframe 내 정상 동작(전체화면 API 직접 호출 금지).
- 오디오: WebAudio 합성음만, 레벨 일정(-14LUFS 감 각), 탭 백그라운드 시 정지·복귀 시 재개.
- 게임명·아이콘은 타 게임과 혼동 금지 — "Block Nova" 고정, 로고는 자체 제작.

## 광고 어댑터 (`src/ads/adapter.ts`)
인터페이스: `init() / loadingStart() / loadingStop() / gameplayStart() / gameplayStop() /
happytime() / showInterstitial() / showRewarded(cb)`.
`VITE_ADS=off|crazygames` 분기 — off는 콘솔+즉시 콜백, crazygames는 SDK 삽입 지점 주석만(활성화는 발주자, monetization §SDK).
호출 지점: 로딩 시작/끝, 판 시작/끝(일시정지 포함), **happytime = 노바 폭발·퍼펙트 클리어·신기록**.

## 구현 단계 (단계별 수용 기준 통과 후 커밋)

### Phase 1 — 코어 + 크로스 입력
- [ ] vitest: 라인 판정 3케이스(§game-design 3), 게임오버 판정, 스폰 백 가중치·직전 조합 금지
- [ ] 마우스/터치/키보드 3입력 모두 배치 가능, 고스트 프리뷰·불가 표시
- [ ] 점수·콤보·노바 게이지, 베스트 저장, 380px 무스크롤 + 데스크톱 레이아웃

### Phase 2 — 후킹 + 프리미엄 주스
- [ ] **첫 실행 골든 퍼스트 무브**(§game-design 11): 프리셋 보드 → 1수에 더블 클리어, 노바 50% 선충전, 코치마크 3개(비주얼·스킵 가능·게임플레이 내)
- [ ] 주스 팩(ui-spec §5): 스쿼시&팝, 파티클, 점수 카운트업, 콤보 피치업 사운드, 햅틱, 신기록 콘페티
- [ ] 노바 폭발 연출 + happytime 호출, reduced-motion 대체

### Phase 3 — 리텐션 메타 (§game-design 12)
- [ ] 스트릭 + 실드(7일마다 1개 지급·결손일 자동 소모), 레벨/XP/랭크(L1 30% 선충전)
- [ ] 주간 퀘스트 3종(ISO 주 시드 결정적) + 진행 바(마지막 10% 글로우)
- [ ] 게임오버 근접실패 화면: "Best까지 -N" + 다음 조각 3개 공개, 15% 이내면 특수 카피
- [ ] PB 페이스 바, 퍼펙트 클리어 +1000 + happytime, 통계 모달
- [ ] vitest: XP 임계 함수, 주간 퀘스트 시드 결정성, 첫 실행 프리셋 더블클리어 성립

### Phase 4 — 포털 하드닝
- [ ] `VITE_ADS=crazygames` 빌드, 인터스티셜(게임오버 2회당)·리워드(부활/데일리 재도전) 지점 연결
- [ ] 위 "절대 규칙" 전 항목 자체 점검 → **심사 방어 점검표를 표로 출력** (항목·상태·근거 파일)
- [ ] `npm run build:portal` → dist 압축 `blocknova-portal.zip` + 번들 크기 보고(목표 ≤ 2MB)
- [ ] Chrome/Edge/Safari + 모바일 뷰포트 스모크 결과 표

## 완료 보고 형식
실행법 + 수용 기준 체크표 + (P4는) 심사 방어 점검표 + 남은 리스크 3줄.

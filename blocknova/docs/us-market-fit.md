# Block Nova 미국 시장 적합성 조사 + 반영 내역 (US Market Fit)

- 조사일: 2026-07-19 · 방법: 미국 블록퍼즐 상위권 게임 분석 기사·시장 리포트 웹 조사 + 코드 대조
- 결론 먼저: **테마(코스믹 다크+보석+골드)는 미국 취향에 적합 — 유지.** 갭은 표기 관습·피드백 크기 등 5건이었고 전부 반영 완료.

## 1. 조사 요약 (근거)

**미국 1위 Block Blast!의 성공 공식** ([MAF 분석](https://maf.ad/en/blog/block-blast/), [Lambert Post](https://thelambertpost.com/showcase/the-block-blast-phenomenon-why-we-cant-stop-playing/), [Playgama](https://playgama.com/blog/game-faqs/why-is-block-blast-so-popular-now/)):
- 클리어마다 **"Unbelievable!" 류 강화 문구 + 사운드 + 폰 진동**의 도파민 루프가 핵심 후킹 장치
- 튜토리얼 없이 3초 이해, 시간 압박 없음(전략적 배치), 짧은 판 = "한 판만 더"
- 화려한 색감+만족스러운 사운드가 틱톡/숏폼 공유로 이어져 바이럴
- **배경은 파스텔이 아니라 다크 네이비 + 광택 캔디 블록** — 다크 배경이 장르 표준

**장르 구조 분석** ([Deconstructor of Fun, 2026-01](https://www.deconstructoroffun.com/blog/2026/1/19/from-tetris-to-block-blast-why-block-puzzles-never-stop-printing)):
- 블록퍼즐은 테트리스 유산 덕에 "설치 전 이미 이해되는" 장르 — UA 파워의 원천
- 1세대(Block Blast 모델): 3조각 트레이 + 제한된 보드 + 강한 피드백 → **Block Nova가 정확히 이 포지션**
- 2025-26 승자의 차별점: ① 개성 있는 비주얼 테마(범용 그리드 탈피) ② 깊은 메타 레이어 ③ 레벨 디자인
- Block Nova는 ①(노바/코스믹 정체성) ②(스트릭·퀘스트·XP·펫 수집·데일리)를 이미 충족

**경쟁 환경** ([Woodoku 계열 리포트](https://marlvel.ai/intel-report/games/woodoku-blast-block-puzzle)):
- 미국의 또 다른 축은 Woodoku류 "코지 우드/젠" — 파스텔 kawaii가 아님
- 과도한 광고 빈도는 미국 유저 이탈 1순위 불만 → Block Nova의 "게임오버 2회당 인터스티셜" 정책이 유리

**판정:** 미국 상위권은 「다크+캔디 광택(Block Blast)」 또는 「코지 우드(Woodoku)」 — 파스텔 아기자기(kawaii)는 아시아向 감성에 가깝다. 앞서 cuteness-audit이 1순위로 꼽은 "파스텔 스킨"은 **미국 타깃에서는 보류**가 맞다.

## 2. 코드 대조에서 발견된 갭 → 반영 완료 (5건)

| # | 갭 | 반영 |
|---|---|---|
| 1 | 점수에 천 단위 콤마 없음(`1240`) — 미국 유저는 `1,240` 기대 | `fmt()` 신설(`i18n.ts`), HUD 점수·베스트·플로팅 +N·게임오버·근접실패 "Best −N"·통계 모달 전부 적용 |
| 2 | 콤보 칭찬 문구가 20~32px 소형 플로팅 — Block Blast 관습은 대형 센터 워드 | `wordPunch` 승격: 38~50px 센터 연출, 낮은 티어 아이스시안·상위 티어 골드(에스컬레이션 위계) |
| 3 | 더블/트리플 동시 클리어에 문구 없음(글로우만) | `DOUBLE!`(시안)/`TRIPLE!!`(골드) 신설 — 단, **한 무브당 한 단어** 원칙: 노바·퍼펙트 > 콤보 사다리 > 더블/트리플 |
| 4 | 퍼펙트 클리어(+1000)가 소형 플로팅 문구 | 골드 센터 워드로 승격 — 골든 퍼스트 무브가 곧 퍼펙트라 **첫 실행 wow가 더 커짐** |
| 5 | 신기록 순간에 진동 없음(사운드만) | `vibrate([20,30,60])` 추가 — Block Blast의 "보상 순간 폰 버즈" 관습 |

접근성 유지: 대형 워드는 reduced-motion 시 스케일 펀치 대신 부드러운 페이드로 대체(`style.css` `word-soft`).

## 3. 검증

- vitest 49/49 · `tsc` + 빌드 통과(gzip ~25.8KB JS)
- Playwright 실측: 골든 첫 수 → **"PERFECT CLEAR!" 단독 골드 워드**(겹침 없음 확인), HUD `1,052`·`BEST 12,480` 콤마 표기, DOUBLE! 시안 워드 경로 확인

## 4. 반영하지 않은 것 (선택 옵션으로 보류)

1. **레벨 모드**(2세대 트렌드) — 엔드리스+데일리 구조가 웹 포털에 적합, v2 후보
2. **IAP 아키텍처** — 웹 포털(광고 모델) 특성상 비적용
3. **사운드 교체** — 현 합성음이 이미 장르 관습(피치업 콤보·서브 붐)과 일치, 실유저 반응 전 교체는 리스크

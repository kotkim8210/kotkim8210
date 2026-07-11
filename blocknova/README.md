# Block Nova — Claude Code 인계 패키지 (비개발자용) · v1.1

검증된 9×9 블록 퍼즐 + 노바/데일리 트위스트. 포털(CrazyGames) 배포용 — **도메인·서버·호스팅 불필요.**
v1.1: CrazyGames 공개 심사 기준 전 항목 방어 규칙 내장 · Cosmic Glass 프리미엄 비주얼 ·
골든 퍼스트 무브 후킹 · 심리학 기반 리텐션(스트릭/실드·레벨·퀘스트·근접실패) 추가.

## 비개발자 실행 절차 (코딩 0)

**1) Claude Code 설치·실행** — Claude 데스크톱 앱의 Code 탭에서 이 폴더를 열거나, 터미널에서:
```bash
cd blocknova && claude
```
**2) 첫 지시 (복사·붙여넣기):**
```
CLAUDE.md를 읽고 Phase 1을 구현해줘. 나는 비개발자니까 실행 방법까지 포함해서 수용 기준 체크표로 보고해.
```
Phase 1 통과 확인 → "Phase 2 진행" → "Phase 3 진행". 각 보고의 체크표만 확인하면 됨.

**3) 제출 (당신이 직접 — 약 30분):**
- developer.crazygames.com 가입 → 게임 등록 → Phase 3가 만든 `blocknova-portal.zip` 업로드
- `docs/monetization.md §SDK` 순서대로 SDK 스니펫 3곳 붙여넣기(Claude Code에 "SDK 붙여줘"라고 시켜도 됨)
- 프리뷰 확인 → 제출 → 지급수단(PayPal) 등록

## 패키지 구성
| 파일 | 내용 |
|---|---|
| CLAUDE.md | Claude Code 빌드 지침(단계·수용 기준·금지사항) |
| PRD.md | 시장 근거·범위·KPI·리스크 |
| docs/game-design.md | 규칙·점수·노바·데일리 시드·광고 훅·저장 스키마 |
| docs/ui-spec.md | 다크 네온 토큰·컴포넌트·모션 |
| docs/wireframes.html | 3화면 시각 와이어프레임(브라우저로 열기) |
| docs/monetization.md | 포털 전략·광고 설계·SDK 절차·수익 시나리오(가설) |
| data/pieces.json | 19종 조각 정의(모양·가중치·색) |

## 이후 로드맵
Basic Launch 지표 확인(4~6주) → 병행 2호 「마작 짝맞추기」 착수(이 패키지 골격 재사용) → 승자 집중.

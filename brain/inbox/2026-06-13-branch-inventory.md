# [브랜치 전수조사] GitHub에 흩어진 스킬·프로젝트 인벤토리

- 일시: 2026-06-13 (UTC)
- 조사 방법: `git ls-tree` 로 17개 원격 브랜치의 파일 구조·스킬·고유 커밋 전수 조사
- 목적: 흩어진 세션 산출물을 brain에 색인하여 어느 세션에서든 `/recall`로 찾게 함
- 배경: 사용자 목표 = "세션마다 깃허브가 나뉘어 대화가 안 이어진다 → 하나의 제2의 뇌로 통합"

---

## 발견된 스킬 (4개) — 대부분 영상/유튜브 관련

### 1. karpathy-guidelines
- 브랜치: `claude/zealous-galileo-LVOsg`
- 출처: `multica-ai/andrej-karpathy-skills` (MIT, ~162k★)
- 내용: LLM 코딩 4원칙 (Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution)
- 형식: SKILL.md 단일 마크다운 (실행코드 없음)

### 2. watch (claude-video)
- 브랜치: `claude/determined-ride-DUgV1` (`.claude/skills/watch/`)
- 출처: `bradautomates/claude-video` (MIT)
- 내용: 영상 URL/로컬 → yt-dlp 다운로드 → ffmpeg 프레임 → 자막/Whisper 전사 → Claude 전달
- 구성: SKILL.md + scripts(download/frames/transcribe/watch/whisper/setup.py) + hooks + commands/watch.md
- 사건: 이 브랜치 커밋 히스토리에 malware 오탐 전말 기록됨 →
  `Add claude-video` → `Remove: confirmed malware` → `Re-add; retract false malware claim`(오탐 철회)

### 3. youtube-shorts-creator-ultimate
- 브랜치: `claude/determined-ride-DUgV1` (`.claude/skills/youtube-shorts-creator-ultimate/`)
- 내용: CC(크리에이티브 커먼즈) 기반 해외 쇼츠를 한국·일본 시청자용으로 현지화·재유통하는 운영 스킬
- 단계: CC 라이선스·음원·초상권 리스크 점검 → 후보 100점 점수표 → 댓글 클러스터 → 첫 2초 후킹 →
  한/일 대본 → 일본어 9항목 자가리뷰 → CapCut 줌·반전·자막 지시서 → 실질변형 게이트(C1~C3) →
  A/B/C 변형 → 업로드 후 24h/72h/7d 데이터 루프
- assets/examples 다수 포함

### 4. osmu-video-builder (osmu-auto)
- 브랜치: `claude/vibrant-cray-fyrz3` (`osmu-video-builder/`)
- 내용: OSMU 영상(역사·금융 '나락' 롱폼 + 클립) 반자동 제작 파이프라인
- 흐름: "N화 X주제로 만들어줘" → 대본(lean config) → auto.py 실행 →
  factcheck_todo.json의 [수치확인]·[실명위험]을 web_search로 자동 검증·수정 → 사람 할 일만 안내
- 핵심 규칙: 고증 검증을 사용자에게 떠넘기지 않음(기억이 아니라 스킬로 강제)
- 3화 '일본 부동산 버블/잃어버린 30년' 대본 포함, CI 스모크 테스트 워크플로 있음

---

## 발견된 독립 프로젝트 (7개)

### A. 인스타/쓰레드 콘텐츠 자동화
- 브랜치: `claude/automate-infographic-reels-dwO7j` (91파일, ahead 15)
- 구성: data/docs/output/scripts/src/templates + package.json (Node)
- 내용: @알쓸지잡10 채널용 트렌드 기반 콘텐츠 JSON 60+개, 인스타/쓰레드 번들 빌드 스크립트(caption + threads_caption), 정책 컴플라이언스 + 역할등록·Dev모드

### B. 홍보처 이메일 크롤러
- 브랜치: `claude/friendly-goldberg-i3mwo8` (ahead 10)
- 파일: build_promo_excel.py, collect_hanbang.py, collect_nursing_hospitals.py, crawl_emails.py
- 내용: 요양병원·한방병원 홈페이지 이메일 크롤러(검수 41건), 네이버 밴드/커뮤니티·B2B 공급처 엑셀, 오프라인 유통 12곳

### C. 당근스토어 상품등록 자동화
- 브랜치: `claude/gallant-keller-Vlmnq` (ahead 8)
- 구성: bookmarklet/legacy/listings/pricing + EXECUTION.md + 시세추적기 v3(.gs)
- 내용: 당근스토어 상품등록 폼 자동채움 북마클릿(초안 7종), 공급단가+시세 마진 추적기, 옥수수 가격 매칭, 당근 통합수수료 3.3%, 비즈프로필+상품판매 자격신청

### D. 성경저널 POD (Print on Demand)
- 브랜치: `claude/tender-wright-hf5pq1` (ahead 10)
- 파일: index/gate-calculator/geo-landing/hook-scorer/pdp-scorer/pain-scorer/validation-landing.html + assets/ideas
- 내용: 등산기록 저널 → 성경저널로 피벗 확정, '엄마의 기도 노트' 인쇄용 디자인 v1(올리브 1도 A5), GA4 자동집계, 쓰레드 14일 콘텐츠, PRO 가격

### E. Next.js 쿠팡파트너스 MVP
- 브랜치: `claude/lean-dev-workflow-i6yeq` (ahead 3), `claude/setup-claude-code-plugin-LIuOs` (ahead 2)
- 내용: Next.js 15 App Router + Tailwind v4 랜딩페이지(hero/feature grid/다크모드), 쿠팡파트너스 수익 + A/B 테스트 MVP, bkit 유틸 패키지

### F. 플러그인 설정 튜닝 (3 브랜치)
- `claude/optimize-token-settings-4r97O`: settings.json 토큰 절약 최적화
- `claude/resolve-namespace-conflicts-fmvMO`: everything-claude-code/gstack 네임스페이스 충돌 해소
- `claude/validate-settings-workflow-GOUhT`: CLAUDE.md 워크플로 템플릿 + validate-settings.sh

### G. brain (제2의 뇌) — 이미 main 통합 완료
- 브랜치: `claude/graphify-setup-7C8ba`(현 기본), `claude/festive-wright-9qx93v`
- 상태: PR #6 → graphify, PR #8 → main 통합 완료

---

## 브랜치 ↔ main 관계 요약 (정리 판단용)
- 머지가능(고유내용 0, main에 포함): festive-wright, graphify-setup, upbeat-goodall, merge-brain-into-main
- 고유 프로젝트 보존 필요: automate-infographic-reels, friendly-goldberg, gallant-keller, tender-wright, vibrant-cray, lean-dev-workflow, setup-claude-code-plugin
- 스킬 보존: zealous-galileo(karpathy), determined-ride(watch+youtube-shorts)
- 설정조각: optimize-token, resolve-namespace, validate-settings

## 후속(미결정)
- [ ] 기본 브랜치를 main으로 전환 (사용자가 GitHub Settings에서 직접 — MCP 도구 없음)
- [ ] 중복 브랜치 4개 삭제 여부 (이 환경 프록시가 push --delete 거부 → GitHub 웹에서)
- [ ] 각 프로젝트를 독립 레포로 분리할지, 이 레포 서브폴더로 둘지 검토

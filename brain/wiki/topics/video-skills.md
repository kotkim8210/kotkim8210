---
title: 영상·유튜브 스킬 모음 (watch · youtube-shorts · osmu)
slug: video-skills
tags: [스킬, 영상, 유튜브, 쇼츠, 자동화]
created: 2026-06-13
updated: 2026-06-13
sources: [2026-06-13-branch-inventory.md, 2026-06-13-skill-install-session.md]
related: [[claude-code-skills]], [[my-projects]]
confidence: high
status: active
---

## 한 줄 요약
GitHub 브랜치에 흩어져 있던 영상·유튜브 관련 Claude 스킬 3종 — 영상 시청(watch), 해외 쇼츠 한·일 현지화(youtube-shorts), 역사·금융 롱폼 반자동 제작(osmu) — 의 색인.

## 핵심 내용

### 1. watch (claude-video) — `claude/determined-ride-DUgV1`
- 위치: `.claude/skills/watch/`. 출처 `bradautomates/claude-video` (MIT). (2026-06-13-branch-inventory.md)
- 기능: 영상 URL/로컬 → yt-dlp 다운로드 → ffmpeg 프레임 추출 → 자막/Whisper 전사 → Claude가 시청·답변.
- 구성: SKILL.md + scripts(download/frames/transcribe/watch/whisper/setup.py) + hooks + commands/watch.md.
- **malware 오탐 사건**: 이 브랜치 커밋에 전말 기록 — `Add` → `Remove: confirmed malware` → `Re-add; retract false malware claim`(오탐 철회 확정). 영상 다운로더 패턴(외부도구+.env+네트워크)이 보안 분류기에 오탐되기 쉬움.

### 2. youtube-shorts-creator-ultimate — `claude/determined-ride-DUgV1`
- 위치: `.claude/skills/youtube-shorts-creator-ultimate/`.
- 기능: CC(크리에이티브 커먼즈) 기반 해외 쇼츠를 한국·일본 시청자용으로 현지화·재유통.
- 파이프라인: CC/음원/초상권 리스크 점검 → 후보 100점 점수표 → 댓글 클러스터 → 첫 2초 후킹 → 한/일 대본 → 일본어 9항목 자가리뷰 → CapCut 지시서 → 실질변형 게이트(C1~C3) → A/B/C 변형 → 24h/72h/7d 데이터 루프.

### 3. osmu-video-builder (osmu-auto) — `claude/vibrant-cray-fyrz3`
- 위치: `osmu-video-builder/`.
- 기능: OSMU 영상(역사·금융 '나락' 롱폼+클립) 반자동 제작. "N화 X주제로 만들어줘" → 대본(lean config) → auto.py → factcheck_todo.json의 [수치확인]·[실명위험]을 web_search로 자동 검증 → 사람 할 일만 안내.
- 핵심 규칙: 고증 검증을 사용자에게 떠넘기지 않음(기억 아닌 스킬로 강제). 3화 '일본 부동산 버블' 대본 포함.

## 연결고리 (Connections)
- [[claude-code-skills]] — 이들은 모두 user-invocable(슬래시 호출) 또는 스크립트 포함 스킬. 설치 스코프 규칙 적용.
- [[my-projects]] — youtube-shorts·osmu는 실제 콘텐츠 프로젝트(인스타·유튜브 채널 운영)와 직접 연결됨.

## 미해결/모순 (Open Questions)
- [ ] 이 영상 스킬 3종을 main(또는 유튜브 작업 레포)에 정식 설치할지 결정.
- [확인필요] watch 스킬 잔여 스크립트(frames/transcribe/whisper.py) 안전성 완전 검증.

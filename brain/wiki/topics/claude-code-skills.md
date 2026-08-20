---
title: 클로드 코드 스킬 — 설치·스코프·환경 (Claude Code Skills)
slug: claude-code-skills
tags: [클로드코드, 스킬, 설치, 환경, 안전]
created: 2026-06-13
updated: 2026-08-20
sources: [2026-06-13-skill-install-session.md, 2026-08-20-agent-browser-설치-트러블슈팅.md]
related: [[session-independence]], [[claude-knowledge-system]], [[agent-browser]]
confidence: high
status: active
---

## 한 줄 요약
클로드 코드 스킬은 설치 스코프(레포 커밋 / 유저레벨 / 전역 플러그인)에 따라 지속성·적용 범위가 다르며, "로컬 PC"와 "클라우드 임시 컨테이너"는 서로 보이지 않는 별개 컴퓨터라는 점이 모든 혼선의 근원이다.

## 핵심 내용
### 스킬 스코프 3가지 (지속성 차이)
- **레포 커밋** (`.claude/skills/<name>/SKILL.md` 커밋·푸시) → **영속**. 그 레포를 여는 어떤 세션에서도 적용. (2026-06-13-skill-install-session.md)
- **유저레벨** (`~/.claude/skills/...`, 윈도우 `%USERPROFILE%\.claude\skills\...`) → 그 컴퓨터 한정. 클라우드 컨테이너에 깔면 **세션 종료 시 소멸**(임시).
- **전역 플러그인** (`/plugin marketplace add ...`) → 로컬 Claude Code 전용. **웹/클라우드엔 `/plugin` 자체가 없음**(없는 게 정상).

### 로컬 PC ↔ 클라우드 컨테이너 = 다른 컴퓨터 (혼선의 핵심)
- 사용자 윈도우 PC(`C:\Users\..\.claude\skills`)와 클라우드 임시 컨테이너(`/root`)는 **서로 안 보인다.**
- 데스크톱 앱이라도 웹/클라우드 세션에 연결돼 있으면 **PC 설치가 적용되지 않는다.** 진짜 로컬(터미널 `claude` 또는 앱이 로컬 폴더를 연 상태)에서만 PC의 `~/.claude/skills`가 자동 적용.
- 판별법: `/plugin` → "isn't available"이면 클라우드, 메뉴가 반응하면 로컬.

### 스킬 호출 방식
- `user-invocable: true`가 있어야 `/skills` 메뉴·슬래시 호출형. 없으면 **model-invoked**(필요 시 자동 적용) — "메뉴에 안 보임 ≠ 안 깔림". (예: karpathy-guidelines=자동형, claude-video의 `watch`=슬래시형)

### 구체 스킬 (이 세션에서 다룸)
- **karpathy-guidelines** (`multica-ai/andrej-karpathy-skills`, MIT, 약 16만★): 코딩 행동 개선용 SKILL.md 단일 파일(실행 코드 없음→안전). 4원칙: Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution.
- **claude-video** (`bradautomates/claude-video`, MIT): `/watch`로 영상→프레임/전사→클로드. **실행 코드+SessionStart 훅 포함** → 설치 전 정독 권장. [확인필요] 일부 스크립트(watch/frames/transcribe/whisper.py) 미정독.
- **skill-creator** (Anthropic 공식): 이미 `/mnt/skills/examples/`에 번들로 존재(전역 기본 23종 중 하나).
- **agent-browser** (`vercel-labs/agent-browser`): CDP 브라우저 자동화 CLI. `--copy`로 레포에 커밋 → 영속. **SKILL.md는 스텁일 뿐 CLI 설치가 별도 필요**(`npm i -g agent-browser && agent-browser install`). 상세는 [[agent-browser]]. (2026-08-20-agent-browser-설치-트러블슈팅.md)

### 안전 원칙 (사건 교훈)
- 보안 분류기가 영상 다운로더 같은 패턴(외부 도구 실행+.env+네트워크)을 **malware로 오탐하기 쉽다.** 근거(어느 파일 어느 줄) 확인 전 단정 금지.
- **force-push 절대 금지** — 보안 경고 이력을 역사에서 지워 되돌리기 어렵게 만든다. 오탐 확정 시 **정정 커밋**으로 처리.

## 연결고리 (Connections)
- [[session-independence]] — "임시 컨테이너에선 커밋한 것만 영속" + "로컬 PC ↔ 클라우드는 다른 컴퓨터" 원칙을 스킬 설치 맥락에서 재확인(= brain/inbox 위치 혼선과 동일 원인).
- [[claude-knowledge-system]] — 이 제2의 뇌도 `.claude/`(스킬·명령)로 구현되므로 스킬 스코프 규칙의 영향을 받음.
- [[agent-browser]] — 스코프 규칙(`--copy`+커밋=영속, 전역 CLI=휘발)이 실제로 적용된 사례. "스킬 파일 ≠ 동작하는 도구"라는 새 교훈 추가.

## 미해결/모순 (Open Questions) — 후속 To-Do
- [ ] claude-video를 `the-reabon-youtube-blog` 레포 대상 세션에서 실제 설치(malware 근거 확인 후 오탐이면 정정 커밋).
- [ ] 윈도우 로컬 Claude Code에서 karpathy 작동 확인(코딩 과제로 검증).
- [ ] (선택) claude-video 잔여 스크립트 4종 정독으로 안전성 완전 검증.

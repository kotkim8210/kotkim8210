---
title: 세션 독립성 (Session Independence) — GitHub·API 키 없이 어디서나 작동
slug: session-independence
tags: [설계원칙, 운영, 비용, 아키텍처]
created: 2026-06-13
updated: 2026-06-13
sources: [2026-06-13-session-log-제2의뇌-구축.md]
related: [[claude-knowledge-system]], [[dream-sequence]], [[self-evolving-wiki]], [[data-dumping]], [[claude-code-skills]]
confidence: high
status: active
---

## 한 줄 요약
이 제2의 뇌의 두뇌는 GitHub가 아니라 `CLAUDE.md` + 슬래시 명령이므로, API 키·GitHub 설정 없이 **어떤 클로드 세션에서도** 완전히 작동하며 GitHub Action은 선택적 자동화 트리거일 뿐이다.

## 핵심 내용
- **원칙**: 시스템 로직의 단일 진실 공급원은 `.claude/commands/*.md`와 `CLAUDE.md`다. 따라서 웹·데스크톱·IDE·CLI 등 어떤 세션에서든 저장소만 열면 `/ingest`·`/dream`·`/recall`이 그대로 동작한다. (2026-06-13-session-log-제2의뇌-구축.md)
- **GitHub Action = 선택**: `.github/workflows/`의 자동화는 동일 명령을 자동 트리거하는 편의일 뿐이며, `ANTHROPIC_API_KEY` 시크릿이 없으면 **무비용으로 조용히 건너뛴다**. 즉 키·GitHub 없이도 손해가 없다.
- **비용 정책(결정)**: 사용자 요구("비용 거의 없는 수준")에 따라 드림 시퀀스 자동 실행은 **주 1회(일요일 새벽 KST)** 로 최소화. 빈도는 워크플로의 `cron` 한 줄로 조정.
- **근거(사용자 발화)**: "분리하지 말고 깃허브에 상관없이 어떤 세션에서도 작동하게끔 해줘."

## 연결고리 (Connections)
- [[claude-knowledge-system]] — 이 원칙이 3-컴포넌트 아키텍처의 실행 계층을 '세션'으로 못박는다.
- [[dream-sequence]] — 정제기는 GitHub Action 없이도 아무 세션의 `/dream`으로 실행된다(자동화는 옵션).
- [[self-evolving-wiki]] — `/ingest`·`/recall`도 세션에서 직접 동작하므로 연결·검색이 GitHub에 의존하지 않는다.
- [[data-dumping]] — 수집 역시 세션 `/ingest`로 충분(push 자동 수집은 옵션).
- [[claude-code-skills]] — 같은 뿌리 원리: "로컬 PC ↔ 클라우드 컨테이너는 다른 컴퓨터, 커밋한 것만 영속". 스킬 설치·`brain/inbox` 위치 혼선이 모두 여기서 비롯됨.

## 미해결/모순 (Open Questions)
- 없음.

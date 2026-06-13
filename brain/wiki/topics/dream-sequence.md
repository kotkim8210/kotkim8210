---
title: 드림 시퀀스 (Dream Sequence) — 백그라운드 지식 정제
slug: dream-sequence
tags: [정제기, 자동화, 백그라운드, 3단계, 핵심]
created: 2026-06-13
updated: 2026-06-13
sources: [2026-06-13-claude-second-brain.md]
related: [[second-brain]], [[self-evolving-wiki]], [[claude-knowledge-system]]
confidence: high
status: active
---

## 한 줄 요약
AI가 백그라운드 유휴 상태(예: 잠자는 시간)에 스스로 지식을 검토하여 모순·중복을 정리하고, 낡은 지식을 걸러내며 새 통찰을 쌓아 시스템의 성능과 정확도를 장기적으로 극대화하는 자동 정제 과정.

## 핵심 내용
- **작동 시점**: AI가 백그라운드에서 유휴 상태일 때(사람이 잠든 밤 등). (2026-06-13-claude-second-brain.md)
- **작동 내용**: 스스로 지식을 검토하여 ① 모순된 정보 정리 ② 중복 내용 정리 ③ 낡은 지식 필터링 ④ 새로운 통찰 축적.
- **효과**: 지속적 정제로 지식이 최신화되고 통찰력이 강화되어, 장기적으로 시스템의 성능·정확도가 극대화된다(자가 학습 루프).
- **구현(이 저장소)**: `.github/workflows/dream-sequence.yml`이 매일 새벽 클로드를 깨워 `/dream` 절차를 실행하고 결과를 커밋한다. 안전 원칙상 지식은 삭제하지 않고 `brain/archive/`로 보관하며 모든 변경은 `brain/.state/dream-log.md`에 기록한다.
- **타임라인**: [00:44] 단계. **이 시스템에서 가장 중요한 작업.**

## 연결고리 (Connections)
- [[self-evolving-wiki]] — 드림 시퀀스가 정제·개선하는 대상(위키와 지식 지도).
- [[claude-knowledge-system]] — 구현 컴포넌트가 "백그라운드 정제기(Refiner)".
- [[second-brain]] — 제2의 뇌의 품질 유지(3단계).

## 미해결/모순 (Open Questions)
- 없음.

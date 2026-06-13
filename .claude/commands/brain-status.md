---
description: 제2의 뇌 시스템의 통계와 상태를 요약한다 (대시보드)
allowed-tools: Read, Glob, Bash(bash scripts/brain.sh:*)
---

# 📊 /brain-status — 시스템 대시보드

다음을 수집해 사람이 읽기 좋게 요약하라:

1. `bash scripts/brain.sh`를 실행해 기본 통계(미처리 inbox · 주제 수 · 보관 수 · 총 단어 수 · 마지막 드림 시각)를 얻는다.
2. `brain/wiki/MAP.md`를 읽어 주요 주제군과 미해결 모순 목록을 파악한다.
3. `brain/.state/dream-log.md`의 최근 1~2개 항목을 확인해 최근 정제 활동을 요약한다.
4. `brain/.state/processed.json`에서 미처리 inbox가 있으면 `/ingest` 권장.

## 출력
- 한눈에 보이는 통계 블록
- 최근 드림 시퀀스가 한 일 요약
- 권장 다음 행동 (미처리 inbox가 있으면 /ingest, 모순이 쌓였으면 /dream 등)

#!/usr/bin/env bash
# brain.sh — 제2의 뇌 빠른 통계 (Second Brain quick stats)
# 사용법: bash scripts/brain.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# 미처리 inbox = inbox 파일 중 processed.json에 기록되지 않은 것
unprocessed=0
while IFS= read -r f; do
  base=$(basename "$f")
  if ! grep -q "$base" brain/.state/processed.json 2>/dev/null; then
    unprocessed=$((unprocessed + 1))
  fi
done < <(find brain/inbox -type f ! -name '.gitkeep' ! -name 'README.md' 2>/dev/null)

topic_count=$(find brain/wiki/topics -type f -name '*.md' ! -name '.gitkeep' 2>/dev/null | wc -l | tr -d ' ')
archive_count=$(find brain/archive -type f -name '*.md' 2>/dev/null | wc -l | tr -d ' ')

# 위키 전체 단어 수 (주제 + MAP + 통찰)
words=$(cat brain/wiki/topics/*.md brain/wiki/MAP.md brain/insights/INSIGHTS.md 2>/dev/null | wc -w | tr -d ' ')

# 마지막 드림 시퀀스 시각 (dream-log의 마지막 날짜 헤더, "## " 접두사 제거)
last_dream=$(grep -hoE '^## [0-9]{4}-[0-9]{2}-[0-9]{2}.*' brain/.state/dream-log.md 2>/dev/null | tail -1 | sed 's/^## //' || true)
[ -z "$last_dream" ] && last_dream="(아직 없음)"

echo "🧠 제2의 뇌 상태"
echo "──────────────────────────────"
echo "🗑️  미처리 inbox 항목 : ${unprocessed}"
echo "📄 위키 주제 문서      : ${topic_count}"
echo "🗄️  보관(archive) 문서 : ${archive_count}"
echo "📝 지식 총 단어 수     : ${words}"
echo "🌙 마지막 드림 시퀀스  : ${last_dream}"
echo "──────────────────────────────"
echo "다음 단계: /ingest (수집) · /dream (정제) · /recall <질문> (검색)"

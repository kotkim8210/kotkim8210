#!/bin/bash
# 영구 설정 검증 + 완벽 테스트

set -euo pipefail

SETTINGS_FILE=".claude/settings.json"
PASS=0
FAIL=0

check() {
  local label="$1"
  local result="$2"
  if [[ "$result" == "ok" ]]; then
    echo "  ✅ $label"
    PASS=$((PASS+1))
  else
    echo "  ❌ $label — $result"
    FAIL=$((FAIL+1))
  fi
}

echo "=== 1. settings.json 영구 저장 확인 ==="
if [[ -f "$SETTINGS_FILE" ]]; then
  check "settings.json 존재" "ok"
else
  check "settings.json 존재" "파일 없음: $SETTINGS_FILE"
fi

if grep -q "everything-claude-code" "$SETTINGS_FILE" 2>/dev/null; then
  check "extraKnownMarketplaces 등록" "ok"
else
  check "extraKnownMarketplaces 등록" "everything-claude-code 항목 없음"
fi

if grep -q '"enabledPlugins"' "$SETTINGS_FILE" 2>/dev/null; then
  check "enabledPlugins 설정" "ok"
else
  check "enabledPlugins 설정" "enabledPlugins 항목 없음"
fi

echo ""
echo "=== 2. 네임스페이스 분리 확인 ==="
if grep -q "gstack" "$SETTINGS_FILE" 2>/dev/null; then
  check "gstack-prod 네임스페이스" "ok"
else
  check "gstack-prod 네임스페이스" "settings.json에 gstack 항목 없음 (선택 사항)"
  FAIL=$((FAIL-1)); PASS=$((PASS+1))  # 선택 사항이므로 실패 취소
fi

echo ""
echo "=== 3. 자동 워크플로우 확인 ==="
if [[ -f "CLAUDE.md" ]]; then
  check "CLAUDE.md 존재" "ok"
else
  check "CLAUDE.md 존재" "CLAUDE.md 없음"
fi

if grep -q "바이브코더" CLAUDE.md 2>/dev/null; then
  check "바이브코더 워크플로우 템플릿" "ok"
else
  check "바이브코더 워크플로우 템플릿" "CLAUDE.md에 워크플로우 없음"
fi

if grep -q "CREATION:.*everything" CLAUDE.md 2>/dev/null && \
   grep -q "VALIDATION:.*gstack" CLAUDE.md 2>/dev/null; then
  check "CREATION/VALIDATION 워크플로우 정의" "ok"
else
  check "CREATION/VALIDATION 워크플로우 정의" "워크플로우 항목 없음"
fi

echo ""
echo "=== 4. 결과 요약 ==="
echo "  통과: $PASS  실패: $FAIL"
if [[ $FAIL -eq 0 ]]; then
  echo ""
  echo "🚀 바이브코더 15인 개발팀 완벽 설정 완료! 🚀"
  echo ""
  echo "다음 단계:"
  echo "  claude            # Claude Code 시작"
  echo "  /plugin list      # 플러그인 확인"
  echo "  /everything plan '작업 내용'"
else
  echo ""
  echo "위의 ❌ 항목을 수정한 후 다시 실행하세요."
  exit 1
fi

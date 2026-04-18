# 바이브코더 15인 개발팀 — 프로젝트 워크플로우

## 플러그인 설정

이 저장소는 `.claude/settings.json`을 통해 `everything-claude-code` 플러그인이 자동으로 등록·활성화됩니다.

## 개발 워크플로우

CREATION: /everything plan → /everything multi-execute
VALIDATION: /gstack review → /gstack ship

## 자동 적용 설정

- `extraKnownMarketplaces` : `everything-claude-code` 마켓플레이스 등록
- `enabledPlugins` : `everything-claude-code@everything-claude-code` 자동 활성화
- `PREFERRED_SKILLS` : gstack-prod 네임스페이스 분리

## 네임스페이스 분리

| 네임스페이스 | 용도 |
|---|---|
| `everything-claude-code` | 기본 서브에이전트·스킬·훅 |
| `gstack-prod` | 프로덕션 gstack 전용 스킬 |

## 검증 방법

```bash
bash validate-settings.sh
```

## 새 프로젝트 적용

```bash
git clone <this-repo>
cd <project>
cp -r .claude .
claude
```

Claude Code 시작 시 프로젝트 신뢰 프롬프트를 승인하면 모든 설정이 자동 적용됩니다.

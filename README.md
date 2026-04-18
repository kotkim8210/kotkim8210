# kotkim8210

Next.js 15 (App Router) + Tailwind CSS v4 스캐폴드.

## Getting Started

```bash
npm install
npm run dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000) 으로 접속하세요. `app/page.tsx` 를 수정하면 즉시 반영됩니다.

## Claude Code 플러그인

This repo is pre-configured to use the [`everything-claude-code`](https://github.com/affaan-m/everything-claude-code) plugin — a toolkit of subagents, skills, and automation hooks (code review, TDD, security scanning, formatting, multi-language patterns).

## Automatic setup

The project-level `.claude/settings.json` registers the marketplace and enables the plugin, so you don't need to run `/plugin` commands manually.

```bash
git clone <this-repo>
cd kotkim8210
claude
```

When Claude Code starts, approve the project-trust prompt. The marketplace `everything-claude-code` (source: `affaan-m/everything-claude-code`) is registered and the plugin `everything-claude-code@everything-claude-code` is enabled automatically.

Verify with:

```
/plugin list
/plugin marketplace list
```

## Manual fallback

If you opted out of project settings, run these inside Claude Code:

```
/plugin marketplace add affaan-m/everything-claude-code
/plugin install everything-claude-code@everything-claude-code
/plugin list
```

## Files

- `.claude/settings.json` — shared plugin/marketplace config (committed).
- `.claude/settings.local.json` — per-developer overrides (gitignored).

## Upstream

<https://github.com/affaan-m/everything-claude-code>

# [세션 대화 기록] 스킬 탐색·설치 (kke318 ↔ 클로드)

- 일시: 2026-06-13 (UTC)
- 참여: 사용자(kke318@gmail.com) · 클로드(Claude Code)
- 작업 브랜치(원본): `claude/zealous-galileo-LVOsg` (레포 `kotkim8210/kotkim8210`)
- 실행 환경: Claude Code 웹/클라우드 임시 컨테이너 (리눅스 VM, `/root` 홈). 커밋·푸시한 것만 영속.
- 비고: 사용자 요청으로 이 세션 대화 전체를 `brain/inbox`에 자료로 적재. 사람이 읽는 대화·결정 기록.

---

## 🙋 요청 1 — Karpathy Guidelines 설치
"15만 스타 받은 Karpathy Guidelines를 깃허브에서 찾아 다운로드·설치해서 쓸 수 있게 세팅."

## 🤖 응답 1 — 조사 후 설치 완료
- **canonical 레포:** `multica-ai/andrej-karpathy-skills` — **162,313★** (조사 시점, 올해 초 150k 돌파). 원작자 forrestchang, **MIT**.
  - "A single CLAUDE.md file to improve Claude Code behavior, derived from Andrej Karpathy's observations on LLM coding pitfalls."
- **스킬명:** `karpathy-guidelines`. **형식:** 마크다운 SKILL.md 단일 파일(실행 코드 없음 → 안전).
- **4대 원칙:** Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution.
- 안전 게이트가 자동 설치를 1차 차단 → 사용자 승인 후 설치. 사용자 선택: **"Repo + global"**.
  1. 프로젝트 커밋본 `.claude/skills/karpathy-guidelines/SKILL.md` → 커밋 `d5b6709` 푸시. **영속**.
  2. 유저레벨 `/root/.claude/skills/karpathy-guidelines/SKILL.md` → 컨테이너 한정, **임시**.
  - 원본과 SHA256 일치 확인.
- 설치 직후 시스템이 스킬 자동 인식 확인.

---

## 🙋 요청 2 — claude-video를 "유튜브 프로젝트에만" 설치
처음 "전체 환경" → 곧 정정: **유튜브 관련 프로젝트에만**.

## 🤖 응답 2 — 조사 완료, 설치는 환경 제약으로 미완
- **레포:** `bradautomates/claude-video` (MIT). `/watch`로 영상 다운로드(yt-dlp)→프레임(ffmpeg)→자막/Whisper 전사→Claude 전달.
- Karpathy와 달리 **실행 코드 포함**: `scripts/*.py`, `/watch` 커맨드, **SessionStart 훅**.
- **안전성:** 설치 전 핵심 파일(`SKILL.md`, `hooks.json`, `check-setup.sh`, `setup.py`, `download.py`, `README.md`) 직접 정독 → 깨끗. 단 `watch/frames/transcribe/whisper.py`는 미정독 → "본 파일은 깨끗"이지 "전부 보증"은 아님.
- **유튜브 레포 추정:** `kotkim8210/the-reabon-youtube-blog` (공개).
- **막힌 이유:** 이 세션은 `kotkim8210/kotkim8210`에만 권한. 유튜브 레포 push 시도 → `repository not authorized` (502) 거부.
- **2가지 방법 제시:**
  - Option 1(사용자 직접): 로컬에서 유튜브 레포 클론 후 `.claude/skills/watch/`에 복사·커밋·푸시.
  - Option 2(Claude 처리): claude.com/code에서 유튜브 레포 대상 **새 세션** 열고 "install claude-video here". → **사용자 선택: Option 2 (A)**.
- 작성자 공식 1줄(`/plugin marketplace add ...`)은 **전역 설치**라 "유튜브에만"과 반대 → 프로젝트 스코프(레포 내 파일 복사)가 정답.

---

## ⚠️ 사건 — 새 세션의 'malware' 분류
유튜브 레포 대상 새 세션이 claude-video를 한때 **"malware"로 커밋**했다가 "오탐인 듯"으로 번복. "잘못된 malware 커밋 정리?" 4지선다 노출(그대로 두기 / **force-push로 깨끗이** / 정정 커밋 / 기타).

**조언:**
- **force-push 절대 금지** — 되돌리기 어렵고 보안 경고 이력을 역사에서 삭제. 어느 쪽이든 손해.
- 누르기 전 **근거부터 요구**: "어느 스크립트 어느 줄 때문에 malware인가?"
- 오탐 확정 → **정정 커밋**. 진짜 의심 → 경고 남긴 채 제거 + 실행된 것(훅, `~/.config/watch/.env`) 점검.
- 판단: 영상 다운로더는 보안 분류기가 **오탐 내기 쉬운 패턴**(외부 도구 실행 + .env + 네트워크). 핵심 스크립트는 깨끗 → **오탐 가능성 높음**, 단 근거 확인 후 진행 권고.
- 로컬 직접 설치(mac/linux):
  ```bash
  git clone --depth 1 https://github.com/bradautomates/claude-video.git /tmp/cv
  mkdir -p .claude/skills/watch
  cp -r /tmp/cv/SKILL.md /tmp/cv/scripts .claude/skills/watch/
  ```

---

## 🙋 요청 3 — Skill Creator(Anthropic 공식) 설치돼 있나?

## 🤖 응답 3
- **이미 환경에 존재.** `/mnt/skills/examples/skill-creator/` (LICENSE.txt 포함 공식 번들).
  - 구성: SKILL.md, scripts, agents, assets, references, eval-viewer. 기능: 스킬 생성·개선·eval·description 최적화.
- `/mnt/skills/`는 Anthropic 기본 번들(skill-creator 외 mcp-builder, canvas-design 등 23개).
- "디스크 존재 ≠ 이번 세션 슬래시 호출 가능". 활성 스킬 디렉터리 연결 필요.

---

## 🙋 요청 4 — Karpathy를 "내 모든 세션에서 자동" 되게 (윈도우 로컬 설치)

## 🤖 응답 4
- 사용자 환경: **Windows 10 (cmd)**. 처음 준 mac/linux 명령 실패(`mkdir -p`, `~`, `\`, `-o`).
- **성공한 cmd 명령:**
  ```cmd
  mkdir "%USERPROFILE%\.claude\skills\karpathy-guidelines"
  curl -sL https://raw.githubusercontent.com/multica-ai/andrej-karpathy-skills/main/skills/karpathy-guidelines/SKILL.md -o "%USERPROFILE%\.claude\skills\karpathy-guidelines\SKILL.md"
  type "%USERPROFILE%\.claude\skills\karpathy-guidelines\SKILL.md"
  ```
- 결과: `type` 출력으로 설치 확인 → `C:\Users\0\.claude\skills\karpathy-guidelines\SKILL.md`.
- 출력의 `??`는 cmd 코드페이지가 `→` 화살표를 화면에 못 그리는 것뿐 — **파일 내용 정상**.

---

## 🙋 반복 질문 — "어디서 적용되나?" / "이 데스크톱 세션에서 자동 적용?"

## 🤖 개념 정리 (핵심)
- **두 개의 다른 컴퓨터:** ① 사용자 윈도우 PC(`C:\Users\0\.claude\skills`) ↔ ② 클라우드 임시 컨테이너(`/root`). 서로 안 보임.
- **이 클라우드 세션:** Claude가 따로 깔아둔 karpathy 활성 → 코드 작업 시 자동 적용. **단 사용자 PC 설치와 무관.**
- **`/plugin` 안 됨 = 정상:** 로컬 Claude Code 전용. 웹/클라우드엔 없음.
- **`/skills` 메뉴에 karpathy 안 뜸 = 정상:** SKILL.md에 `user-invocable: true` 없음 → 슬래시 호출형 아님(model-invoked = 자동 적용). claude-video의 `watch`는 그게 있어 슬래시 가능(대조). "메뉴에 없다 ≠ 안 깔림".
- **판별법:** `/plugin` → "isn't available" = 클라우드 / 메뉴 반응 = 로컬.
- **데스크톱 앱이라도** 웹/클라우드 세션에 연결돼 있으면 PC 설치 적용 안 됨. 진짜 로컬(터미널 `claude` 또는 앱이 로컬 폴더 연 상태)에서만 PC의 `~/.claude/skills` 자동 적용.

---

## 🗂️ 후속 작업 (To-Do)
- [ ] **claude-video를 `the-reabon-youtube-blog`에 실제 설치** — 그 레포 대상 세션에서. malware 근거 확인 후 오탐이면 정정 커밋, 진짜면 정지.
- [ ] 사용자 윈도우 **로컬 Claude Code**에서 karpathy 작동 확인 (코딩 과제로 검증, `/skills` 아님).
- [ ] (선택) claude-video 잔여 스크립트 4종 정독으로 안전성 완전 검증.
- [ ] (선택) Skill Creator를 이번 세션에서 슬래시 호출 가능하게 활성화할지 결정.

---

## 📌 메모 — brain/inbox 위치 혼선 해결
- 사용자가 처음 "여태 대화 전부 brain/inbox에 넣어" 요청 → Claude가 작업 브랜치(`zealous-galileo-LVOsg`)에 `brain/inbox/2026-06-13-skill-install-session.md` 생성·커밋(`56c2720`).
- 이후 사용자가 스크린샷으로 **실제 brain 시스템은 다른 브랜치** `claude/festive-wright-9qx93v`의 `brain/inbox`임을 지적 → 본 파일을 그 브랜치 inbox에 적재(이 파일). `/ingest`로 위키 반영 가능.

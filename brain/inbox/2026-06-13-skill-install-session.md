# 세션 기록 — 스킬 탐색·설치 작업

- **날짜:** 2026-06-13 (UTC)
- **레포:** `kotkim8210/kotkim8210`
- **브랜치:** `claude/zealous-galileo-LVOsg`
- **실행 환경:** Claude Code 웹/클라우드 임시 컨테이너 (리눅스 VM, `/root` 홈). 세션 종료 시 컨테이너 회수 → 커밋·푸시한 것만 영속.
- **요약:** Karpathy Guidelines 스킬 설치(완료), claude-video 스킬 조사(설치는 환경 제약으로 미완), Skill Creator 설치 여부 확인, 로컬(윈도우) 설치 안내, "어디서 적용되는가" 개념 정리.

---

## 1. Karpathy Guidelines 스킬 — 찾기·설치 (완료)

### 요청
"15만 스타 받은 Karpathy Guidelines를 깃허브에서 찾아 다운로드·설치해서 쓸 수 있게 세팅."

### 조사 결과
- **canonical 레포:** `multica-ai/andrej-karpathy-skills`
  - 스타: **162,313★** (조사 시점). 올해 초 150k 돌파.
  - 설명: "A single CLAUDE.md file to improve Claude Code behavior, derived from Andrej Karpathy's observations on LLM coding pitfalls."
  - 원작자: forrestchang. 라이선스: **MIT**.
  - 동일 내용 미러: `forrestchang/andrej-karpathy-skills` (개인 계정).
- **스킬 이름:** `karpathy-guidelines`
- **형식:** 마크다운 SKILL.md 단일 파일 (**실행 코드/스크립트 없음** → 안전).
- **4대 원칙:** Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution.
- 레포는 4가지 설치 포맷 제공: Claude 플러그인, Agent Skill, CLAUDE.md, Cursor rules.

### 설치 내역 (사용자 승인 후)
사용자 선택: **"Repo + global"** (레포 커밋 + 유저레벨 전역).

1. **프로젝트(레포) 커밋본** — `.claude/skills/karpathy-guidelines/SKILL.md`
   - git 커밋 `d5b6709` → `claude/zealous-galileo-LVOsg` 브랜치에 푸시 완료.
   - **영속적** (git에 박힘). `kotkim8210/kotkim8210` 레포를 여는 세션에서 자동 작동.
2. **유저레벨 복사본** — `/root/.claude/skills/karpathy-guidelines/SKILL.md`
   - 이 컨테이너 내 모든 프로젝트에서 작동하지만 **임시** (컨테이너 회수 시 소멸).
- 원본과 SHA256 일치 확인: `6e22cc54cb02a5e98ae42d06d9d7292db0c1b43894831b32879beb0166b2aea7`.

### 주의/오해 정리
- 처음 "전역(global)"은 **이 클라우드 컨테이너 한정 전역**이라는 뜻이었음 (사용자 PC 아님).
- 영속적으로 남는 건 **레포 커밋본 하나뿐**.

---

## 2. claude-video 스킬 — 조사 (설치는 환경 제약으로 미완)

### 요청 변화
처음 "전체 환경에 설치" → 곧바로 정정: **"claude-video를 유튜브 관련 프로젝트에만 설치"**.

### 조사 결과
- **레포:** `bradautomates/claude-video`
- **기능:** "Give Claude the ability to watch any video." `/watch` 명령으로 영상 다운로드(yt-dlp) → 프레임 추출(ffmpeg) → 자막/Whisper 전사 → Claude에 전달.
- **라이선스:** MIT.
- **Karpathy 스킬과 차이:** 이건 **실행 코드 포함** — `scripts/{watch,download,frames,transcribe,whisper,setup}.py`, `/watch` 커맨드, **SessionStart 훅**(`hooks/hooks.json` + `check-setup.sh`).

### 안전성 검토 (설치 전 직접 읽음)
읽은 파일: `SKILL.md`, `hooks/hooks.json`, `hooks/scripts/check-setup.sh`, `scripts/setup.py`, `scripts/download.py`, `README.md` → **깨끗함**.
- 정상 동작: yt-dlp로 공개 영상 다운로드, ffmpeg 프레임/오디오 추출, 자막 없을 때만(키 설정 시) Groq/OpenAI Whisper로 **오디오만** 전송.
- 안 하는 것: 영상 자체 업로드 X, 플랫폼 로그인/쿠키 X, API 키 로깅/유출 X.
- **단, 전체 파일을 다 읽지는 못함** (`watch.py`, `frames.py`, `transcribe.py`, `whisper.py` 미정독) → "내가 본 파일은 깨끗"이지 "전부 보증"은 아님.

### 설치 못 한 이유 (환경 제약)
- 유튜브 레포 = `kotkim8210/the-reabon-youtube-blog` (공개)로 추정.
- **이 세션은 `kotkim8210/kotkim8210`에만 권한.** 다른 레포 push 시도 → `repository not authorized` (502) 거부됨.
- 따라서 이 세션에서는 유튜브 레포에 직접 클론·커밋·푸시 불가.

### 제시한 2가지 방법
- **Option 1 (사용자 직접):** 로컬 터미널에서 유튜브 레포 클론 후 `.claude/skills/watch/`에 `SKILL.md`+`scripts/` 복사 → 커밋·푸시. (프로젝트 스코프 = 유튜브 레포에만)
- **Option 2 (Claude가 처리):** claude.com/code에서 `the-reabon-youtube-blog` 대상으로 **새 세션**을 열고 "install claude-video here" → 그 세션의 Claude가 전부 처리. **사용자 선택: A (Option 2).**

### 프로젝트 스코프 vs 전역
- 작성자 공식 1줄: `/plugin marketplace add bradautomates/claude-video` → `/plugin install watch@claude-video` = **전역 설치** (모든 프로젝트). "유튜브에만"과 반대.
- 올바른 프로젝트 스코프: 레포 안 `.claude/skills/watch/`에 파일로 직접 복사.

---

## 3. 새 세션의 'malware' 분류 사건 (유튜브 레포 쪽 세션)

- 사용자가 Option 2로 새 세션을 열자, 그쪽 세션이 claude-video를 한때 **"malware"로 커밋**했다가 "오탐인 듯"으로 말 바꿈. "잘못된 malware 커밋 어떻게 정리?" 4지선다 노출.
  1. 그대로 두기(세션만 사용) 2. **강제 푸시로 깨끗이(force-push)** 3. 정정 커밋 추가 4. 기타
- **조언:**
  - **2번(force-push) 절대 금지** — 되돌리기 어렵고 보안 경고 이력을 역사에서 지움. 어느 쪽이든 손해.
  - 누르기 전에 **근거부터 요구**: "어느 스크립트 어느 줄 때문에 malware라고 했나?"
  - 오탐 확정 시 → **3번(정정 커밋)** 권장. 진짜 의심 시 → 경고 남긴 채 정상 제거 + 이미 실행된 것(훅, `~/.config/watch/.env`) 점검.
- **Claude 판단:** 영상 다운로더는 보안 분류기가 **오탐 내기 쉬운 패턴**(외부 도구 실행 + .env 읽기 + 네트워크). 설치 전 핵심 스크립트는 깨끗했음 → **오탐 가능성 높음**. 단 전 파일 미검증이라 "근거 확인 후 진행" 권고.
- **로컬 직접 설치 명령(윈도우 아님, mac/linux):**
  ```bash
  git clone --depth 1 https://github.com/bradautomates/claude-video.git /tmp/cv
  mkdir -p .claude/skills/watch
  cp -r /tmp/cv/SKILL.md /tmp/cv/scripts .claude/skills/watch/
  ```

---

## 4. Skill Creator (Anthropic 공식 스킬) — 설치 확인

- 질문: "Anthropic 공식 Skill Creator 설치돼 있나?"
- **답: 이미 환경에 존재.** 위치: `/mnt/skills/examples/skill-creator/` (LICENSE.txt 포함, 공식 번들).
  - 구성: `SKILL.md`, `scripts/`, `agents/`, `assets/`, `references/`, `eval-viewer/`.
  - 기능: 새 스킬 생성, 기존 스킬 수정·개선, eval/벤치마크, description 트리거 최적화.
- `/mnt/skills/`는 Anthropic 기본 제공 번들 (skill-creator 외 mcp-builder, canvas-design, brand-guidelines, web-artifacts-builder 등 23개).
- **단, "디스크에 존재" ≠ "이번 세션에서 슬래시로 호출 가능".** 번들 스킬은 활성 스킬 디렉터리로 연결해야 슬래시 사용 가능.

---

## 5. 로컬(윈도우 PC) 설치 — Karpathy 전역 적용

- 목표: "내 모든 세션에서 자동 작동" → **사용자 로컬 PC의 `~/.claude/skills/`** 에 깔아야 함 (클라우드 컨테이너에 뭘 해도 PC엔 안 옴).
- 사용자 환경: **Windows 10 (cmd)**. 처음 준 mac/linux 명령(`mkdir -p`, `~`, `\`, `-o`) 실패.
- **성공한 윈도우 cmd 명령:**
  ```cmd
  mkdir "%USERPROFILE%\.claude\skills\karpathy-guidelines"
  curl -sL https://raw.githubusercontent.com/multica-ai/andrej-karpathy-skills/main/skills/karpathy-guidelines/SKILL.md -o "%USERPROFILE%\.claude\skills\karpathy-guidelines\SKILL.md"
  type "%USERPROFILE%\.claude\skills\karpathy-guidelines\SKILL.md"
  ```
- 결과: `type` 출력으로 **설치 확인됨** → `C:\Users\0\.claude\skills\karpathy-guidelines\SKILL.md`.
- 출력의 `??` 표시: cmd 한글 코드페이지가 `→`(화살표) 특수문자를 화면에 못 그리는 것뿐 — **파일 내용은 정상** (curl -o는 바이트 그대로 저장, Claude Code는 UTF-8로 정상 읽음). 메모장으로 열면 화살표 정상.

---

## 6. 개념 정리 — "어디서 적용되는가" (반복 질문)

### 핵심 구분: 두 개의 다른 컴퓨터
| | 사용자가 cmd로 깐 곳 | 지금 이 채팅 세션 |
|---|---|---|
| 위치 | `C:\Users\0\.claude\skills\` (윈도우 PC) | 클라우드 임시 컨테이너 (`/root`, 리눅스 VM) |
| 관계 | **서로 다른 기계** | |

- **이 클라우드 세션**: Claude가 따로 깔아둔 karpathy가 활성 → 코드 작업 시 자동 적용됨. **단 이는 사용자 PC 설치와 무관.**
- **사용자 윈도우 로컬 Claude Code**: cmd 설치본이 자동 적용되는 목적지.

### `/plugin` 안 됨 → 정상
- `/plugin`은 **로컬 Claude Code 전용**. 웹/클라우드 세션엔 없음 → "isn't available in this environment" 정상.

### `/skills` 메뉴에 karpathy 안 뜸 → 정상
- karpathy SKILL.md에 **`user-invocable: true` 없음** → 슬래시로 부르는 스킬이 아님 (model-invoked = 모델이 자동 적용).
- claude-video의 `watch`는 `user-invocable: true` 있어서 슬래시 호출 가능 (대조).
- 따라서 "메뉴에 없다 = 안 깔림"이 아님. **코드 작업 시 자동 적용**되는 방식.

### 적용 위치 1초 판별법
- 채팅에 `/plugin` → "isn't available" = **클라우드** (PC 설치 무관) / 메뉴 반응 = **로컬** (PC 설치 적용).

### 데스크톱 앱 관련 (B 케이스)
- 데스크톱 **앱**이어도 "웹/클라우드 세션"에 연결돼 있으면 실행은 클라우드 → 사용자 PC 설치 적용 안 됨.
- 진짜 로컬(터미널 `claude` 또는 데스크톱 앱이 로컬 폴더 연 상태)에서만 PC의 `~/.claude/skills`가 자동 적용.

---

## 미해결/후속 작업 (To-Do)
- [ ] **claude-video를 `the-reabon-youtube-blog`에 실제 설치** — 그 레포 대상 세션에서 진행 (이 세션 권한 밖). malware 판정 근거 확인 후 오탐이면 3번(정정 커밋), 진짜면 정지.
- [ ] 사용자 윈도우 **로컬 Claude Code**에서 karpathy 작동 확인 (코딩 과제로 검증, `/skills` 아님).
- [ ] (선택) claude-video 잔여 스크립트 4종(`watch/frames/transcribe/whisper.py`) 정독으로 안전성 완전 검증.
- [ ] (선택) Skill Creator를 이번 세션에서 슬래시 호출 가능하게 활성화할지 결정.

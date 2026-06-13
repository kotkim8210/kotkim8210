# 🧠 제2의 뇌 (Second Brain) — 스스로 진화하는 클로드 위키

> 분류하지 말고 그냥 던져라. **연결·요약·정제·검색은 클로드가 한다.**

방대한 정보를 수동으로 분류하느라 시간을 낭비하지 않고, 그냥 `brain/inbox/`에 던져넣기만 하면
클로드(Claude)가 스스로 **요약된 지식 지도**를 만들고, 정보 사이의 **연결고리**를 찾아내며,
밤마다 **드림 시퀀스(Dream Sequence)** 로 모순과 중복을 정제하는 자가 진화형 지식 창고입니다.

---

## ⚙️ 시스템 구조

| 구성 요소 | 핵심 기능 | 구현 | 위치 |
| :--- | :--- | :--- | :--- |
| 🗑️ **데이터 수집기**<br>(Collector) | 분류 기준 없이 무작위 투입 | `/ingest` 명령 + push 시 자동 실행 | `brain/inbox/` |
| 🧠 **지식 연결 엔진**<br>(Connector) | 정보 간 상관관계 매핑 → 요약된 **지식 지도** 생성 | `/ingest`가 위키·MAP 생성 | `brain/wiki/` |
| 🌙 **백그라운드 정제기**<br>(Refiner) | 유휴 시간에 모순/중복 필터링 + 통찰 합성 | `/dream` (선택: 주간 자동 Action) | `.github/workflows/` |
| 🔍 **초고속 검색** | 40만 단어 속에서도 몇 초 만에 답 | `/recall` (MAP 인덱스 우선) | — |

---

## ✅ 어디서나 작동 — GitHub도, API 키도 필요 없음

이 시스템의 두뇌는 **GitHub가 아니라 [`CLAUDE.md`](CLAUDE.md) + 슬래시 명령**입니다.
따라서 **어떤 클로드 세션에서든**(웹 · 데스크톱 앱 · IDE · CLI) 이 저장소를 열기만 하면 그대로 작동합니다.

| | 세션에서 직접 (기본 · 추가 비용 0) | GitHub Action (선택 · 완전 자동) |
|---|---|---|
| 수집 | `/ingest` | inbox push 시 자동 |
| 정제 | `/dream` | 주 1회 야간 자동 |
| 검색 | `/recall <질문>` | — |
| 필요한 것 | **없음** — 클로드 세션만 있으면 됨 | `ANTHROPIC_API_KEY` 시크릿 (1회 설정) |

> 즉, API 키나 GitHub 설정을 **전혀 하지 않아도** 모든 기능이 동작합니다.
> GitHub Action은 "내가 아무것도 안 해도 알아서 돌아가는" 편의를 원할 때만 켜는 **선택 사항**이며,
> 키가 없으면 워크플로는 **비용 없이 조용히 건너뜁니다.**

---

## 🚀 3단계 사용법

### 1단계 — 무가공 데이터 축적 (Data Dumping)
연구 자료, 웹 스크랩, 메모, PDF 발췌, 회의록… **무엇이든** `brain/inbox/`에 그대로 넣습니다.
폴더를 나누거나 이름을 고민할 필요가 전혀 없습니다.

```bash
# 예: 아무 메모나 던져넣기
echo "오늘 읽은 논문 요약 ..." > brain/inbox/$(date +%F)-아무거나.md
```

### 2단계 — 자가 진화형 위키 구축
클로드 세션에서 한 줄만 실행하면, inbox의 모든 지식을 스캔해 주제별 문서로 정리하고,
서로의 연결고리를 `[[위키링크]]`로 이어 **지식 지도(`brain/wiki/MAP.md`)** 를 만듭니다.

```text
/ingest
```

### 3단계 — 원하는 답을 몇 초 만에
질문하면 클로드는 먼저 작은 **MAP 인덱스**만 읽어 위치를 찾고, 관련 문서 1~3개만 펼쳐 답합니다.
그래서 데이터가 40만 단어를 넘어도 검색이 느려지지 않습니다.

```text
/recall 작년에 정리한 마케팅 전략의 핵심이 뭐였지?
```

---

## 🌙 드림 시퀀스 (Dream Sequence) — 이 시스템의 심장

> **클로드가 스스로 지식을 검토하고 정제합니다.** 다음을 수행하고 변경 사항을 기록·커밋합니다:

1. **모순 탐지** — 서로 충돌하는 주장을 찾아 신뢰도·최신성 기준으로 정리
2. **중복 병합** — 겹치는 주제를 하나의 정본(canonical)으로 통합
3. **구식 정리** — 더 이상 유효하지 않은 지식을 `brain/archive/`로 이동(삭제 아님)
4. **통찰 합성** — 여러 주제를 가로지르는 **새로운 연결**을 발견해 `brain/insights/INSIGHTS.md`에 누적
5. **재색인** — `[[위키링크]]`와 `MAP.md`를 다시 정리하고, 모든 변경을 `.state/dream-log.md`에 기록

이 과정이 반복되며 **낡은 지식은 걸러지고 새로운 통찰이 쌓여**, 시스템의 정확도와 성능이 시간이 갈수록 극대화됩니다.

### ▶ 실행 방법 — 두 가지 길

**길 1 (기본 · 추가 비용 0 · 권장):** 아무 클로드 세션에서나 직접 실행
```text
/dream
```
설정도, API 키도, GitHub도 필요 없습니다. 생각날 때(또는 자료를 한참 넣은 뒤) 한 번 돌리면 됩니다.

**길 2 (선택 · 완전 자동):** 잠든 사이에도 알아서 돌게 하고 싶다면
1. [Anthropic Console](https://console.anthropic.com/)에서 API 키 발급
2. 저장소 → **Settings → Secrets and variables → Actions → New repository secret**
3. 이름 `ANTHROPIC_API_KEY`, 값에 API 키 붙여넣기 → 끝
4. **매주 일요일 새벽**(KST) 자동 정제됩니다. 비용을 아끼려 빈도를 주 1회로 잡았고, `.github/workflows/dream-sequence.yml`의 `cron`만 바꾸면 조정됩니다. **Actions 탭 → Run workflow**로 즉시 실행도 가능.

> 키를 설정하지 않으면 자동화는 **비용 없이 그냥 건너뜁니다.** 손해는 전혀 없습니다.

---

## 📂 디렉터리

```
brain/
├── inbox/          # 🗑️ 여기에 무엇이든 던지세요
├── wiki/
│   ├── MAP.md      # ⭐ 지식 지도 (검색 인덱스)
│   └── topics/     # 주제별 문서 (상호 연결)
├── insights/INSIGHTS.md   # 💡 드림 시퀀스가 발견한 통찰
├── archive/        # 🗄️ 폐기된 구식 지식 (보존)
└── .state/         # 처리 기록 · 드림 로그
```

명령의 상세 동작은 [`.claude/commands/`](.claude/commands/)에, 전체 운영 규칙은 [`CLAUDE.md`](CLAUDE.md)에 정의되어 있습니다.

---

## 🔧 명령 모음

| 명령 | 설명 |
|------|------|
| `/ingest` | inbox를 스캔해 위키·지식지도 생성/갱신 |
| `/dream` | 드림 시퀀스 정제를 지금 즉시 실행 |
| `/recall <질문>` | 지식 베이스에서 답을 빠르게 검색 |
| `/brain-status` | 시스템 통계 요약 |
| `bash scripts/brain.sh` | 단어 수·주제 수 등 빠른 통계 |

---

## 🧩 부가: everything-claude-code 플러그인

이 저장소는 제2의 뇌와 **별개로**, [`everything-claude-code`](https://github.com/affaan-m/everything-claude-code) 플러그인도 함께 설정되어 있습니다 — 서브에이전트·스킬·자동화 훅(코드 리뷰, TDD, 보안 스캔, 포매팅, 다국어 패턴) 모음입니다.

프로젝트 레벨 `.claude/settings.json`이 마켓플레이스를 등록하고 플러그인을 활성화하므로, `/plugin` 명령을 수동으로 실행할 필요가 없습니다. Claude Code 시작 시 프로젝트 신뢰 프롬프트만 승인하면 됩니다.

```text
/plugin list                 # 활성 플러그인 확인
/plugin marketplace list     # 등록된 마켓플레이스 확인
```

수동 설치(프로젝트 설정을 끈 경우):
```text
/plugin marketplace add affaan-m/everything-claude-code
/plugin install everything-claude-code@everything-claude-code
```

- `.claude/settings.json` — 공유 플러그인/마켓플레이스 설정 (커밋됨)
- `.claude/settings.local.json` — 개발자별 오버라이드 (gitignore)
- Upstream: <https://github.com/affaan-m/everything-claude-code>

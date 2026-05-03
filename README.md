# @알쓸지잡10 — 인포그래픽 릴스 MVP 파이프라인

주제 한 줄을 입력하면 → Claude API가 인포그래픽 JSON을 생성하고 → Puppeteer가
1080×1920 캐러셀 이미지(표지/본문/CTA 3장)를 로컬에 떨어뜨리는 최소 파이프라인.

## 디자인 시스템

- 다크 모드 (`#0a0a0f` 배경) + 선셋 오렌지 (`#f97316`) 강조
- 도트 그리드 패턴 + 라디얼 글로우 오브
- Noto Sans KR (Google Fonts)
- 5종 카드: cover / ranking / checklist / comparison / cta

## 빠른 시작

```bash
# 1. 의존성 설치 (Puppeteer가 Chromium ~170MB 다운로드)
npm install

# 2. API 키 설정
cp .env.example .env
# .env 파일을 열어 ANTHROPIC_API_KEY 입력

# 3. 한 주제로 end-to-end 실행
node src/pipeline.js "2026 대기업 신입 초봉 티어"
```

성공 시 `output/` 디렉터리에 다음 파일이 생성됩니다:

```
output/
├── <topic_id>.json              # Claude가 생성한 콘텐츠 JSON
├── <topic_id>_01_cover.jpg      # 표지 카드
├── <topic_id>_02_<type>.jpg     # 본문 카드 (ranking/checklist/comparison)
└── <topic_id>_03_cta.jpg        # CTA 카드
```

## 카드 타입별 테스트 주제

3종 본문 템플릿이 모두 잘 렌더링되는지 확인하려면:

```bash
node src/pipeline.js "2026 대기업 신입 초봉 티어"          # ranking
node src/pipeline.js "20대 모르면 손해보는 정부지원금"    # checklist
node src/pipeline.js "네이버 vs 카카오 신입 복지 비교"   # comparison
```

## 배치 실행 (10~30개 한 번에)

`data/topics.json`에 주제 배열을 넣고 한 번에 처리합니다.

```bash
# 기본: data/topics.json 의 모든 주제 처리
npm run batch

# 다른 주제 파일 사용
node src/batch.js my-topics.json

# 첫 3개만 (테스트/예산 절약용)
node src/batch.js --limit 3

# 이전 실행에서 실패한 항목 재시도
node src/batch.js --retry-errors
```

**상태 추적**: `output/batch-state.json`에 주제별 진행 상태가 저장됩니다.
- `pending` → `json_done` → `done`
- 실패 시: `error_json` (Claude 호출 실패) / `error_image` (렌더링 실패)
- 재실행 시 `done` 항목은 건너뜀 → API 토큰/시간 절약

**한 Puppeteer 브라우저 인스턴스 재사용**: 30개 주제를 처리해도 Chromium은 1번만
launch → 약 60초 절약.

**Ctrl-C 중단**: 현재 처리 중인 주제까지 마치고 깨끗이 종료. 다음 실행 시 이어서.

`data/topics.json` 예시:
```json
[
  "2026 대기업 신입 초봉 티어표",
  "인서울 대학교 등록금 순위 TOP 15",
  "20대 모르면 손해보는 정부지원금"
]
```

## Instagram 자동 업로드

생성된 이미지를 Instagram 비즈니스 계정에 캐러셀 게시물로 자동 발행합니다.

### 사전 세팅 (처음 1회, ~30분)

`docs/instagram-setup.md` 참고. 필요한 것:
- Instagram 비즈니스/크리에이터 계정 + Facebook 페이지 연결
- Meta 개발자 앱 + Graph API 권한 5종
- 60일 long-lived access token + Instagram Business Account ID
- imgbb 무료 API 키 (이미지를 IG가 fetch할 수 있게 공개 URL로 호스팅)

`.env` 채우기:
```
IMGBB_API_KEY=...
IG_ACCESS_TOKEN=...
IG_USER_ID=17841400000000000
```

### 사용

```bash
# 특정 토픽 업로드 (output/{topic_id}.json + 이미지 3장 필요)
npm run upload <topic_id>

# output/의 모든 미업로드 토픽 자동 발견 + 업로드
npm run upload -- --all

# 처음 5개만 (rate limit 안전 / 신규 계정)
npm run upload -- --all --limit 5

# imgbb까지만 검증 (IG 발행 안 함)
node src/upload-instagram.js <topic_id> --dry-run

# 60일 토큰 갱신 (월 1회 권장)
npm run refresh-token
```

### 처리 흐름

1. `output/{topic_id}.json` + 이미지 파일 존재 확인
2. 각 이미지를 imgbb로 업로드 → 공개 HTTPS URL 3개 받음
3. IG Graph API: 자식 컨테이너 3개 → 캐러셀 컨테이너 1개 → 발행
4. `output/upload-state.json`에 `media_id`, `permalink`, 타임스탬프 저장
5. 다음 실행 시 status=`uploaded`인 토픽은 자동 스킵 (중복 방지)

### 한도 / 안전 가이드

- **24시간당 50개 게시물** (신규 계정 25개부터). 점진적으로 늘리세요:
  - Week 1: 3개/일 → Week 5+: 30개/일
- 시간당 200 API 호출. 캐러셀 1개 = ~10 호출 → 시간당 ~20개 안전.
- 같은 IP/계정에서 갑자기 30개 이상 = 스팸 판정 위험.

자세한 설정/트러블슈팅은 `docs/instagram-setup.md` 참고.

## 환경 변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `ANTHROPIC_API_KEY` | ✅ | Anthropic Console에서 발급 |
| `MODEL` | — | 기본값 `claude-sonnet-4-6` |
| `DEFAULT_HANDLE` | — | 카드에 표시될 핸들. 기본값 `@알쓸지잡10` |
| `PUPPETEER_SKIP_DOWNLOAD` | — | `true` 설정 시 Chromium 다운로드 스킵 |
| `PUPPETEER_EXECUTABLE_PATH` | — | 시스템 Chrome 경로 (스킵 시 필수) |

## 프로젝트 구조

```
.
├── package.json
├── .env.example
├── README.md
├── templates/
│   ├── cover.hbs            # 표지
│   ├── ranking.hbs          # 순위형
│   ├── checklist.hbs        # 체크리스트
│   ├── comparison.hbs       # 비교형 (3열 테이블)
│   └── cta.hbs              # CTA
├── data/
│   └── topics.json          # 배치 처리할 주제 리스트
├── docs/
│   └── instagram-setup.md   # Meta 앱 등록 + 토큰 발급 walkthrough
├── src/
│   ├── prompts/
│   │   └── content-generator.md  # 시스템 프롬프트
│   ├── generate-content.js  # 주제 → JSON (Claude + web_search)
│   ├── render-images.js     # JSON → 이미지 (Handlebars + Puppeteer)
│   ├── pipeline.js          # 단일 주제 CLI
│   ├── batch.js             # 배치 실행기 (상태 추적 + 재개)
│   ├── image-host.js        # imgbb 업로드 (공개 URL 발급)
│   ├── instagram.js         # Instagram Graph API 클라이언트
│   ├── upload-instagram.js  # 캐러셀 업로드 러너
│   └── refresh-token.js     # 60일 토큰 갱신 유틸
└── output/                  # JSON, 이미지, batch-state.json, upload-state.json
```

## 동작 원리

### 1. 콘텐츠 생성 (`src/generate-content.js`)

- `claude-sonnet-4-6` + `web_search_20260209` 도구 (최대 5회)
- 시스템 프롬프트는 `cache_control: ephemeral`로 캐싱 → 30개 배치 시 ~90% 캐시 히트
- `pause_turn` (web_search 한도) 발생 시 자동으로 재개

### 2. 이미지 렌더링 (`src/render-images.js`)

- Handlebars로 5개 템플릿 컴파일 (시작 시 1회)
- `slide.type`에 따라 cover/ranking/checklist/comparison/cta 중 자동 선택
- Puppeteer headless Chromium, 1080×1920 viewport
- `document.fonts.ready` await 후 200ms 추가 대기 (한글 폰트 로드 보장)
- JPEG 품질 92로 저장 (Instagram 호환)

### 3. 파이프라인 (`src/pipeline.js`)

```
주제 입력 → generateContent() → {topic_id}.json 저장 → renderImages() → 이미지 N장
```

## 알려진 제약 / 다음 단계

- 인스타그램 업로드 미구현 (Instagram Graph API 별도 작업)
- Google Sheets 연동 미구현
- 30개 배치 처리 미구현 (현재는 1개씩만)
- htmlcsstoimage.com 대신 로컬 Puppeteer 사용 → 비용 0, 속도 ↑

## 문제 해결

### Puppeteer Chromium 다운로드 실패

```bash
# 방법 1: 시스템 Chrome 사용
echo "PUPPETEER_SKIP_DOWNLOAD=true" >> .env
echo "PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome" >> .env
npm install --ignore-scripts

# 방법 2: 한글 폰트 누락 (Linux)
sudo apt-get install -y fonts-noto-cjk
```

### 한글이 □ 박스로 출력됨

- 시스템에 한글 폰트가 없는 경우. Linux: `fonts-noto-cjk` 설치
- Google Fonts 로드 실패 가능성. `.env`에 프록시 설정 확인

### Claude가 마크다운 펜스를 추가함

- `extractJsonFromText()`가 자동으로 ` ```json ... ``` ` 펜스를 제거합니다.
- 그래도 실패하면 `output/<topic_id>.json` 직전에 raw 응답 출력 추가 권장

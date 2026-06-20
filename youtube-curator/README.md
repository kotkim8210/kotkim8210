# 🎯 YouTube 큐레이터 — CC 떡상 영상 → 숏츠 자동 편집

내가 안 들여다봐도, **매일 자동으로** 내 카테고리에서 떡상한 영상을 찾아
**롱폼 → 숏츠**로 편집해 줍니다. (분석 사이트 "danbi"가 보여주는 *발굴* + 우리 `video-editor`의 *편집*을 합친 것)

```
발굴(CC 떡상) → ⚖️ 권리 게이트(CC만) → 다운로드 → 하이라이트 선택(LLM/휴리스틱)
            → 롱폼→숏츠 편집(9:16·자막·무음컷) → 결과 + 출처(CC) 기록
```

---

## ⚖️ 가장 중요 — 저작권 (채널 정지 방지)
- **남의 떡상 영상을 그대로 잘라 재업로드하면 = 저작권 스트라이크 → 채널 정지.**
- 그래서 이 도구는 **편집·업로드 대상을 Creative Commons(CC) 라이선스 영상으로 한정**합니다.
  yt-dlp 의 `license` 필드로 `Creative Commons Attribution license (reuse allowed)` 인지
  **이중 확인**한 것만 통과시키고, 결과마다 `*.txt`에 **출처표기**(CC 의무)를 만들어 둡니다.
- *발굴(분석)*은 모든 영상에 해도 합법(공개 데이터)이지만, *편집*은 권리 있는 것만.
- ⚠️ 자동 **업로드는 일부러 안 합니다.** 결과 숏츠를 보고 사람이 올리세요(잘못된 자동 업로드 방지).

## 자동 실행 ('안 봐도 알아서')
- `.github/workflows/curate.yml` 이 **매일 19:50 KST** 자동 실행 → 결과(숏츠 + 대시보드)를 **아티팩트**로 저장.
- 수동 실행: 깃허브 Actions 탭 → *YouTube 큐레이터* → **Run workflow** (카테고리 slug 지정 가능).
- 필요한 secrets (Settings → Secrets → Actions):
  - `YT_COOKIES` *(권장)* — YouTube 쿠키(`cookies.txt` 내용). 데이터센터 IP의 'bot 확인' 벽을 100% 우회.
    (없어도 android 클라이언트로 상당수 통과하지만, 안정적이려면 쿠키 권장.)
  - `ANTHROPIC_API_KEY` *(선택)* — 있으면 Claude 가 가장 후킹되는 하이라이트 구간을 고름. 없으면 휴리스틱.

## 카테고리 추가
`categories.yaml` 만 고치면 됩니다. (검색어·길이·자막언어·도메인어휘)
```yaml
- name: 먹방
  slug: mukbang
  query: 먹방 asmr
  lang: ko
  hint: 먹방,맛집,리뷰
  short_len: 45
  caption: "🍜 #먹방 #shorts"
```
기본 포함: **축구 월드컵**, **쇼핑 숏츠**.

## 수동 실행 (로컬)
```bash
pip install -r youtube-curator/requirements.txt
# 발굴만 미리 보기
python youtube-curator/discover.py "월드컵 축구 하이라이트" --want 3
# 한 카테고리 풀 실행 → output/ 에 숏츠 생성
python youtube-curator/curate.py --only worldcup --per-category 1
```
> 이 저장소의 샌드박스처럼 TLS 프록시 뒤라면 `--insecure` 를 붙이세요(개발 전용).

## 구성
| 파일 | 역할 |
|------|------|
| `discover.py` | CC 떡상 발굴 + 권리 게이트(YouTube API 키 불필요) |
| `curate.py` | 발굴→다운로드→하이라이트→9:16 숏츠 편집→매니페스트 오케스트레이션 |
| `channels.py` | 채널 스냅샷 수집 + 랭킹 + 성장/조회수 예측 |
| `shorts2shorts.py` / `shorts_sources.yaml` | 틱톡/샤오홍수 → 한국 쇼츠(카테고리별 떡상 공식·정밀 튜닝 노브) |
| `upload.py` | 검수 후 반자동 업로드(YouTube OAuth, 기본 비공개·공개는 확인 필수) |
| `categories.yaml` / `channels.yaml` | 카테고리 설정 / 추적 채널(수동) 설정 |
| `dashboard/index.html` | 분석 대시보드(숏츠 + 채널 분석 탭) |
| `../video-editor/` | 실제 편집 엔진(9:16 `--fit cover`·자막·번역·무음컷) 재사용 |
| `../.github/workflows/curate.yml` | 매일 19:50 KST 크론 자동화 |
| `output/manifest.json` · `channels.json` | 숏츠·출처·떡상점수 / 채널 랭킹·예측 데이터(대시보드용) |

## 한국어 자막 자동 번역 (분위기 반영) ✅
외국어 CC 원본은 **영상 분위기에 맞춰** 한국어 자막으로 자동 번역됩니다(`categories.yaml`의 `translate: true`).
- 코믹/예능 → 센스있고 요즘 유행하는 표현·밈 감성
- 감동/스토리 → 감정선이 살아있는 단어
- 스포츠/정보 → 짧고 임팩트 있게

LLM 이 먼저 분위기/장르를 파악한 뒤 그에 맞는 어휘로 번역합니다. (`ANTHROPIC_API_KEY` 필요, 없으면 원문 유지)
기본 **축구 월드컵** 카테고리는 영어 CC 영상이 풍부해 `lang: en, translate: true` 로 설정돼 있습니다.

## 채널 분석 — 랭킹 + 성장 예측 (danbi 스타일) ✅
`channels.py` 가 채널별 **구독자 + 최근 영상 성과**를 매일 스냅샷으로 모아(`output/channels_history.jsonl`):
- **랭킹**: 구독자순 + 급상승(일 성장순)
- **예측**: 스냅샷 2일+ 쌓이면 일 성장률로 **7/30일 구독자 예측**, 최근 영상 떡상 속도로 **주간 조회수 예측**
  (스냅샷이 쌓일수록 정확해짐 — danbi 가 2025년부터 모은 것과 같은 원리. 첫날은 "데이터 축적 중")

**추적 채널 = 수동 + 자동**
- 수동: `channels.yaml` 에 **내 채널 + 경쟁사**를 넣음
- 자동: 큐레이션(발굴)에서 나온 **CC 창작자 채널**이 `output/auto_channels.json` 에 자동 추가돼 랭킹이 알아서 늘어남

```bash
python youtube-curator/channels.py --collect    # 스냅샷 1회 수집 + 랭킹·예측 갱신 → output/channels.json
```

## 대시보드 ✅ (탭 2개)
`dashboard/index.html` — 정적 분석 페이지. **📹 만든 숏츠**(출처·떡상점수·CC 배지) + **📊 채널 분석**(랭킹·구독자·일성장·7/30일 예측·최근영상 주간예상) 탭.
```bash
# 로컬에서 보기 (서버로 띄워야 fetch 가 됨)
python -m http.server -d youtube-curator/dashboard 8000   # → http://localhost:8000
```
- 매일 크론 아티팩트(`curator-<id>`)에 대시보드 + 데이터(`manifest.json`·`channels.json`)가 같이 들어갑니다. 받아서 `index.html` 열면 그날 결과.
- 데이터 없으면 `*.sample.json` 으로 미리보기.

## 쇼츠 → 쇼츠 (틱톡/샤오홍수 → 한국 쇼츠) ⚡ ✅
중국 쇼츠(틱톡·샤오홍수)의 **최신 떡상 소재**를 받아 **한국어 번역 + 카테고리 공식대로 재편집**해 빠르게 뽑습니다.
"스피드가 생명" — 트렌드는 늦으면 끝나므로 **링크 받으면 즉시 처리**가 핵심.

- **카테고리별 떡상 공식**: `shorts_sources.yaml` 의 `formula` (먹방/펫/꿀팁/신기/중드 등 — 주제마다 공식이 달라
  LLM 편집기가 그 공식대로 **쓸 구간·순서·후킹·자막 톤**을 결정). 성과 보며 `formula` 한 줄만 고쳐 계속 다듬습니다.
  - **정밀 튜닝 노브**(LLM 편집기가 실제로 읽음): `hook_sec`(훅 길이) · `target_cuts`(컷 수=호흡) ·
    `caption_chars`(자막 글자수) · `pace`(호흡) · `retention`(체류 전술) · `cta`(루프/저장 유도).
    **먹방(`mukbang`)** 카테고리가 정밀 튜닝 레퍼런스 — 사운드 큰 '한 입'을 훅으로, 10컷 빠른 호흡,
    8자 의성어 자막, 마지막을 또 한 입으로 끝내 **루프(반복재생)**. 다른 카테고리도 이 구조로 숫자만 바꿔 튜닝.
- **후킹 앞배치**: 공식에 맞는 훅 구간을 **맨 앞**으로 재정렬(ffmpeg) → 9:16 + 한국어 자막(GmarketSans).
- **입력 = 둘 다**: ① `shorts_sources.yaml`의 `sources`(크리에이터 워치리스트, 6시간 크론 자동) ② **떡상 링크 즉시 처리**.
```bash
# 떡상 링크 즉시 처리(가장 빠름) — 카테고리 공식 적용
python youtube-curator/shorts2shorts.py --only mukbang --urls "https://www.tiktok.com/@x/video/123"
# GitHub Actions: '쇼츠→쇼츠' 워크플로 → Run workflow 에 urls 붙여넣으면 즉시 실행
```
- ⚖️ **권리**: 틱톡/샤오홍수는 CC 아님 → 재업로드 위험. 출처표기(`*.txt`)·번역·재편집 변형 전제, 본인 권리/허락 소재 권장.
- 봇 차단 우회: secrets `TIKTOK_COOKIES`(또는 `YT_COOKIES`) 권장.

## 떡상 점수
`떡상 = 조회수 / 업로드 후 경과일` (하루 평균 조회수). 신선도(`max_age_days`)·길이 조건으로 트렌드만 추립니다.

## 검수 후 반자동 업로드 (YouTube OAuth) ✅
만든 숏츠를 **사람이 검수한 뒤** YouTube 에 올리는 `upload.py` (YouTube Data API v3 OAuth).
> ⚠️ **완전 자동 공개 업로드는 일부러 안 합니다.** 기본 공개범위 `private`, 공개(public)는 `--confirm` 명시 필수,
> 비-CC 소재(쇼츠→쇼츠)는 비공개가 아니면 추가 `--confirm` 요구 → 잘못된 자동 재업로드 방지.
```bash
python youtube-curator/upload.py --list                          # ① 검수: 안 올린 숏츠 목록(CC/비-CC 배지)
python youtube-curator/upload.py --upload mukbang_xxx.mp4 --privacy unlisted   # ② 콕 집어 미공개 업로드
python youtube-curator/upload.py --upload 0 --privacy public --confirm         # ③ 검수 끝 → 공개
```
- **자격증명(절대 커밋 금지, `output/*.json` gitignore)**: Google Cloud Console → OAuth 클라이언트 ID(**데스크톱 앱**) JSON 을
  `--client-secret`(또는 env `YT_OAUTH_CLIENT_SECRET_FILE`)으로 지정. 첫 실행 시 브라우저 동의 → 토큰 자동 저장/갱신(`output/youtube_token.json`).
- **설명란 = 만들 때 써둔 `.txt`**(캡션 + CC/출처표기)를 그대로 사용 → CC 출처표기 의무 자동 충족.
- **GitHub Actions**: `upload.yml`(수동 `workflow_dispatch` 전용, **크론 없음**). 로컬 1회 인증 토큰을 secret `YT_OAUTH_TOKEN` 으로 주입.

## 다음 단계(선택)
- TOP 1200 대규모 랭킹(대형 채널 시드 + 쿠키 필요)

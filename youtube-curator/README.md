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

## 떡상 점수
`떡상 = 조회수 / 업로드 후 경과일` (하루 평균 조회수). 신선도(`max_age_days`)·길이 조건으로 트렌드만 추립니다.

## 다음 단계(선택)
- 검수 후 **반자동 업로드**(YouTube OAuth)
- TOP 1200 대규모 랭킹(대형 채널 시드 + 쿠키 필요)

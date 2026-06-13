# Google Sheets 연동 사전 세팅 가이드

`npm run sheets`로 Google Sheets 를 콘텐츠 입력 DB 로 사용하려면 아래 외부 자격 증명이 필요합니다.

| 환경변수 | 의미 | 어디서 받나 |
|----------|------|-------------|
| `GOOGLE_SHEETS_ID` | 스프레드시트 ID | URL 의 `/d/` 와 `/edit` 사이 |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | service account JSON 파일 **경로** | GCP Console (아래 단계) |

소요 시간: 처음 세팅 약 15분.

---

## 1단계 — GCP 프로젝트 만들기

1. https://console.cloud.google.com 로그인
2. 상단 프로젝트 드롭다운 → **New Project** (예: `kotkim-sheets`)
3. 좌측 메뉴 → **APIs & Services** → **Library**
4. 검색: `Google Sheets API` → **Enable**

---

## 2단계 — Service Account 만들기

1. **APIs & Services** → **Credentials**
2. 상단 **+ CREATE CREDENTIALS** → **Service account**
3. 이름: 자유 (예: `kotkim-runner`) → **Create and Continue**
4. 역할은 **Skip** (Sheets 권한은 시트 공유로 부여)
5. **Done**
6. 생성된 서비스 계정 클릭 → **KEYS** 탭 → **ADD KEY** → **Create new key** → **JSON** → 다운로드

JSON 파일을 안전한 위치에 저장. 예: `/home/user/kotkim8210/credentials/service-account.json` (이 디렉터리는 `.gitignore` 에 등록됨).

서비스 계정 이메일 주소 메모 — 형태: `kotkim-runner@<project>.iam.gserviceaccount.com`

---

## 3단계 — Google Sheet 만들고 공유

1. https://sheets.google.com → 새 시트 생성 (예: `kotkim 콘텐츠 DB`)
2. 시트 이름은 **Sheet1** (또는 한국어 `시트1`이 기본일 수 있음 — `Sheet1` 로 변경하세요)
3. 우측 상단 **공유** → 위에서 받은 service account 이메일 입력 → **편집자** 권한
4. URL 에서 SHEET_ID 추출:
   ```
   https://docs.google.com/spreadsheets/d/AbCdEf123...XyZ/edit
                                           ^^^^^^^^^^^^^^^^
                                           이 부분이 GOOGLE_SHEETS_ID
   ```

---

## 4단계 — `.env` 채우기

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
IMGBB_API_KEY=...

GOOGLE_SHEETS_ID=AbCdEf123...XyZ
GOOGLE_SERVICE_ACCOUNT_JSON=./credentials/service-account.json

# Instagram 발행을 같이 하려면 (선택)
IG_ACCESS_TOKEN=...
IG_USER_ID=17841400000000000
```

---

## 5단계 — 실행 + 시트 자동 초기화

```bash
# 1회 실행 (대기 row 0개여도 헤더 생성됨)
npm run sheets -- --no-publish --limit 0
```

처음 실행하면:
- 시트 1행에 12개 컬럼 헤더가 자동 입력됨 (topic_id, category, ..., processed_at)

이후 사용자는 시트의 D열(topic_title)에 주제를, J열(status)에 `pending` 입력 → 다음 실행 시 자동 처리.

---

## 시트 컬럼 구조

| 열 | 이름 | 방향 | 설명 |
|----|------|------|------|
| A | topic_id | 시스템 쓰기 | Claude 가 생성한 snake_case ID |
| B | category | 시스템 쓰기 | 취업/연봉 / 대학/입시 / ... |
| C | card_type | 시스템 쓰기 | ranking / checklist / comparison |
| **D** | **topic_title** | **사용자 입력** | "2026 대기업 신입 초봉" 같은 주제 |
| E | json_data | 시스템 쓰기 | 전체 JSON (디버깅용) |
| F | cover_img_url | 시스템 쓰기 | imgbb 공개 URL |
| G | body_img_url | 시스템 쓰기 | imgbb 공개 URL |
| H | cta_img_url | 시스템 쓰기 | imgbb 공개 URL |
| I | caption | 시스템 쓰기 | IG 캡션 (제목+본문+해시태그) |
| **J** | **status** | **사용자/시스템** | pending → processing → images_done → uploaded |
| K | error_message | 시스템 쓰기 | 실패 시 에러 또는 IG permalink |
| L | processed_at | 시스템 쓰기 | ISO 8601 |

### Status 흐름

```
사용자 입력:  pending
              ↓
시스템:      processing  (작업 중 표시)
              ↓
시스템:      images_done  (--no-publish 시 종착역)
              ↓
시스템:      uploaded     (IG 발행 완료)

실패 시:     error_json | error_image | error_upload
```

재실행 시 `pending` 만 자동 픽업. `error_*` 는 사용자가 J열을 다시 `pending` 으로 바꿔야 재시도.

크래시로 `processing` 상태로 멈춘 row 는 다음 실행 시작 시 자동으로 `pending` 으로 리셋됩니다 (단일 러너 가정).

---

## 사용 예시

```bash
# 일회 실행: 모든 pending row 처리
npm run sheets

# imgbb 까지만 (IG 발행은 직접 검토 후 별도)
npm run sheets -- --no-publish

# 한 번에 3개만 (rate limit 안전)
npm run sheets -- --limit 3

# 5분마다 자동 폴링 (상시 실행)
npm run sheets -- --watch --interval 300

# 1시간마다 폴링, 한 사이클당 5개 (조심스런 운영)
npm run sheets -- --watch --interval 3600 --limit 5
```

---

## cron 으로 스케줄링 (production)

`--watch` 대신 cron 으로 주기 실행하면 메모리 누수 / 프로세스 관리 부담 없음.

```bash
# 매시 0분에 최대 3개 처리
0 * * * * cd /home/user/kotkim8210 && /usr/bin/node src/sheets-runner.js --limit 3 >> /var/log/kotkim.log 2>&1

# 평일 9시/12시/15시/18시 각 5개씩 → 하루 최대 20개 (Week 4~5 권장)
0 9,12,15,18 * * 1-5 cd /home/user/kotkim8210 && /usr/bin/node src/sheets-runner.js --limit 5 >> /var/log/kotkim.log 2>&1
```

---

## 트러블슈팅

| 증상 | 원인 / 해결 |
|------|------------|
| `403 The caller does not have permission` | 시트를 service account 이메일에 **편집자** 권한으로 공유 안 함 |
| `404 Requested entity was not found` | `GOOGLE_SHEETS_ID` 오타 / 잘못된 시트 |
| `400 Unable to parse range: Sheet1` | 시트 이름이 `Sheet1` 아님 → 한국어 `시트1` 등이면 시트 이름을 `Sheet1` 로 변경 (또는 `src/sheets-client.js` 의 `SHEET_NAME` 수정) |
| `ENOENT: no such file or directory` | `GOOGLE_SERVICE_ACCOUNT_JSON` 경로 잘못. 절대경로 또는 프로젝트 루트 기준 상대경로 |
| 헤더가 임의로 변경됨 | `ensureHeaders` 가 다시 정상화함. 다음 실행 시 자동 복원 |

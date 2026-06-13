# Instagram 업로드 사전 세팅 가이드

`npm run upload`로 Instagram에 캐러셀 게시물을 자동 발행하려면 아래 외부 자격 증명이 필요합니다.

| 환경변수 | 의미 | 어디서 받나 |
|----------|------|-------------|
| `IMGBB_API_KEY` | imgbb 이미지 호스팅 키 | https://api.imgbb.com/ |
| `IG_ACCESS_TOKEN` | 60일 long-lived user access token | Graph API Explorer (아래 단계) |
| `IG_USER_ID` | Instagram Business Account ID (17자리 숫자) | Graph API 호출로 확인 (아래 단계) |

소요 시간: 처음 세팅 약 30분. 매월 1회 토큰 갱신 필요 (`npm run refresh-token`).

---

## 0단계 — 정책 컴플라이언스 (먼저 읽기)

"인스타가 자동 업로드를 문제 삼지 않나?" 자주 묻습니다. 결론: **공식 Graph API로 본인 비즈니스 계정에 발행하는 것은 Meta가 명시적으로 허용하는 정상 경로**입니다. 단, 세 가지를 구분해야 합니다.

| 구분 | 허용 ✅ | 금지 ❌ |
|------|--------|--------|
| 접근 방식 | 공식 Graph API (이 가이드가 쓰는 방식) | 비공식 봇·브라우저 자동화·스크레이퍼 (계정 영구정지 위험) |
| 권한 범위 | **본인 계정**만 발행 → 앱 리뷰 불필요, Development 모드 유지 가능 | 남의 계정을 대행 발행 → 앱 리뷰 + Advanced Access 필요 (2~4주) |
| 발행 속도 | rate limit 내 점진 확대 | 신규 계정 즉시 대량 발행 → 공식 API여도 스팸 시스템에 잡힘 |

**근거**: Meta Platform Terms — 승인된 API를 통한 자동화는 rate limit 준수 시 compliant. 본인 계정만 다루는 앱은 App Review 면제, Development 모드에서 운영 가능 (단, 인스타/페이스북 계정이 앱에 **Admin·Developer·Tester 역할로 등록**돼 있어야 함 → 2단계 참고).

**즉**: 이 가이드 그대로 따르면 정책 위반이 아니며, 인스타가 문제 삼지 않습니다. 다만 "공식 API = 도달 보장"은 아니므로 속도 조절은 별개로 지켜야 합니다 (마지막 "한도" 섹션 참고).

---

## 1단계 — Instagram 비즈니스 계정 + Facebook 페이지 연결

Instagram Graph API는 **개인 계정에선 작동하지 않습니다.** 비즈니스(또는 크리에이터) 계정으로 전환 필요.

1. Instagram 앱 → 설정 → 계정 → "프로페셔널 계정으로 전환" → 비즈니스 또는 크리에이터 선택
2. Facebook 페이지가 없다면 https://www.facebook.com/pages/create 에서 새로 생성
3. Instagram 앱에서 설정 → 계정 → "페이지 연결" → 위에서 만든 Facebook 페이지 선택

**연결 확인**: Facebook 페이지 → 설정 → Linked accounts → Instagram 에서 계정이 보이면 OK.

---

## 2단계 — Meta 개발자 앱 등록

1. https://developers.facebook.com 로그인 → **My Apps** → **Create App**
2. 앱 타입: **Business** 선택
3. 앱 이름은 자유 (예: `kotkim-uploader`)
4. 생성 후 좌측 메뉴 → **Add Product** → **Instagram Graph API** 추가
5. **앱 역할 등록 (중요)**: 대시보드 → **Roles → Roles** (또는 **Settings → Roles**) →
   - 본인 Facebook 계정을 **Admin** 또는 **Developer**로 추가
   - **Roles → Instagram Testers** 에서 발행 대상 인스타 계정 추가 → Instagram 앱(@계정 → 설정 → 앱·웹사이트 → 초대) 에서 초대 수락
6. **앱은 Development 모드로 유지**: 상단 토글이 "In development"이면 OK. Live 모드로 바꿀 필요 없습니다 — 본인 계정 발행은 Dev 모드에서 정상 동작.

본인 계정만 다루는 한 별도 권한 신청 절차(앱 리뷰)는 필요 없습니다. **단, 위 5·6번을 빠뜨리면 토큰은 받아도 발행 단계에서 `#200 permission` 또는 빈 응답이 납니다** — 앱이 "내가 관리하는 계정"으로 인지해야 권한이 통과되기 때문.

---

## 3단계 — short-lived token 받기 (Graph API Explorer)

1. https://developers.facebook.com/tools/explorer 접속
2. 우측 상단에서 본인 앱 선택
3. **Generate Access Token** 클릭 → 본인 Facebook 계정 권한 부여
4. **권한** 섹션에서 다음을 모두 추가하고 다시 토큰 생성:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
   - `business_management`
5. 생성된 토큰을 임시로 메모해 둡니다 (이건 1시간만 유효한 short-lived).

---

## 4단계 — 60일 long-lived token 으로 교환

short-lived 토큰을 그대로 쓰지 마세요. 1시간 후 만료됩니다. 아래 URL 의 `<APP_ID>`, `<APP_SECRET>`, `<SHORT_TOKEN>` 채워서 브라우저에 붙여넣기:

```
https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=<APP_ID>&client_secret=<APP_SECRET>&fb_exchange_token=<SHORT_TOKEN>
```

- `APP_ID`, `APP_SECRET` 은 개발자 앱 설정의 Basic 페이지에 있음
- 응답 JSON 의 `access_token` 값이 **60일 long-lived user token** — 이것이 `IG_ACCESS_TOKEN` 입니다.

---

## 5단계 — IG_USER_ID 찾기

long-lived 토큰을 받은 직후, 다음 두 호출로 ID 를 확인합니다.

### 5-1. 페이지 ID 찾기

```
https://graph.facebook.com/v21.0/me/accounts?access_token=<LONG_TOKEN>
```

응답의 `data[].id` 가 페이지 ID 입니다 (Facebook 페이지가 여러 개면 인스타와 연결된 페이지 선택).

### 5-2. Instagram Business Account ID 찾기

```
https://graph.facebook.com/v21.0/<PAGE_ID>?fields=instagram_business_account&access_token=<LONG_TOKEN>
```

응답:
```json
{
  "instagram_business_account": { "id": "17841400000000000" },
  "id": "<PAGE_ID>"
}
```

`instagram_business_account.id` (17자리 숫자) 가 **`IG_USER_ID`** 입니다.

---

## 6단계 — imgbb API 키

1. https://api.imgbb.com/ → "Get API key" 클릭 → 무료 가입
2. 발급된 키를 `IMGBB_API_KEY` 에 입력

용량: 32MB/이미지 (우리는 ~200KB 라 여유). 무료 영구 호스팅.

---

## 7단계 — `.env` 채우기 + 검증

```bash
# .env
IMGBB_API_KEY=...
IG_ACCESS_TOKEN=<long_token_from_step_4>
IG_USER_ID=<ig_business_account_id_from_step_5>
```

검증:

```bash
npm run refresh-token
```

성공하면 새 60일 토큰을 출력합니다. 그 값을 다시 `.env` 에 복사 (선택 — 갱신 의미). 인증 실패 시 토큰/권한 문제.

이제 업로드 가능:

```bash
# 먼저 dry-run (imgbb까지만 검증, IG 발행 안 함)
node src/upload-instagram.js <topic_id> --dry-run

# 실제 발행
npm run upload <topic_id>
```

---

## 토큰 재발급 (60일 만료 시)

`refresh-token` 호출이 실패하면 (401 / `code=190`) 토큰이 revoke 됐거나 60일 지났습니다. 3단계로 돌아가 short-lived 토큰부터 재생성 → 4단계 long-lived 교환 → `.env` 갱신.

매월 1회 `npm run refresh-token` 실행 권장 — 그러면 60일 카운터가 리셋되어 사실상 무기한 유지.

---

## 한도 / 주의사항

- **24시간당 50개 게시물**: 신규 계정은 25개부터. 점진적으로 늘리세요 (Week 1: 3개/일 → Week 5+: 30개/일).
- **시간당 200 API 호출**: 1개 캐러셀 = ~10 호출 (컨테이너 4개 + status 폴링 + 발행) → 시간당 ~20개 캐러셀 안전.
- **JPEG만 지원**: PNG/WEBP/GIF 거부됨 (우리는 JPEG 출력이라 OK).
- **이미지 fetch 실패**: 컨테이너 status가 `ERROR`로 끝나면 imgbb URL 이 IG 에서 안 열린다는 뜻. 다른 호스트로 교체 시도.

---

## 트러블슈팅

| 증상 | 원인 / 해결 |
|------|------------|
| `401 invalid x-api-key` (Anthropic) | `.env` 의 `ANTHROPIC_API_KEY` 잘못 |
| `code=190 OAuthException` | IG 토큰 만료/revoke → 3~4단계 재진행 |
| `code=10 #200 permission` | 권한 부족 — Step 3 권한 5개 + **Step 2-5·6의 역할 등록(Admin/Developer + Instagram Tester) & Development 모드** 둘 다 확인 (가장 흔한 함정) |
| `Instagram User ID is invalid` | `IG_USER_ID` 가 페이지 ID 와 혼동된 경우. 17자리 숫자 ID 인지 확인 |
| imgbb `400` | API 키 오타 |
| imgbb `429` | rate limit (분당 호출 너무 많음) — 잠시 대기 후 재시도 |
| 컨테이너 `ERROR` 종료 | imgbb URL 일시 다운 또는 이미지 포맷 이슈. 재시도. |

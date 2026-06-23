# 셀러픽(SellerPic) 배포 & 운영 가이드

이 폴더(`site/`)는 **무료로 운영되는 상품 이미지 변환 서비스**입니다.
GitHub Pages(정적 호스팅) + 100% 브라우저 처리 구조라서 **서버·DB·API 비용이 전혀 들지 않습니다.**

---

## 💰 운영 비용: 0원

| 항목 | 방식 | 비용 |
|---|---|---|
| 호스팅 | GitHub Pages | 무료 |
| 이미지 변환 | 사용자 브라우저(클라이언트)에서 처리 | 무료(서버 없음) |
| 저장소/DB | 없음 (서버에 아무것도 저장 안 함) | 무료 |
| 트래픽 | GitHub Pages 기본 제공 | 무료 |
| 수익 | Google AdSense 광고 | **수익 발생(지출 X)** |

---

## 🚀 라이브로 만드는 법 (2단계)

### 1단계 — PR 병합 → 자동 배포
이 변경사항의 Pull Request를 **main 브랜치로 병합(Merge)** 하면,
`.github/workflows/deploy-pages.yml` 워크플로가 자동 실행되어 Pages가 켜지고 사이트가 게시됩니다.

- 배포 주소: **https://kotkim8210.github.io/**
- 진행 상황: 저장소 **Actions** 탭에서 확인
- (자동 활성화가 막혀 있다면) **Settings → Pages → Source = “GitHub Actions”** 로 한 번만 설정 후 Actions에서 `Deploy site to GitHub Pages` 재실행

### 2단계 — 검색 노출(선택, 권장)
1. [Google Search Console](https://search.google.com/search-console) 에 `https://kotkim8210.github.io/` 등록
2. 사이트맵 제출: `https://kotkim8210.github.io/sitemap.xml`
3. (선택) [네이버 서치어드바이저](https://searchadvisor.naver.com/) 에도 등록하면 국내 검색 노출에 유리

---

## 💵 Google AdSense 켜기 (수익화)

> AdSense는 **본인 계정 + 구글 승인**이 필요해 코드만으로 자동 적용되지 않습니다.
> 현재는 안전하게 **광고 요청이 전혀 발생하지 않도록 비활성** 상태입니다.

1. [Google AdSense](https://adsense.google.com/) 가입 → 사이트 `kotkim8210.github.io` 추가
2. 발급받은 **게시자 ID**(`ca-pub-` + 숫자 16자리)를 두 곳에 입력:
   - **`site/index.html`** 상단:
     ```js
     window.ADSENSE_CLIENT = "ca-pub-1234567890123456"; // ← 본인 ID로 교체
     ```
   - **`site/ads.txt`**:
     ```
     google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0
     ```
     (`ca-`를 뺀 `pub-...` 형식 주의)
3. AdSense 대시보드에서 **자동 광고(Auto ads)** 를 `kotkim8210.github.io` 에 켜면, 페이지에 광고가 자동 배치됩니다.
4. 다시 PR 병합/푸시하면 반영됩니다.

> ✅ 게시자 ID가 placeholder(`ca-pub-XXXX...`)인 동안에는 광고 스크립트가 로드되지 않아
> 정책 위반(잘못된 광고 요청) 위험이 없습니다. 승인 후 ID만 바꾸면 즉시 동작합니다.

### 광고 위치 메모
- **자동 광고**만 켜도 본문에 자동 배치됩니다(가장 간단).
- 특정 위치를 직접 지정하려면 `index.html`의 `<div class="ad-slot" data-ad-slot="0000000000">` 의
  `0000000000` 을 AdSense에서 만든 **광고 단위 슬롯 ID**로 바꾸세요.

---

## 🔧 마케팅·SEO 체크리스트 (이미 적용됨)
- [x] 검색 친화 `<title>` / `description` / 키워드 (쿠팡 대표이미지·1000x1000·png jpg 변환 등)
- [x] Open Graph / Twitter 카드 + 공유 이미지(`og-image.png`) → 카카오톡·페북 미리보기
- [x] 구조화 데이터(JSON-LD): WebApplication + FAQPage(리치 결과 노출 유리)
- [x] `robots.txt` · `sitemap.xml`
- [x] FAQ·사용법·규격표 등 롱테일 검색을 잡는 본문 콘텐츠(AdSense 승인에도 유리)
- [x] 개인정보처리방침(`privacy.html`) — AdSense 필수 요건

## ✍️ 배포 전 바꾸면 좋은 것
- `privacy.html` 의 문의 이메일(`your-email@example.com`)
- 자체 도메인을 쓰려면 `site/CNAME` 파일 추가 후 각 파일의 `kotkim8210.github.io` 주소 교체

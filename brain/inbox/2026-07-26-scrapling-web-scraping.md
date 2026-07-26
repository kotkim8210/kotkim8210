# [학습] Scrapling — 적응형·반봇 우회 웹스크래핑 → 쿠팡·네이버쇼핑 크롤러

- 일시: 2026-07-26
- 출처 영상: 오늘코드(todaycode), "7만 GitHub star를 받은 Scrapling, Cloudflare 차단 어디까지 우회할 수 있을까? 적응형 웹스크래핑"
  - https://youtube.com/watch?v=hdEweGeZpuE
- 목적: 이 라이브러리를 학습해 **쿠팡·네이버쇼핑 크롤링**을 가능하게 함
- 산출물: `projects/coupang-naver-crawler/` (동작 코드 + 오프라인 테스트 28/28 통과)

---

## Scrapling이란
- GitHub 7만+ star. 파이썬 **적응형(adaptive) 웹스크래핑 프레임워크**. (제작: Karim Shoair, BSD-3)
- 두 축이 핵심:
  1. **반봇(anti-bot) 우회**: Cloudflare Turnstile을 기본으로 우회하는 스텔스 브라우저.
  2. **적응형 선택자**: 사이트 레이아웃이 바뀌면 저장해둔 지문으로 요소를 **자동 재배치**. (AutoScraper보다 ~5배 빠름, 파서 속도는 Parsel급)

## 세 가지 페처(Fetcher)
| 클래스 | 용도 | 특징 |
|---|---|---|
| `Fetcher` | 일반 HTTP | TLS 지문 위장, `impersonate='chrome'`, HTTP/3 |
| `StealthyFetcher` | **반봇 우회** | `solve_cloudflare=True`로 Turnstile 자동해결. 사람 행동 모방 |
| `DynamicFetcher` | 동적 콘텐츠 | Playwright Chromium 브라우저 자동화 |
- 세션 버전: `FetcherSession` / `StealthySession` / `DynamicSession` (브라우저 재사용)
- Spider 프레임워크(스크래피 유사): 동시성·일시정지/재개·프록시 로테이션

## 설치
```
pip install "scrapling[fetchers]"
scrapling install          # 스텔스 브라우저(camoufox/chromium) 내려받기
```
- 파서만: `pip install scrapling` (fetchers는 curl_cffi/playwright 필요)
- 설치 버전 확인: 0.4.11. 파서 클래스는 `Selector`. css는 `css(sel, adaptive=, auto_save=, percentage=40)`.

## 핵심 API
```python
from scrapling.fetchers import StealthyFetcher
page = StealthyFetcher.fetch(url, headless=True, solve_cloudflare=True,
                             network_idle=True, google_search=True, proxy=...)
page.css('.name::text').get()          # 첫 값
page.css('.name::text').getall()       # 전체
page.css('a::attr(href)').get()        # 속성
el.attrib['data-product-id']           # 요소 속성
page.css('.price::text').re_first(r'[\d,]+')
StealthyFetcher.adaptive = True
page.css('.product', auto_save=True)   # 최초: 지문 저장
page.css('.product', adaptive=True)    # 레이아웃 변경 시: 재배치
```

## 쿠팡·네이버쇼핑 적용 포인트 (실전 노하우)
- **쿠팡**: 강한 반봇 방어 → `StealthyFetcher(solve_cloudflare=True)` 필수. 데이터센터 IP 차단 심함 → 주거용 프록시 권장.
  - 검색 URL: `https://www.coupang.com/np/search?q=키워드&page=N&listSize=72`
  - 상품 li: `ul#productList li.search-product` (각 li에 `data-product-id`). 이름 `.name`, 가격 `strong.price-value`, 링크 `a.search-product-link`, 로켓배지 `.badge.rocket`.
- **네이버쇼핑**: 반봇 + **해시 클래스명이 자주 바뀜**(`product_item__abcDE`) → CSS 취약.
  - **1순위: `script#__NEXT_DATA__` JSON 파싱**. 구조도 바뀌므로 고정 경로 대신 **재귀 탐색**으로 "제목+가격+몰/이미지"를 가진 dict를 찾음. 실패 시 CSS 폴백.
  - 검색 URL: `https://search.shopping.naver.com/search/all?query=키워드&pagingIndex=N&pagingSize=40`
- 공통 매너: 요청 간 지연, robots/약관/법 준수, 대량은 공식 API 우선 검토.

## 설계 교훈
- **선택자를 코드에서 분리**(`config/selectors.json`)하면 사이트 변경에 강해진다. + adaptive가 1차 방어.
- **JSON-우선(embedded state) 전략**이 해시 클래스명 CSS보다 훨씬 견고하다(네이버 사례).
- 페처 의존성은 실행 시점에만 import → 파서 전용 환경에서도 로드/테스트 가능.

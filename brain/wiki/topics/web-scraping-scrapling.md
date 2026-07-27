---
title: Scrapling 웹스크래핑 & 쿠팡·네이버쇼핑 크롤러
slug: web-scraping-scrapling
tags: [크롤링, 스크래핑, scrapling, 쿠팡, 네이버쇼핑, 반봇, 파이썬]
created: 2026-07-26
updated: 2026-07-26
sources: [2026-07-26-scrapling-web-scraping.md]
related: [[my-projects]], [[video-skills]]
confidence: high
status: active
---

## 한 줄 요약
GitHub 7만★ 적응형 스크래핑 프레임워크 **Scrapling**(반봇 우회 + 레이아웃 변경 자동 재배치)을 학습해 만든 **쿠팡·네이버쇼핑 상품 크롤러** — 코드는 `projects/coupang-naver-crawler/`, 오프라인 파서 테스트 28/28 통과.

## 핵심 내용

### Scrapling 두 축 (2026-07-26-scrapling-web-scraping.md)
- **반봇 우회**: `StealthyFetcher(solve_cloudflare=True)`가 Cloudflare Turnstile을 자동 해결하고 사람 행동을 모방.
- **적응형 선택자**: `auto_save=True`로 선택자 지문을 저장 → 사이트가 바뀌면 `adaptive=True`로 요소를 자동 재배치.
- 세 페처: `Fetcher`(HTTP·TLS위장) / `StealthyFetcher`(반봇) / `DynamicFetcher`(Playwright). 설치 버전 0.4.11, 파서 클래스 `Selector`.
- 설치: `pip install "scrapling[fetchers]"` + `scrapling install`(스텔스 브라우저). 파서만 쓰면 `pip install scrapling`.

### 쿠팡 (강한 반봇 → 스텔스+프록시)
- 검색 `…/np/search?q=키워드&page=N&listSize=72`, 상품 `ul#productList li.search-product`(`data-product-id`).
- 데이터센터 IP 차단 심함 → 주거용 프록시 권장. 이름/가격/링크/로켓배지 선택자로 파싱.

### 네이버쇼핑 (반봇 + 해시 클래스명 변동 → JSON 우선)
- **1순위 전략: `script#__NEXT_DATA__` JSON을 재귀 탐색**해 "제목+가격+몰/이미지"를 가진 dict를 상품으로 인식 → 해시 클래스명(`product_item__abcDE`) CSS보다 훨씬 견고. 실패 시 CSS 폴백.

### 설계 교훈 (재사용 가능한 원칙)
- 선택자를 코드에서 분리(`config/selectors.json`) + adaptive → 사이트 변경 내성.
- **embedded-state(JSON) 우선** 전략이 동적 CSS보다 견고.
- 페처 의존성은 실행 시점 import → 파서 전용 환경에서도 테스트 가능.

### 실측 검증 결과 (2026-07-26 리뷰테스트)
- **쿠팡 403(Access Denied·Akamai), 네이버 418** — 평범한 HTTP 클라이언트는 실제로 차단됨을 확인. 스텔스 엔진이 필요한 이유가 실증됨.
- **Scrapling 0.4.11 실측 함정 3가지**
  1. `get_all_text()`는 `<script>` 내용을 **빈 문자열**로 반환 → 인라인 JSON을 정규식으로 찾을 땐 `html_content`(또는 `body`)를 써야 한다. (이걸 몰라 네이버 폴백이 죽은 코드였음 → 수정)
  2. `block_images` 인자는 **존재하지 않으며 조용히 무시**된다. 리소스 차단은 `disable_resources`가 담당.
  3. `auto_save`/`adaptive` 인자는 **Selector 생성 시 adaptive가 켜져 있어야** 동작하고, 아니면 무시하며 선택자마다 WARNING을 찍는다. `_Selector__adaptive_enabled`로 사전 감지 가능.
- **재시도 중첩 주의**: Scrapling 페처가 내부적으로 3회 재시도하므로, 바깥에서 또 3회 감싸면 3×3=9회로 차단 사이트에서 극단적으로 느려진다.
- **환경 제약**: 개발 샌드박스의 이그레스 프록시가 헤드리스 브라우저·TLS 지문 위장 트래픽을 리셋 → 스텔스 라이브 크롤링은 일반 PC에서 검증해야 한다.

## 연결고리 (Connections)
- [[my-projects]] — 기존 '홍보처 이메일 크롤러'·'쿠팡파트너스 MVP'와 같은 수집·커머스 계열. 이 크롤러가 상품 데이터 수집 축을 보강.
- [[video-skills]] — 둘 다 **유튜브 영상을 학습해 산출물로 전환**한 사례(watch/osmu ↔ Scrapling). "영상→실행코드" 파이프라인.

## 미해결/모순 (Open Questions)
- [확인필요] 쿠팡/네이버 **실제 라이브 선택자 검증은 아직 미완**. 샌드박스 프록시가 스텔스 브라우저를 차단해 라이브 수집을 못 했다(위 '실측 검증 결과' 참고). 일반 PC(주거용 IP)에서 1회 실행해 선택자를 확정할 것.
- [ ] 대량 수집 시 공식 API(쿠팡 파트너스/오픈API, 네이버 쇼핑검색 API)로 전환할지 검토.
- [ ] Spider(동시성·재개) 기반 대규모 크롤링 버전으로 확장할지.

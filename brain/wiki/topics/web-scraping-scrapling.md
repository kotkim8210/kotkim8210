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

## 연결고리 (Connections)
- [[my-projects]] — 기존 '홍보처 이메일 크롤러'·'쿠팡파트너스 MVP'와 같은 수집·커머스 계열. 이 크롤러가 상품 데이터 수집 축을 보강.
- [[video-skills]] — 둘 다 **유튜브 영상을 학습해 산출물로 전환**한 사례(watch/osmu ↔ Scrapling). "영상→실행코드" 파이프라인.

## 미해결/모순 (Open Questions)
- [확인필요] 쿠팡/네이버 실제 라이브 선택자는 시점에 따라 변할 수 있음(코드의 기본값은 통상 구조 기준, adaptive+config로 대응). 실 계정/프록시 환경에서 1회 검증 필요.
- [ ] 대량 수집 시 공식 API(쿠팡 파트너스/오픈API, 네이버 쇼핑검색 API)로 전환할지 검토.
- [ ] Spider(동시성·재개) 기반 대규모 크롤링 버전으로 확장할지.

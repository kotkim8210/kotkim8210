# 쿠팡 · 네이버쇼핑 크롤러 (Scrapling 기반)

[**Scrapling**](https://github.com/D4Vinci/Scrapling)을 학습해 만든 **쿠팡·네이버쇼핑 상품 크롤러**입니다.
Scrapling은 GitHub 7만+ star의 적응형(adaptive) 웹스크래핑 프레임워크로, **Cloudflare/Turnstile 등 반봇 방어를 우회**하고, **사이트 레이아웃이 바뀌어도 요소를 자동 재배치**하는 게 핵심입니다.

> 학습 출처: 오늘코드(todaycode) — *"7만 GitHub star를 받은 Scrapling, Cloudflare 차단 어디까지 우회할 수 있을까? 적응형 웹스크래핑"* ([영상](https://youtube.com/watch?v=hdEweGeZpuE))

---

## 왜 Scrapling인가

쿠팡과 네이버쇼핑은 크롤링이 특히 까다롭습니다.

| 사이트 | 난관 | 이 크롤러의 대응 |
|---|---|---|
| **쿠팡** | 강한 반봇 방어(Akamai/CF류), 데이터센터 IP 차단 | `StealthyFetcher(solve_cloudflare=True)` 로 사람처럼 위장, 프록시 지원 |
| **네이버쇼핑** | 강한 반봇 + **자주 바뀌는 해시 클래스명**(`product_item__abcDE`) | 1순위로 `__NEXT_DATA__` **JSON을 재귀 파싱**, 실패 시 CSS 폴백 |
| 공통 | 레이아웃 변경으로 선택자가 깨짐 | Scrapling **adaptive 선택자**로 요소 자동 재배치 |

---

## 설치

```bash
cd projects/coupang-naver-crawler

# 1) 파서만 (오프라인 테스트용)
pip install scrapling

# 2) 실제 크롤링 (반봇 우회 포함) — fetchers extra + 스텔스 브라우저
pip install "scrapling[fetchers]>=0.4"
scrapling install
```

> `scrapling install` 은 스텔스 브라우저(camoufox/chromium 등)를 내려받습니다. 최초 1회만 필요합니다.

---

## 사용법 (CLI)

```bash
# 쿠팡 검색 2페이지 → JSON 저장
python crawl.py coupang --query "무선 이어폰" --pages 2 --out out/coupang.json

# 네이버쇼핑 검색, 상위 20개만 CSV로
python crawl.py naver --query "무선 이어폰" --limit 20 --out out/naver.csv

# 쿠팡 상품 상세(ID 하나)
python crawl.py coupang --product-id 1234567890

# 차단이 심하면: 브라우저 창을 띄우고(headed) 주거용 프록시 사용
python crawl.py coupang -q "커피" --no-headless --proxy http://user:pass@host:port
```

### 주요 옵션
| 옵션 | 설명 |
|---|---|
| `-q, --query` | 검색어 |
| `-p, --pages` | 가져올 페이지 수 (기본 1) |
| `--limit N` | 최대 상품 수 |
| `-o, --out` | 저장 경로(`.json`/`.csv`). 생략 시 표준출력 |
| `--engine` | `stealthy`(기본·반봇우회) / `dynamic`(Playwright) / `http`(빠름·비보호 페이지) |
| `--no-headless` | 브라우저 창 띄우기(디버깅·수동 캡차 대응) |
| `--no-solve` | Cloudflare 자동해결 끄기 |
| `--no-adaptive` | 적응형 선택자 끄기 |
| `--proxy URL` | 프록시 지정 |
| `--fast` | 이미지·불필요 리소스 차단(속도↑) |
| `-v` | 디버그 로그 |

---

## 라이브러리로 사용

```python
from crawler import coupang, naver_shopping
from crawler.common import FetchOptions, save

# 쿠팡
rows = coupang.search("게이밍 마우스", pages=2, limit=50)
save(rows, "out/coupang.json")

# 네이버쇼핑 (스텔스 필수)
rows = naver_shopping.search("게이밍 마우스", pages=2)
save(rows, "out/naver.csv")

# 옵션 커스터마이즈
opts = FetchOptions(engine="stealthy", headless=False, proxy="http://...", block_images=True)
rows = coupang.search("커피", opts=opts)
```

### 출력 스키마
- **쿠팡 검색**: `product_id, name, price, base_price, per_unit, rating, rating_count, is_rocket, is_ad, is_sold_out, image, url`
- **네이버쇼핑**: `product_id, name, price, mall, brand, category, review_count, rating, image, url`

---

## 사이트가 바뀌어 선택자가 안 맞을 때

1. **적응형이 1차 방어**: `adaptive=True`(기본)면 Scrapling이 저장해둔 지문으로 요소를 재배치합니다.
2. **그래도 안 되면** `config/selectors.json` 만 고치세요(코드 수정 불필요). 적은 키만 기본값을 덮어씁니다:

```json
{
  "coupang": { "name": "div.new-name-class::text", "price": "strong.new-price::text" },
  "naver":   { "list_item": "div[class*='newItem']" }
}
```

네이버는 대부분 `__NEXT_DATA__` JSON에서 뽑으므로 CSS 수정이 거의 필요 없습니다. JSON 구조가 바뀌어도 **재귀 탐색**이 "제목+가격+몰/이미지"를 가진 dict를 자동으로 찾습니다.

---

## 테스트 (오프라인)

네트워크·브라우저 없이 파싱 로직만 검증합니다(픽스처 기반):

```bash
pip install scrapling      # 파서만 있으면 됨
python tests/test_parsers.py
# → 28/28 통과 ✅
```

---

## 구조

```
coupang-naver-crawler/
├── crawl.py                 # 통합 CLI
├── requirements.txt
├── config/selectors.json    # 선택자 오버라이드(코드 수정 없이 튜닝)
├── crawler/
│   ├── common.py            # Scrapling 페처 래퍼·적응형 선택자·재시도·저장
│   ├── coupang.py           # 쿠팡 검색/상세
│   └── naver_shopping.py    # 네이버쇼핑(JSON 우선 + CSS 폴백)
└── tests/test_parsers.py    # 오프라인 파서 테스트
```

---

## 주의 · 매너

- **교육/연구 목적**입니다. 각 사이트의 `robots.txt`·이용약관과 국내 법(정보통신망법 등)을 준수하세요.
- 요청 사이에 지연을 둡니다(`polite_sleep`). `--no-delay`는 소량 테스트에만.
- 대량·상업적 수집은 **공식 API**(쿠팡 파트너스/오픈API, 네이버 쇼핑검색 API 등)를 우선 검토하세요.
- 개인정보·저작권 데이터는 수집·저장하지 마세요.

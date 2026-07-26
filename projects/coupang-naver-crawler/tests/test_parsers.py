#!/usr/bin/env python3
"""오프라인 파서 테스트 — 네트워크·브라우저 없이 파싱 로직만 검증한다.

Scrapling 파서(Selector)만 있으면 실행된다(fetchers extra 불필요):
    pip install scrapling
    python tests/test_parsers.py     # 또는  pytest tests/

실제 사이트 접속(쿠팡/네이버)은 여기서 하지 않는다. 순수 파싱 함수가
저장된 HTML/JSON 픽스처에서 올바른 결과를 내는지만 확인한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapling import Selector  # noqa: E402

from crawler import coupang, naver_shopping  # noqa: E402
from crawler.common import to_int  # noqa: E402

# --------------------------------------------------------------------------- #
# 픽스처
# --------------------------------------------------------------------------- #
COUPANG_HTML = """
<ul id="productList">
  <li class="search-product" data-product-id="111">
    <a class="search-product-link" href="/vp/products/111?itemId=1">
      <img class="search-product-wrap-img" src="//img.coupang.com/a.jpg" data-img-src="//img.coupang.com/a2.jpg">
      <div class="name">애플 에어팟 프로 2세대</div>
      <strong class="price-value">299,000</strong>
      <del class="base-price">359,000</del>
      <span class="unit-price">(100g당 1,000원)</span>
      <em class="rating">4.5</em>
      <span class="rating-total-count">(12,345)</span>
      <span class="badge rocket">로켓배송</span>
    </a>
  </li>
  <li class="search-product" data-product-id="222">
    <a class="search-product-link" href="/vp/products/222">
      <div class="name">가성비 무선 이어폰</div>
      <strong class="price-value">15,900</strong>
      <span class="ad-badge">광고</span>
    </a>
  </li>
</ul>
"""

COUPANG_DETAIL_HTML = """
<html><body>
  <h1 class="prod-buy-header__title">애플 에어팟 프로 2세대 USB-C</h1>
  <div class="prod-price"><span class="total-price"><strong>299,000원</strong></span></div>
  <span class="prod-sale-vendor-name">쿠팡</span>
  <span class="prod-txt-delivery-date">내일(수) 도착 보장</span>
</body></html>
"""

# 네이버는 __NEXT_DATA__ JSON을 파싱한다. 구조를 일부러 깊게/변형해서 재귀 탐색을 검증.
NAVER_HTML = """
<html><body>
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"initialState":{"products":{"list":[
  {"item":{"id":"nv9001","productName":"삼성 갤럭시 버즈3 프로","lowPrice":"219000",
           "mallName":"삼성전자","brand":"삼성","imageUrl":"https://img/n1.jpg",
           "mallProductUrl":"https://smartstore.naver.com/p/9001","reviewCount":"3210",
           "category1Name":"디지털/가전","category2Name":"음향기기","averageReviewScore":4.8}},
  {"item":{"id":"nv9002","productTitle":"소니 WF-1000XM5","price":289000,
           "mallName":"소니코리아","imageUrl":"https://img/n2.jpg",
           "crUrl":"https://cr.shopping.naver.com/9002","reviewCnt":1200}}
]}}}}}
</script>
</body></html>
"""


# --------------------------------------------------------------------------- #
# 헬퍼
# --------------------------------------------------------------------------- #
_checks = 0
_fails = 0


def check(cond: bool, msg: str) -> None:
    global _checks, _fails
    _checks += 1
    if cond:
        print(f"  ✅ {msg}")
    else:
        _fails += 1
        print(f"  ❌ {msg}")


# --------------------------------------------------------------------------- #
# 테스트
# --------------------------------------------------------------------------- #
def test_to_int() -> None:
    print("[to_int]")
    check(to_int("299,000원") == 299000, "'299,000원' → 299000")
    check(to_int(15900) == 15900, "정수 그대로")
    check(to_int(None) is None, "None → None")
    check(to_int("품절") is None, "숫자 없음 → None")


def test_coupang_search() -> None:
    print("[쿠팡 검색 파싱]")
    page = Selector(COUPANG_HTML)
    items = page.css(coupang.DEFAULT_SELECTORS["list_item"])
    check(len(items) == 2, f"상품 2개 인식 (실제 {len(items)})")

    a = coupang.parse_search_item(items[0], coupang.DEFAULT_SELECTORS)
    check(a["product_id"] == "111", "product_id=111")
    check(a["name"] == "애플 에어팟 프로 2세대", "상품명 추출")
    check(a["price"] == 299000, "가격 299000")
    check(a["base_price"] == 359000, "정가 359000")
    check(a["rating_count"] == 12345, "리뷰수 12345")
    check(a["is_rocket"] is True, "로켓배송 배지 인식")
    check(a["url"] == "https://www.coupang.com/vp/products/111?itemId=1", "절대 URL 생성")
    check(a["image"] == "https://img.coupang.com/a.jpg", "이미지 src(//→https)")

    b = coupang.parse_search_item(items[1], coupang.DEFAULT_SELECTORS)
    check(b["is_ad"] is True, "광고 배지 인식")
    check(b["is_rocket"] in (False, None), "로켓 없음")


def test_coupang_detail() -> None:
    print("[쿠팡 상세 파싱]")
    page = Selector(COUPANG_DETAIL_HTML)
    d = coupang.parse_detail(page, 111, coupang.DETAIL_SELECTORS)
    check(d["title"].startswith("애플 에어팟 프로 2세대"), "상세 제목")
    check(d["price"] == 299000, "상세 가격 299000")
    check(d["seller"] == "쿠팡", "판매자 추출")


def test_naver_json() -> None:
    print("[네이버 __NEXT_DATA__ 파싱]")
    page = Selector(NAVER_HTML)
    rows = naver_shopping.extract_from_json(page)
    check(len(rows) == 2, f"상품 2개 추출 (실제 {len(rows)})")

    by_id = {r["product_id"]: r for r in rows}
    a = by_id.get("nv9001", {})
    check(a.get("name") == "삼성 갤럭시 버즈3 프로", "productName 키 처리")
    check(a.get("price") == 219000, "lowPrice(문자열) → 219000")
    check(a.get("mall") == "삼성전자", "몰명 추출")
    check(a.get("category") == "디지털/가전 > 음향기기", "카테고리 결합")
    check(a.get("review_count") == 3210, "리뷰수 3210")
    check(a.get("rating") == 4.8, "평점 4.8")

    b = by_id.get("nv9002", {})
    check(b.get("name") == "소니 WF-1000XM5", "productTitle 키 처리(대체 키)")
    check(b.get("price") == 289000, "price(정수) 처리")
    check(b.get("url") == "https://cr.shopping.naver.com/9002", "crUrl 대체 URL")


def main() -> int:
    for t in (test_to_int, test_coupang_search, test_coupang_detail, test_naver_json):
        t()
    print(f"\n결과: {_checks - _fails}/{_checks} 통과", "✅" if _fails == 0 else f"❌ {_fails} 실패")
    return 1 if _fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

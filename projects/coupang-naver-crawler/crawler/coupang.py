"""쿠팡(Coupang) 크롤러 — 검색 결과 · 상품 상세.

쿠팡은 강력한 반봇(bot) 방어(Akamai/Cloudflare류)를 쓴다. 그래서 기본 엔진은
StealthyFetcher(`solve_cloudflare=True`) 다. 데이터센터 IP는 차단되기 쉬우므로
실사용 시 주거용(residential) 프록시를 권장한다(README 참고).

파싱 함수(`parse_search_item`, `parse_detail`)는 네트워크 없이도 테스트할 수 있게
Selector 요소만 받는다 → tests/test_parsers.py 에서 오프라인 검증.
"""
from __future__ import annotations

import logging
from urllib.parse import quote, urljoin

from . import common
from .common import FetchOptions, first, present, to_int

log = logging.getLogger("crawler.coupang")

BASE = "https://www.coupang.com"
SEARCH_URL = BASE + "/np/search?q={q}&page={page}&listSize={size}&sorter=scoreDesc"
PRODUCT_URL = BASE + "/vp/products/{id}"
LIST_SIZE = 72

# 기본 선택자 — 사이트가 바뀌면 config/selectors.json 의 "coupang" 키로 덮어쓸 수 있다.
DEFAULT_SELECTORS = {
    "list_item": "ul#productList li.search-product",
    "id_attr": "data-product-id",
    "name": "div.name::text",
    "price": "strong.price-value::text",
    "base_price": "del.base-price::text",
    "per_unit": "span.unit-price::text",
    "rating": "em.rating::text",
    "rating_count": "span.rating-total-count::text",
    "link": "a.search-product-link::attr(href)",
    "image": "img.search-product-wrap-img::attr(src)",
    "image_lazy": "img.search-product-wrap-img::attr(data-img-src)",
    "rocket": "span.badge.rocket, img[alt*='로켓']",
    "ad": "span.ad-badge, span.ad-badge-text",
    "sold_out": "div.out-of-stock, span.out-of-stock",
}

DETAIL_SELECTORS = {
    "title": "h1.prod-buy-header__title::text, h2.prod-buy-header__title::text",
    "price": "span.total-price > strong::text, div.prod-price .total-price strong::text",
    "base_price": "span.origin-price::text",
    "seller": "span.prod-sale-vendor-name::text, a.prod-sale-vendor-name::text",
    "rating": "span.rating-star-num::attr(style)",
    "rating_count": "span.count::text",
    "delivery": "span.prod-txt-delivery-date::text",
}


def _image(li, sels) -> str | None:
    """이미지 src(지연로딩 대비 data-img-src도 확인) → 절대 URL로 정규화."""
    for key in ("image", "image_lazy"):
        sel = sels.get(key)
        if not sel:
            continue
        v = li.css(sel).get()
        if v:
            return "https:" + v if v.startswith("//") else v
    return None


def parse_search_item(li, sels: dict) -> dict:
    """검색 결과의 <li> 하나를 dict로 변환(오프라인 테스트 가능)."""
    href = li.css(sels["link"]).get()
    return {
        "product_id": li.attrib.get(sels["id_attr"]),
        "name": first(li, sels["name"]),
        "price": to_int(first(li, sels["price"])),
        "price_text": first(li, sels["price"]),
        "base_price": to_int(first(li, sels.get("base_price", ""))),
        "per_unit": first(li, sels.get("per_unit", "")),
        "rating": first(li, sels.get("rating", "")),
        "rating_count": to_int(first(li, sels.get("rating_count", ""))),
        "is_rocket": present(li, sels.get("rocket")),
        "is_ad": present(li, sels.get("ad")),
        "is_sold_out": present(li, sels.get("sold_out")),
        "image": _image(li, sels),
        "url": urljoin(BASE, href) if href else None,
    }


def parse_detail(page, product_id, sels: dict) -> dict:
    """상품 상세 페이지 → dict(오프라인 테스트 가능)."""
    return {
        "product_id": str(product_id),
        "title": first(page, sels["title"]),
        "price": to_int(first(page, sels["price"])),
        "base_price": to_int(first(page, sels.get("base_price", ""))),
        "seller": first(page, sels.get("seller", "")),
        "delivery": first(page, sels.get("delivery", "")),
        "url": PRODUCT_URL.format(id=product_id),
    }


def search(
    query: str,
    pages: int = 1,
    opts: FetchOptions | None = None,
    limit: int | None = None,
    delay: bool = True,
) -> list[dict]:
    """키워드로 쿠팡을 검색해 상품 목록을 반환한다."""
    opts = opts or FetchOptions(engine="stealthy")
    sels = common.load_selectors("coupang", DEFAULT_SELECTORS)
    results: list[dict] = []

    for page_no in range(1, pages + 1):
        url = SEARCH_URL.format(q=quote(query), page=page_no, size=LIST_SIZE)
        log.info("[쿠팡] 검색 p%d: %s", page_no, url)
        page = common.with_retry(lambda u=url: common.fetch(u, opts), what=f"coupang p{page_no}")

        items = common._sel(page, sels["list_item"], opts.adaptive)
        log.info("[쿠팡] p%d 상품 %d개 파싱", page_no, len(items))
        for li in items:
            row = parse_search_item(li, sels)
            if row.get("name"):  # 광고/빈 슬롯 방어
                results.append(row)
            if limit and len(results) >= limit:
                return results
        if delay and page_no < pages:
            common.polite_sleep()

    return results


def product(
    product_id: str | int,
    opts: FetchOptions | None = None,
) -> dict:
    """상품 ID로 상세 정보를 가져온다."""
    opts = opts or FetchOptions(engine="stealthy")
    sels = common.load_selectors("coupang_detail", DETAIL_SELECTORS)
    url = PRODUCT_URL.format(id=product_id)
    log.info("[쿠팡] 상세: %s", url)
    page = common.with_retry(lambda: common.fetch(url, opts), what="coupang detail")
    return parse_detail(page, product_id, sels)

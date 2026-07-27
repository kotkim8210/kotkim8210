"""네이버쇼핑(search.shopping.naver.com) 크롤러.

네이버쇼핑은 (1) 강한 반봇 방어와 (2) 자주 바뀌는 해시 클래스명(예:
`product_item__abcDE`) 때문에 CSS만으로는 취약하다. 그래서 **1순위 전략은
페이지에 심긴 `__NEXT_DATA__`(또는 프리로드 상태) JSON을 파싱**하는 것이다.

JSON 구조도 종종 바뀌므로, 고정 경로 대신 **재귀 탐색**으로 "상품처럼 생긴"
dict(제목+가격+몰/이미지 보유)를 찾아낸다. 이게 실패하면 CSS 폴백을 쓴다.

파싱 함수는 네트워크 없이 테스트할 수 있게 순수 함수로 분리했다.
"""
from __future__ import annotations

import json
import logging
import re
from urllib.parse import quote

from . import common
from .common import FetchOptions, to_int

log = logging.getLogger("crawler.naver")

SEARCH_URL = (
    "https://search.shopping.naver.com/search/all"
    "?query={q}&pagingIndex={page}&pagingSize={size}&productSet=total&sort=rel"
)
PAGE_SIZE = 40

# 상품 dict를 식별하기 위한 키 후보들 (네이버가 이름을 바꿔도 폭넓게 대응)
TITLE_KEYS = ("productTitle", "productName", "title", "prodName")
PRICE_KEYS = ("price", "lowPrice", "mobileLowPrice", "salePrice", "dispSalePrice")
MALLURL_KEYS = ("mallProductUrl", "crUrl", "productUrl", "adcrUrl", "mallPcUrl")
IMAGE_KEYS = ("imageUrl", "imgUrl", "productImageUrl", "imageUrl300")
ID_KEYS = ("id", "nvMid", "mallProductId", "productId", "prodNo")
MALL_KEYS = ("mallName", "mallNm", "mallInfoName")
BRAND_KEYS = ("brand", "maker", "brandName")
REVIEW_KEYS = ("reviewCount", "reviewCnt", "totalReviewCount")
RATING_KEYS = ("averageReviewScore", "reviewScore", "scoreInfo")

# CSS 폴백 — 해시 클래스명은 접두/부분일치로 잡는다(취약하므로 최후의 수단).
DEFAULT_SELECTORS = {
    "list_item": "div[class*='product_item'], li[class*='product_item']",
    "name": "a[class*='title'] span::text, a[class*='title']::text",
    "price": "span[class*='price'] span[class*='num']::text, span[class*='price']::text",
    "link": "a[class*='title']::attr(href)",
    "image": "img::attr(src)",
    "mall": "a[class*='mall']::text",
}


def _pick(node: dict, keys) -> object | None:
    for k in keys:
        v = node.get(k)
        if v not in (None, "", 0, "0"):
            return v
    return None


def _looks_like_product(node: dict) -> bool:
    """제목 + 가격 + (몰 URL | 이미지 | 몰명) 을 모두 가진 dict를 상품으로 본다."""
    has_title = any(isinstance(node.get(k), str) and node.get(k) for k in TITLE_KEYS)
    has_price = _pick(node, PRICE_KEYS) is not None
    has_ctx = (
        _pick(node, MALLURL_KEYS) is not None
        or _pick(node, IMAGE_KEYS) is not None
        or _pick(node, MALL_KEYS) is not None
    )
    return has_title and has_price and has_ctx


def normalize(node: dict) -> dict:
    """네이버 상품 dict → 표준 스키마."""
    cats = [node.get(f"category{i}Name") for i in range(1, 5)]
    rating = _pick(node, RATING_KEYS)
    if isinstance(rating, dict):  # scoreInfo 가 dict인 경우
        rating = rating.get("averageReviewScore") or rating.get("score")
    return {
        "product_id": _pick(node, ID_KEYS),
        "name": _pick(node, TITLE_KEYS),
        "price": to_int(_pick(node, PRICE_KEYS)),
        "mall": _pick(node, MALL_KEYS),
        "brand": _pick(node, BRAND_KEYS),
        "category": " > ".join([c for c in cats if c]) or None,
        "review_count": to_int(_pick(node, REVIEW_KEYS)),
        "rating": rating,
        "image": _pick(node, IMAGE_KEYS),
        "url": _pick(node, MALLURL_KEYS),
    }


def _walk(node, out: list[dict]) -> None:
    """JSON 트리를 재귀 순회하며 상품 dict를 수집한다."""
    if isinstance(node, dict):
        if _looks_like_product(node):
            out.append(normalize(node))
            return  # 매칭된 상품 내부로는 더 들어가지 않음(중복·잡음 방지)
        for v in node.values():
            _walk(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk(v, out)


def _dedup(rows: list[dict]) -> list[dict]:
    seen: set = set()
    uniq: list[dict] = []
    for r in rows:
        key = r.get("product_id") or r.get("url") or r.get("name")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        uniq.append(r)
    return uniq


_JSON_BLOB = re.compile(
    r"(?:__NEXT_DATA__|__PRELOADED_STATE__|__APOLLO_STATE__)\s*=\s*(\{.*?\})\s*[;<]",
    re.DOTALL,
)


def _raw_json(page) -> str | None:
    """페이지에서 상태 JSON 문자열을 뽑아낸다(script 태그 우선, 없으면 정규식)."""
    for sel in ("script#__NEXT_DATA__::text", "script[id*='PRELOADED']::text"):
        try:
            v = page.css(sel).get()
        except Exception:  # noqa: BLE001
            v = None
        if v:
            return v
    # 정규식 폴백은 **원본 HTML**에서 찾아야 한다.
    # 주의: get_all_text()는 <script> 안의 내용을 돌려주지 않는다(빈 문자열) → 쓰면 안 됨.
    html = None
    for attr in ("html_content", "body"):
        try:
            v = getattr(page, attr, None)
            v = v() if callable(v) else v
            if v:
                html = v if isinstance(v, str) else str(v)
                break
        except Exception:  # noqa: BLE001
            continue
    if html is None:
        html = str(page)
    m = _JSON_BLOB.search(html or "")
    return m.group(1) if m else None


def extract_from_json(page) -> list[dict]:
    """__NEXT_DATA__/프리로드 JSON에서 상품을 추출(1순위 전략)."""
    raw = _raw_json(page)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:  # noqa: BLE001
        return []
    out: list[dict] = []
    _walk(data, out)
    return _dedup(out)


def extract_from_dom(page, sels: dict) -> list[dict]:
    """CSS 폴백 — 해시 클래스명 부분일치(최후의 수단)."""
    rows: list[dict] = []
    for it in common._sel(page, sels["list_item"], adaptive=True):
        href = it.css(sels["link"]).get()
        rows.append(
            {
                "product_id": None,
                "name": common.first(it, sels["name"]),
                "price": to_int(common.first(it, sels["price"])),
                "mall": common.first(it, sels.get("mall", "")),
                "brand": None,
                "category": None,
                "review_count": None,
                "rating": None,
                "image": it.css(sels["image"]).get() if sels.get("image") else None,
                "url": href,
            }
        )
    return _dedup([r for r in rows if r.get("name")])


def search(
    query: str,
    pages: int = 1,
    opts: FetchOptions | None = None,
    limit: int | None = None,
    delay: bool = True,
) -> list[dict]:
    """키워드로 네이버쇼핑을 검색해 상품 목록을 반환한다."""
    opts = opts or FetchOptions(engine="stealthy")  # 네이버는 스텔스 필수
    sels = common.load_selectors("naver", DEFAULT_SELECTORS)
    results: list[dict] = []

    for page_no in range(1, pages + 1):
        url = SEARCH_URL.format(q=quote(query), page=page_no, size=PAGE_SIZE)
        log.info("[네이버] 검색 p%d: %s", page_no, url)
        page = common.with_retry(lambda u=url: common.fetch(u, opts), what=f"naver p{page_no}")

        rows = extract_from_json(page)
        if not rows:
            log.warning("[네이버] JSON 파싱 실패 → CSS 폴백 시도")
            rows = extract_from_dom(page, sels)
        log.info("[네이버] p%d 상품 %d개 파싱", page_no, len(rows))

        results.extend(rows)
        if limit and len(results) >= limit:
            return _dedup(results)[:limit]
        if delay and page_no < pages:
            common.polite_sleep()

    return _dedup(results)

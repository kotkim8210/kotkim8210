"""쿠팡 검색결과 → 경쟁강도 지표.

입력은 coupang-naver-crawler의 `coupang.search()` 출력(dict 리스트)이다.
따라서 네트워크 없이 픽스처로 테스트할 수 있고, 크롤러와 분리돼 있다.

측정하는 것(사용자 요청 매핑):
- "경쟁강도가 낮으며"        → 1페이지 리뷰수 **중앙값**이 낮을수록 진입 쉬움
- "리뷰수 대비 순위 올리기 쉽고" → 리뷰 적은(=이길 만한) 경쟁자 비율
- "광고비 최소한"            → 검색결과 상단 **광고 침투율**이 낮을수록 광고 없이 노출 가능
- (로켓 침투율)             → 로켓배송 비율이 높으면 셀러배송 3P가 배송으로 불리
"""
from __future__ import annotations

from statistics import median

LOW_REVIEW_THRESHOLD = 50  # 이 미만이면 '이길 만한' 경쟁자로 본다


def _nums(values):
    return [v for v in values if isinstance(v, (int, float))]


def analyze(items: list[dict], low_review: int = LOW_REVIEW_THRESHOLD) -> dict:
    """coupang.search() 결과 → 경쟁강도 지표 dict."""
    n = len(items)
    if n == 0:
        return {"n_results": 0, "empty": True}

    prices = sorted(_nums(it.get("price") for it in items))
    reviews = sorted((it.get("rating_count") or 0) for it in items)
    ads = sum(1 for it in items if it.get("is_ad"))
    rockets = sum(1 for it in items if it.get("is_rocket"))
    beatable = sum(1 for r in reviews if r < low_review)

    return {
        "n_results": n,
        "empty": False,
        "price_min": prices[0] if prices else None,
        "price_median": int(median(prices)) if prices else None,
        "price_max": prices[-1] if prices else None,
        "review_min": reviews[0],
        "review_median": int(median(reviews)),
        "review_max": reviews[-1],
        "beatable_count": beatable,               # 리뷰 < low_review 경쟁자 수
        "beatable_ratio": round(beatable / n, 3), # 그 비율(높을수록 진입 쉬움)
        "ad_ratio": round(ads / n, 3),            # 광고 침투율(낮을수록 광고비 부담↓)
        "rocket_ratio": round(rockets / n, 3),    # 로켓 침투율(높을수록 3P 배송 불리)
        "low_review_threshold": low_review,
    }


def summarize(metric: dict) -> str:
    """사람이 읽는 한 줄 요약."""
    if metric.get("empty"):
        return "검색결과 없음(또는 차단)"
    return (
        f"결과 {metric['n_results']}개 · 리뷰중앙값 {metric['review_median']:,} · "
        f"이길만한 경쟁자 {metric['beatable_count']}개({metric['beatable_ratio']*100:.0f}%) · "
        f"광고 {metric['ad_ratio']*100:.0f}% · 로켓 {metric['rocket_ratio']*100:.0f}% · "
        f"최저가 {metric['price_min']:,}원~중앙 {metric['price_median']:,}원"
    )

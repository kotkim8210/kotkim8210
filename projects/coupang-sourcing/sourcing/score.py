"""기회 점수(Opportunity Score) — 여러 신호를 0~100 점수로 합성.

원칙: 검색량(수요)은 높고, 경쟁(리뷰중앙값·광고·로켓)은 낮고, 마진은 나는 키워드가 좋다.
모든 하위 점수와 가중치를 투명하게 노출한다(config/sourcing.json 에서 조정 가능).

    기회점수 = 100 × Σ(가중치 × 하위점수)   (가중치 합 = 1)

하위 점수(각 0~1, 높을수록 좋음):
    demand      검색량 (log 스케일 정규화)
    entry       진입 용이 = 리뷰중앙값 낮음 + 이길만한 경쟁자 비율 높음
    low_ad      1 − 광고 침투율
    delivery    1 − 로켓 침투율 (셀러배송 3P 관점)
    margin      마진율을 안전선 대비로 환산 (마진 게이트)
"""
from __future__ import annotations

import math

DEFAULT_WEIGHTS = {
    "demand": 0.30,
    "entry": 0.30,
    "low_ad": 0.15,
    "delivery": 0.10,
    "margin": 0.15,
}

# 검색량 정규화 기준: total=이 값이면 demand≈1.0 (log10 스케일)
DEMAND_SATURATION = 50000
# 리뷰 중앙값이 이 값 이상이면 entry의 리뷰항목 0점
REVIEW_HARD = 300


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def demand_score(total_searches: int | None) -> float | None:
    if total_searches is None:
        return None
    if total_searches <= 0:
        return 0.0
    return _clamp(math.log10(total_searches + 1) / math.log10(DEMAND_SATURATION))


def entry_score(review_median: int, beatable_ratio: float) -> float:
    """리뷰 중앙값이 낮고, 이길만한(리뷰 적은) 경쟁자가 많을수록 높음."""
    low_review = _clamp(1 - (review_median / REVIEW_HARD))
    return _clamp(0.6 * low_review + 0.4 * beatable_ratio)


def margin_score(margin_rate: float | None, floor: float = 0.10, good: float = 0.30) -> float | None:
    """마진율을 [floor, good] 구간에서 0~1로. floor 미만이면 0, good 이상이면 1."""
    if margin_rate is None:
        return None
    if margin_rate <= 0:
        return 0.0
    return _clamp((margin_rate - floor) / (good - floor))


def opportunity(
    *,
    demand: float | None,
    competition: dict,
    margin_rate: float | None,
    weights: dict | None = None,
) -> dict:
    """하위 점수 합성 → {score, subscores, weights_used}. 신호 없는 항목은 가중치 재정규화."""
    w = dict(weights or DEFAULT_WEIGHTS)
    subs = {
        "demand": demand,
        "entry": entry_score(competition.get("review_median", REVIEW_HARD),
                             competition.get("beatable_ratio", 0.0)) if not competition.get("empty") else 0.0,
        "low_ad": _clamp(1 - competition.get("ad_ratio", 0.0)) if not competition.get("empty") else None,
        "delivery": _clamp(1 - competition.get("rocket_ratio", 0.0)) if not competition.get("empty") else None,
        "margin": margin_score(margin_rate),
    }
    # None(신호없음)은 제외하고 가중치 재정규화
    avail = {k: v for k, v in subs.items() if v is not None}
    wsum = sum(w[k] for k in avail) or 1.0
    score = sum(w[k] * v for k, v in avail.items()) / wsum * 100
    return {
        "score": round(score, 1),
        "subscores": {k: (round(v, 3) if v is not None else None) for k, v in subs.items()},
        "weights_used": {k: round(w[k] / wsum, 3) for k in avail},
        "missing_signals": [k for k, v in subs.items() if v is None],
    }


def grade(score: float) -> str:
    if score >= 70:
        return "A (강력추천)"
    if score >= 55:
        return "B (검토가치)"
    if score >= 40:
        return "C (보통)"
    return "D (비추천)"

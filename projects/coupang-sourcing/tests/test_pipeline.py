#!/usr/bin/env python3
"""경쟁강도·기회점수·파이프라인 오프라인 검증 (크롤링 없이 픽스처 주입).

무설치 실행:  python tests/test_pipeline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sourcing import competition, score  # noqa: E402
from sourcing.margin import BundleSourcing  # noqa: E402
from sourcing.pipeline import evaluate, format_report, rank  # noqa: E402

_checks = 0
_fails = 0


def check(cond, msg, got=None):
    global _checks, _fails
    _checks += 1
    if cond:
        print(f"  ✅ {msg}")
    else:
        _fails += 1
        print(f"  ❌ {msg}" + (f"  (got={got})" if got is not None else ""))


# 쿠팡 검색결과 픽스처: coupang.search() 출력 형태(dict 리스트)
def make_items(reviews, prices, ads=0, rockets=0):
    items = []
    for i, (rv, pr) in enumerate(zip(reviews, prices)):
        items.append({
            "product_id": str(i),
            "name": f"상품{i}",
            "price": pr,
            "rating_count": rv,
            "is_ad": i < ads,
            "is_rocket": i < rockets,
        })
    return items


def test_competition():
    print("[경쟁강도 분석]")
    # 리뷰 적은 블루오션: 리뷰 median 낮고, 광고/로켓 적음
    blue = make_items(reviews=[3, 8, 12, 20, 45], prices=[9900, 10900, 8900, 11900, 9500], ads=1, rockets=1)
    m = competition.analyze(blue)
    check(m["review_median"] == 12, "리뷰 중앙값 12", m["review_median"])
    check(m["beatable_count"] == 5, "리뷰<50 경쟁자 5개(전부)", m["beatable_count"])
    check(m["ad_ratio"] == 0.2, "광고 침투율 20%", m["ad_ratio"])
    check(m["price_min"] == 8900, "최저가 8,900", m["price_min"])

    # 레드오션: 리뷰 수천 개, 로켓 도배
    red = make_items(reviews=[5200, 3100, 8800, 1200, 900], prices=[5900, 6900, 5500, 7900, 6200],
                     ads=2, rockets=5)
    mr = competition.analyze(red)
    check(mr["review_median"] >= 1200, "레드오션 리뷰 중앙값 큼", mr["review_median"])
    check(mr["rocket_ratio"] == 1.0, "로켓 침투율 100%", mr["rocket_ratio"])
    check(mr["beatable_count"] == 0, "이길만한 경쟁자 0", mr["beatable_count"])


def test_scores():
    print("[하위 점수]")
    check(score.demand_score(0) == 0.0, "검색량 0 → demand 0")
    check(score.demand_score(50000) >= 0.99, "검색량 5만 → demand≈1")
    check(score.demand_score(None) is None, "검색량 None → None")
    check(score.margin_score(0.0) == 0.0, "마진 0% → 0")
    check(score.margin_score(0.30) >= 0.99, "마진 30% → 1")
    check(score.margin_score(0.10) == 0.0, "마진=안전선 → 0")
    e_blue = score.entry_score(12, 1.0)
    e_red = score.entry_score(1200, 0.0)
    check(e_blue > e_red, "블루오션 진입점수 > 레드오션", (round(e_blue, 2), round(e_red, 2)))


def test_opportunity_missing_signal():
    print("[기회점수 — 신호 결손 시 가중치 재정규화]")
    blue = competition.analyze(make_items([3, 8, 12, 20, 45], [9900, 10900, 8900, 11900, 9500]))
    # 검색량 신호 없음(None)
    opp = score.opportunity(demand=None, competition=blue, margin_rate=0.30)
    check(opp["subscores"]["demand"] is None, "demand 신호 없음")
    check("demand" in opp["missing_signals"], "missing_signals에 demand")
    check(abs(sum(opp["weights_used"].values()) - 1.0) < 1e-6, "재정규화 후 가중치합=1",
          sum(opp["weights_used"].values()))
    check(0 <= opp["score"] <= 100, "점수 0~100 범위", opp["score"])


def test_evaluate_offline():
    print("[파이프라인 evaluate — 크롤링 없이 픽스처 주입]")
    src = BundleSourcing(bundle_price=9000, bundle_qty=5, inbound_shipping=3000)

    # 블루오션 + 판매 시세 9,900 → 마진 좋고 점수 높아야
    blue = make_items([3, 8, 12, 20, 45], [9900, 10900, 8900, 11900, 9500])
    r_blue = evaluate("블루키워드", sourcing=src, category="언더웨어", competition_items=blue)
    check(r_blue["sale_ref"] == 9900, "시세=리뷰 median가격 9,900", r_blue["sale_ref"])
    check(r_blue["margin"]["마진율"] > 0.25, "마진율 25%+", round(r_blue["margin"]["마진율"], 3))
    check(r_blue["margin_verdict"]["판정"] in ("좋음", "가능"), "마진 판정 양호", r_blue["margin_verdict"]["판정"])

    # 레드오션 + 시세 5,900 → 마진 박하고 진입 어려움 → 점수 낮아야
    red = make_items([5200, 3100, 8800, 1200, 900], [5900, 6900, 5500, 7900, 6200], rockets=5)
    r_red = evaluate("레드키워드", sourcing=src, category="언더웨어", competition_items=red)
    check(r_red["opportunity"]["score"] < r_blue["opportunity"]["score"],
          "레드오션 점수 < 블루오션 점수",
          (r_red["opportunity"]["score"], r_blue["opportunity"]["score"]))

    # 랭킹/리포트 생성
    ranked = rank([r_red, r_blue])
    check(ranked[0]["keyword"] == "블루키워드", "랭킹 1위=블루키워드")
    report = format_report([r_red, r_blue])
    check("기회 리포트" in report and "블루키워드" in report, "리포트 렌더링 OK")

    # 빈 검색결과(차단) 방어
    r_empty = evaluate("차단키워드", sourcing=src, category="언더웨어", competition_items=[])
    check(r_empty["competition"].get("empty") is True, "빈 결과 → empty 처리")
    check(0 <= r_empty["opportunity"]["score"] <= 100, "빈 결과에도 점수 산출(크래시 없음)")


def main() -> int:
    for t in (test_competition, test_scores, test_opportunity_missing_signal, test_evaluate_offline):
        t()
    print(f"\n결과: {_checks - _fails}/{_checks} 통과", "✅" if _fails == 0 else f"❌ {_fails} 실패")
    return 1 if _fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

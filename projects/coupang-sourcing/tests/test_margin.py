#!/usr/bin/env python3
"""쿠팡 마진계산기 오프라인 검증 — 사용자의 심리스팬티 묶음 예시 포함.

무설치 실행:  python tests/test_margin.py   (표준 라이브러리만 사용)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sourcing.margin import (  # noqa: E402
    BundleSourcing,
    CoupangCost,
    ImportSourcing,
    ad_cost_from_cpc,
    ad_cost_from_roas,
    breakeven_price,
    compute,
    verdict,
)

_checks = 0
_fails = 0


def check(cond: bool, msg: str, got=None) -> None:
    global _checks, _fails
    _checks += 1
    if cond:
        print(f"  ✅ {msg}")
    else:
        _fails += 1
        print(f"  ❌ {msg}" + (f"  (got={got})" if got is not None else ""))


def approx(a, b, tol=1.0):
    return abs(a - b) <= tol


def test_bundle_math():
    print("[묶음 아비트라지 원가 계산]")
    # 5장 묶음 9,000원, 사입배송 3,000원, 1묶음 주문
    b = BundleSourcing(bundle_price=9000, bundle_qty=5, inbound_shipping=3000, bundles_per_order=1)
    check(b.units == 5, "총 낱개 5개")
    check(approx(b.unit_cost, 1800), "개당 순매입가 1,800원", b.unit_cost)
    check(approx(b.inbound_ship_per_unit, 600), "개당 배송분담 600원 (3000/5)", b.inbound_ship_per_unit)
    check(approx(b.landed_unit_cost, 2400), "개당 랜디드원가 2,400원", b.landed_unit_cost)

    # 배송비 분산: 10묶음(50장) 한 번에 사입하면 개당 배송분담이 1/10로
    b2 = BundleSourcing(bundle_price=9000, bundle_qty=5, inbound_shipping=3000, bundles_per_order=10)
    check(b2.units == 50, "10묶음=50개")
    check(approx(b2.unit_cost, 1800), "개당 순매입가는 동일 1,800원", b2.unit_cost)
    check(approx(b2.inbound_ship_per_unit, 60), "개당 배송분담 60원으로 급감", b2.inbound_ship_per_unit)


def test_seamless_panty_single_sale():
    print("[심리스팬티 1장 판매 시 진짜 마진 나오나]")
    # 도매꾹: 5장 9,000원 + 배송 3,000 → 개당 랜디드 2,400원
    src = BundleSourcing(bundle_price=9000, bundle_qty=5, inbound_shipping=3000, bundles_per_order=1)
    # 쿠팡 속옷 카테고리 수수료 ~10.8%, 셀러배송 2,500원, 무료배송으로 판매가에 녹임
    cost = CoupangCost(commission_rate=0.108, outbound_shipping=2500, packaging=200, return_rate=0.03)

    # 경쟁사 최저가가 1장 5,900원인 레드오션이라면?
    r_low = compute(5900, src, cost)
    v_low, _ = verdict(r_low, floor=0.10)
    check(r_low["순마진"] < 800, "판매가 5,900원이면 마진 거의 없음", round(r_low["순마진"]))
    check(v_low in ("주의", "가능", "역마진"), f"판정='{v_low}' (박함)", v_low)

    # 낱개 판매가를 9,900원으로 올리면 (묶음 대비 낱개 프리미엄)
    r_hi = compute(9900, src, cost)
    v_hi, reason = verdict(r_hi, floor=0.10)
    check(r_hi["순마진"] > 2500, "판매가 9,900원이면 개당 2,500원+ 마진", round(r_hi["순마진"]))
    check(r_hi["마진율"] > 0.25, "마진율 25%+", round(r_hi["마진율"], 3))
    check(v_hi == "좋음", f"판정='{v_hi}' ({reason})", v_hi)

    # 총비용 = 판매가 − 순마진 이 항목합과 일치하는지(정합성)
    check(approx(r_hi["총비용"], sum(r_hi["비용상세"].values())), "비용상세 합 = 총비용")
    check(approx(r_hi["판매가"] - r_hi["총비용"], r_hi["순마진"]), "판매가-총비용=순마진")


def test_breakeven():
    print("[목표마진 역산]")
    src = BundleSourcing(bundle_price=9000, bundle_qty=5, inbound_shipping=3000)
    cost = CoupangCost(commission_rate=0.108, outbound_shipping=2500, packaging=200, return_rate=0.03)
    # 목표 마진 20% 남기려면 최소 판매가?
    p = breakeven_price(src, cost, target_margin=0.20)
    r = compute(p, src, cost)
    check(approx(r["마진율"], 0.20, 0.02), f"역산가 {p:,}원에서 마진율≈20%", round(r["마진율"], 3))
    # 그 가격 미만이면 20% 미달
    r_under = compute(p - 1000, src, cost)
    check(r_under["마진율"] < 0.20, "역산가 미만이면 목표 미달")


def test_free_vs_paid_shipping():
    print("[무료배송 판가녹임 vs 유료배송]")
    src = BundleSourcing(bundle_price=9000, bundle_qty=5, inbound_shipping=3000)
    # 무료배송: 배송비를 판매가에 녹임(outbound=0), 판매가 9,900
    free = compute(9900, src, CoupangCost(commission_rate=0.108, outbound_shipping=0, packaging=200))
    # 유료배송: 상품가 7,400 + 배송비 2,500 별도 → 고객체감 동일 9,900, 그러나 수수료는 상품가에만?
    # 쿠팡은 배송비에도 3% 부과하지만 여기선 보수적으로 상품가 기준 수수료만 비교
    paid = compute(7400, src, CoupangCost(commission_rate=0.108, outbound_shipping=2500, packaging=200))
    check(free["순마진"] > paid["순마진"], "무료배송(판가녹임)이 수수료 측면서 유리",
          (round(free["순마진"]), round(paid["순마진"])))


def test_import_cost_breakdown():
    print("[1688 직수입 원가 분해]")
    # 개당 8 CNY × 500개, 환율 195, 내륙 200 CNY, 국제운임 40만원, 관세 8%, 통관 3만
    imp = ImportSourcing(
        unit_price_cny=8, qty=500, fx_rate=195, china_domestic_cny=200,
        intl_shipping=400000, duty_rate=0.08, customs_fee=30000, vat_deductible=True,
    )
    # 물품가 = (8×500 + 200) × 195 = 4200 × 195 = 819,000
    check(approx(imp.goods_krw, 819000), "물품가 819,000원", imp.goods_krw)
    # CIF = 819,000 + 400,000 = 1,219,000
    check(approx(imp.cif, 1219000), "CIF 1,219,000원", imp.cif)
    # 관세 = CIF × 8% = 97,520
    check(approx(imp.duty, 97520), "관세 97,520원", imp.duty)
    # 수입부가세 = (CIF+관세) × 10% = 131,652
    check(approx(imp.import_vat, 131652), "수입부가세 131,652원", imp.import_vat)
    # 랜디드총액 = CIF + 관세 + 통관 = 1,346,520 (부가세는 공제되어 제외)
    check(approx(imp.landed_total, 1346520), "랜디드총액 1,346,520원(부가세 제외)", imp.landed_total)
    check(approx(imp.landed_unit_cost, 2693.04, 1), "개당 랜디드 2,693원", imp.landed_unit_cost)
    check(approx(imp.vat_credit_per_unit, 263.3, 1), "개당 공제 매입세액 263원", imp.vat_credit_per_unit)

    # 간이/면세 사업자면 수입부가세가 원가에 포함되어 더 비싸진다
    imp2 = ImportSourcing(unit_price_cny=8, qty=500, fx_rate=195, china_domestic_cny=200,
                          intl_shipping=400000, duty_rate=0.08, customs_fee=30000, vat_deductible=False)
    check(imp2.landed_unit_cost > imp.landed_unit_cost, "공제불가면 개당 원가 상승",
          (round(imp2.landed_unit_cost), round(imp.landed_unit_cost)))
    check(imp2.vat_credit_per_unit == 0, "공제불가면 매입세액 0")


def test_vat_modes():
    print("[부가세 모드별 차이]")
    src = BundleSourcing(bundle_price=9000, bundle_qty=5, inbound_shipping=3000)
    base = dict(commission_rate=0.108, outbound_shipping=3000, packaging=200, return_rate=0.02)
    none_r = compute(9900, src, CoupangCost(**base, vat_mode="none"))
    simp_r = compute(9900, src, CoupangCost(**base, vat_mode="simplified"))
    norm_r = compute(9900, src, CoupangCost(**base, vat_mode="normal"))
    check(none_r["순마진"] > simp_r["순마진"], "부가세 미반영이 가장 낙관적",
          (round(none_r["순마진"]), round(simp_r["순마진"])))
    check(norm_r["순마진"] < none_r["순마진"], "일반과세는 순마진을 깎는다",
          (round(norm_r["순마진"]), round(none_r["순마진"])))
    # 일반과세 부가세 = 매출/11 − (매입세액 + (택배+포장)/11)
    expect = 9900 / 11 - (src.vat_credit_per_unit + (3000 + 200) / 11)
    check(approx(norm_r["비용상세"]["부가세"], expect, 1), "일반과세 부가세 = 매출세액-매입세액",
          round(norm_r["비용상세"]["부가세"]))


def test_ad_cost_models():
    print("[광고비 모델]")
    # CPC 300원, 전환율 3% → 판매 1건당 광고비 10,000원
    check(approx(ad_cost_from_cpc(300, 0.03), 10000), "CPC300·전환3% → 10,000원/건",
          ad_cost_from_cpc(300, 0.03))
    # 전환율 1%면 3만원 — 마진을 통째로 먹음
    check(approx(ad_cost_from_cpc(300, 0.01), 30000), "전환1% → 30,000원/건")
    # 목표 ROAS 500% → 판매가의 20%
    check(approx(ad_cost_from_roas(20000, 5), 4000), "ROAS500%·2만원 → 4,000원")

    # 광고비를 넣으면 마진이 실제로 깎이는지
    src = BundleSourcing(bundle_price=9000, bundle_qty=5, inbound_shipping=3000)
    no_ad = compute(9900, src, CoupangCost(commission_rate=0.108, outbound_shipping=3000, ad_cost_per_unit=0))
    with_ad = compute(9900, src, CoupangCost(commission_rate=0.108, outbound_shipping=3000, ad_cost_per_unit=2000))
    check(approx(no_ad["순마진"] - with_ad["순마진"], 2000), "광고비 2,000원만큼 순마진 감소",
          round(no_ad["순마진"] - with_ad["순마진"]))


def main() -> int:
    for t in (test_bundle_math, test_seamless_panty_single_sale, test_breakeven, test_free_vs_paid_shipping,
              test_import_cost_breakdown, test_vat_modes, test_ad_cost_models):
        t()
    print(f"\n결과: {_checks - _fails}/{_checks} 통과", "✅" if _fails == 0 else f"❌ {_fails} 실패")
    return 1 if _fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

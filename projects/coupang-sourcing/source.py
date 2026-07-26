#!/usr/bin/env python3
"""쿠팡 자동 소싱기 CLI.

세 가지 명령:

  margin   — 묶음 사입가로 진짜 마진이 남는지 계산 (네트워크 불필요, 즉시 사용)
      python source.py margin --sale 9900 --bundle-price 9000 --bundle-qty 5 \
                              --inbound 3000 --category 언더웨어

  eval     — 키워드를 종합 평가(경쟁강도+검색량+마진 → 기회점수)
      python source.py eval --query "심리스팬티" --bundle-price 9000 --bundle-qty 5 \
                            --inbound 3000 --category 언더웨어

  xhs      — 샤오홍수 트렌드 키워드로 후보를 만들어 쿠팡 기준으로 일괄 평가
      python source.py xhs --bundle-price 9000 --bundle-qty 5 --inbound 3000
"""
from __future__ import annotations

import argparse
import json
import sys

from sourcing import pipeline, xiaohongshu
from sourcing.margin import (
    BundleSourcing,
    blended_ad_cost,
    CoupangCost,
    ImportSourcing,
    ad_cost_from_cpc,
    ad_cost_from_roas,
    breakeven_price,
    compute,
    verdict,
)


def _sourcing_from(a) -> BundleSourcing:
    return BundleSourcing(
        bundle_price=a.bundle_price,
        bundle_qty=a.bundle_qty,
        inbound_shipping=a.inbound,
        bundles_per_order=a.bundles,
    )


def _add_bundle_args(p):
    p.add_argument("--bundle-price", type=int, required=True, help="도매 묶음 총 매입가(원)")
    p.add_argument("--bundle-qty", type=int, required=True, help="묶음당 낱개 수량")
    p.add_argument("--inbound", type=int, default=0, help="도매 사입배송비(주문 1회, 원)")
    p.add_argument("--bundles", type=int, default=1, help="한 번에 사입할 묶음 수(많을수록 배송분담↓)")
    p.add_argument("--category", default="언더웨어", help="쿠팡 카테고리(수수료 결정)")
    p.add_argument("--outbound", type=int, default=3000,
                   help="고객배송 택배원가(무료배송이라도 셀러 실부담. 기본 3,000)")
    p.add_argument("--return-rate", type=float, default=0.02, help="반품율(기본 0.02)")
    p.add_argument("--vat", choices=["none", "simplified", "normal"], default="normal",
                   help="부가세 모드 (기본 normal=일반과세자)")
    p.add_argument("--floor", type=float, default=0.10, help="마진 안전선(기본 0.10)")
    # 광고비: 셋 중 하나로 지정 (직접 / CPC·전환율 / 목표ROAS)
    p.add_argument("--ad", type=int, default=None, help="개당 광고비를 직접 지정(원)")
    p.add_argument("--cpc", type=float, default=None, help="쿠팡 광고 CPC(원). --cvr과 함께 사용")
    p.add_argument("--cvr", type=float, default=None, help="전환율(예: 0.03=3%%). --cpc와 함께 사용")
    p.add_argument("--roas", type=float, default=None, help="목표 ROAS(예: 5=500%%) → 개당 허용광고비 역산")
    p.add_argument("--ad-share", type=float, default=None,
                   help="전체 판매 중 광고 기여 비중(0.2=20%%). 주면 blended 광고비로 환산")


def _ad_per_unit(a, sale: float) -> tuple[float, str]:
    """--ad / --cpc+--cvr / --roas 중 지정된 방식으로 개당 광고비를 정한다.

    --ad-share를 주면 '광고로 팔린 비중'만큼만 부담하는 blended 광고비로 환산한다.
    """
    share = getattr(a, "ad_share", None)
    if a.ad is not None:
        return float(a.ad), "직접지정"
    if a.cpc is not None and a.cvr is not None:
        per_sale = ad_cost_from_cpc(a.cpc, a.cvr)
        note = f"CPC {a.cpc:,.0f}원 ÷ 전환율 {a.cvr*100:.1f}% = 건당 {per_sale:,.0f}원"
        if share is not None:
            return blended_ad_cost(per_sale, share), note + f" × 광고판매비중 {share*100:.0f}%"
        return per_sale, note + " (전량 광고 판매 가정)"
    if a.roas is not None:
        return ad_cost_from_roas(sale, a.roas), f"목표ROAS {a.roas*100:.0f}%"
    return 0.0, "0원(무광고 가정)"


def _build_cost(a, sale: float) -> tuple[CoupangCost, str]:
    fees = pipeline.load_config().get("coupang_fees", {})
    ad, ad_note = _ad_per_unit(a, sale)
    return CoupangCost(
        commission_rate=pipeline.fee_rate(a.category, fees),
        outbound_shipping=a.outbound, return_rate=a.return_rate,
        vat_mode=a.vat, ad_cost_per_unit=int(round(ad)),
    ), ad_note


def cmd_margin(a) -> int:
    src = _sourcing_from(a)
    cost, ad_note = _build_cost(a, a.sale)
    res = compute(a.sale, src, cost)
    v, reason = verdict(res, a.floor)
    be = breakeven_price(src, cost, target_margin=max(a.floor, 0.15))

    _print_margin(res, v, reason, be, a, src, ad_note, title=f"쿠팡 마진 계산: {a.category}")
    return 0


def _print_margin(res, v, reason, be, a, src, ad_note, title: str) -> None:
    vat_label = {"none": "미반영", "simplified": "간이과세", "normal": "일반과세"}[a.vat]
    print(f"\n=== {title} · 판매가 {a.sale:,}원 ===")
    print(f"개당 랜디드원가 : {res['랜디드원가']:,.0f}원 "
          f"(순매입 {src.unit_cost:,.0f} + 부대비 분담 {src.inbound_ship_per_unit:,.0f})")
    print(f"가정            : 부가세 {vat_label} · 광고비 {ad_note}")
    print("비용 상세(개당):")
    for k, val in res["비용상세"].items():
        if val:
            print(f"  - {k:12s}: {val:9,.0f}원")
    print(f"→ 순마진 : {res['순마진']:,.0f}원  |  마진율 {res['마진율']*100:.1f}%  |  ROI {res['ROI']*100:.0f}%")
    print(f"→ 판정   : [{v}] {reason}")
    print(f"→ 참고   : 마진 {max(a.floor,0.15)*100:.0f}% 남기려면 최소 판매가 {be:,}원\n")


def cmd_import(a) -> int:
    """중국 1688 등 직수입 조건으로 마진 계산."""
    src = ImportSourcing(
        unit_price_cny=a.cny, qty=a.qty, fx_rate=a.fx,
        china_domestic_cny=a.china_ship,
        intl_shipping=a.freight, weight_kg=a.weight, intl_rate_per_kg=a.per_kg,
        duty_rate=a.duty, customs_fee=a.customs,
        vat_deductible=(a.vat == "normal"),
    )
    cost, ad_note = _build_cost(a, a.sale)
    res = compute(a.sale, src, cost)
    v, reason = verdict(res, a.floor)
    be = breakeven_price(src, cost, target_margin=max(a.floor, 0.15))

    print(f"\n=== 수입원가 분해 (1688 기준, {a.qty:,}개 수입) ===")
    print(f"  물품가      : {src.goods_krw:>12,.0f}원  (CNY {a.cny}×{a.qty} + 내륙 {a.china_ship} @ {a.fx})")
    print(f"  국제운임    : {src.freight_krw:>12,.0f}원")
    print(f"  ─ CIF(과세가): {src.cif:>12,.0f}원")
    print(f"  관세({a.duty*100:.0f}%)   : {src.duty:>12,.0f}원")
    print(f"  통관·포워더 : {src.customs_fee:>12,.0f}원")
    print(f"  수입부가세  : {src.import_vat:>12,.0f}원  "
          f"({'일반과세 → 매입세액 공제(원가 제외)' if src.vat_deductible else '공제불가 → 원가 포함'})")
    print(f"  ═ 랜디드총액: {src.landed_total:>12,.0f}원  → 개당 {src.landed_unit_cost:,.0f}원")
    _print_margin(res, v, reason, be, a, src, ad_note, title="쿠팡 마진(직수입)")
    return 0


def cmd_eval(a) -> int:
    src = _sourcing_from(a)
    res = pipeline.evaluate(a.query, sourcing=src, category=a.category, pages=a.pages, limit=a.limit)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    else:
        print(pipeline.format_report([res]))
        _print_detail(res)
    return 0


def cmd_xhs(a) -> int:
    cand = xiaohongshu.load_manual()
    if a.query:  # 특정 키워드로 자동수집 시도
        cand = xiaohongshu.fetch_notes(a.query) or cand
    if not cand:
        print("샤오홍수 후보가 없습니다. config/xhs_manual.json 에 키워드를 넣거나 --query 로 시도하세요.",
              file=sys.stderr)
        return 1
    src = _sourcing_from(a)
    results = []
    for c in cand[: a.limit_kw]:
        kw = c["keyword"]
        print(f"· 평가 중: {kw}", file=sys.stderr)
        results.append(pipeline.evaluate(kw, sourcing=src, category=a.category))
    print(pipeline.format_report(results))
    return 0


def _print_detail(res: dict) -> None:
    o = res["opportunity"]
    print(f"\n[기회점수 {o['score']} · {res['grade']}]  하위점수: "
          + ", ".join(f"{k}={v}" for k, v in o["subscores"].items() if v is not None))
    if o["missing_signals"]:
        print(f"  (신호없음: {', '.join(o['missing_signals'])})")
    print(f"  경쟁: {pipeline.competition.summarize(res['competition'])}")
    if res["margin"]:
        print(f"  마진판정: [{res['margin_verdict']['판정']}] {res['margin_verdict']['사유']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="source.py", description="쿠팡 자동 소싱기 (경쟁강도+검색량+묶음 마진게이트)",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    pm = sub.add_parser("margin", help="국내 도매 묶음 사입가로 진짜 마진 계산")
    pm.add_argument("--sale", type=int, required=True, help="쿠팡 판매가(원)")
    _add_bundle_args(pm)

    pi = sub.add_parser("import", help="중국 1688 직수입 원가로 마진 계산(환율·관세·수입부가세 포함)")
    pi.add_argument("--sale", type=int, required=True, help="쿠팡 판매가(원)")
    pi.add_argument("--cny", type=float, required=True, help="1688 개당 단가(CNY)")
    pi.add_argument("--qty", type=int, required=True, help="수입 수량")
    pi.add_argument("--fx", type=float, default=195.0, help="CNY→KRW 환율(기본 195, 수수료 포함 권장)")
    pi.add_argument("--china-ship", type=float, default=0, help="중국 내륙배송(CNY)")
    pi.add_argument("--freight", type=float, default=0, help="국제운임 총액(원). 지정 시 무게계산 무시")
    pi.add_argument("--weight", type=float, default=0, help="총 중량/부피중량(kg)")
    pi.add_argument("--per-kg", type=float, default=0, help="kg당 국제운임(원)")
    pi.add_argument("--duty", type=float, default=0.08, help="관세율(기본 0.08). FTA 적용 시 낮춤")
    pi.add_argument("--customs", type=float, default=30000, help="통관+포워더 수수료(건당, 원)")
    pi.add_argument("--category", default="홈인테리어", help="쿠팡 카테고리(수수료)")
    pi.add_argument("--outbound", type=int, default=3000, help="고객배송 택배원가")
    pi.add_argument("--return-rate", type=float, default=0.02)
    pi.add_argument("--vat", choices=["none", "simplified", "normal"], default="normal")
    pi.add_argument("--floor", type=float, default=0.10)
    pi.add_argument("--ad", type=int, default=None, help="개당 광고비 직접 지정(원)")
    pi.add_argument("--cpc", type=float, default=None, help="광고 CPC(원)")
    pi.add_argument("--cvr", type=float, default=None, help="전환율(0.03=3%%)")
    pi.add_argument("--roas", type=float, default=None, help="목표 ROAS(5=500%%)")
    pi.add_argument("--ad-share", type=float, default=None,
                    help="전체 판매 중 광고 기여 비중(0.2=20%%)")

    pe = sub.add_parser("eval", help="키워드 종합 평가(기회점수)")
    pe.add_argument("--query", required=True, help="검색 키워드")
    pe.add_argument("--pages", type=int, default=1)
    pe.add_argument("--limit", type=int, default=40)
    pe.add_argument("--json", action="store_true", help="JSON 출력")
    _add_bundle_args(pe)

    px = sub.add_parser("xhs", help="샤오홍수 트렌드 키워드 일괄 평가")
    px.add_argument("--query", help="샤오홍수 자동수집 시도할 키워드(생략 시 xhs_manual.json 사용)")
    px.add_argument("--limit-kw", type=int, default=10, help="평가할 키워드 최대 수")
    _add_bundle_args(px)

    a = ap.parse_args(argv)
    if a.cmd == "margin":
        return cmd_margin(a)
    if a.cmd == "import":
        return cmd_import(a)
    if a.cmd == "eval":
        return cmd_eval(a)
    if a.cmd == "xhs":
        return cmd_xhs(a)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

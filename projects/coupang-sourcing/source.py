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
from sourcing.margin import BundleSourcing, CoupangCost, breakeven_price, compute, verdict


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
    p.add_argument("--vat", choices=["none", "simplified", "normal"], default="none", help="부가세 모드")
    p.add_argument("--floor", type=float, default=0.10, help="마진 안전선(기본 0.10)")


def cmd_margin(a) -> int:
    src = _sourcing_from(a)
    fees = pipeline.load_config().get("coupang_fees", {})
    cost = CoupangCost(
        commission_rate=pipeline.fee_rate(a.category, fees),
        outbound_shipping=a.outbound, return_rate=a.return_rate, vat_mode=a.vat,
    )
    res = compute(a.sale, src, cost)
    v, reason = verdict(res, a.floor)
    be = breakeven_price(src, cost, target_margin=max(a.floor, 0.15))

    print(f"\n=== 쿠팡 마진 계산: {a.category} · 판매가 {a.sale:,}원 ===")
    print(f"개당 랜디드원가 : {res['랜디드원가']:,.0f}원 "
          f"(순매입 {src.unit_cost:,.0f} + 배송분담 {src.inbound_ship_per_unit:,.0f})")
    print("비용 상세(개당):")
    for k, val in res["비용상세"].items():
        if val:
            print(f"  - {k:12s}: {val:8,.0f}원")
    print(f"→ 순마진 : {res['순마진']:,.0f}원  |  마진율 {res['마진율']*100:.1f}%  |  ROI {res['ROI']*100:.0f}%")
    print(f"→ 판정   : [{v}] {reason}")
    print(f"→ 참고   : 마진 {max(a.floor,0.15)*100:.0f}% 남기려면 최소 판매가 {be:,}원\n")
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

    pm = sub.add_parser("margin", help="묶음 사입가로 진짜 마진 계산")
    pm.add_argument("--sale", type=int, required=True, help="쿠팡 판매가(원)")
    _add_bundle_args(pm)

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
    if a.cmd == "eval":
        return cmd_eval(a)
    if a.cmd == "xhs":
        return cmd_xhs(a)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

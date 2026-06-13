#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공급단가 + 시세 → 마진 리포트 생성기
------------------------------------------------------------------
입력:
  - pricing/supply_prices.json   공급가(매입가) 추적 원장
  - pricing/market_prices.json   당근 시세(경쟁사 판매가) 참고 원장
  - listings/products.json       현재 등록 판매가(list price)

출력:
  - pricing/MARGIN_REPORT.md     (덮어쓰기 — 직접 편집 금지)

사용:  python3 pricing/build_report.py
원리:  순마진 = 판매가 − 공급가 − 판매가×(결제+판매수수료) − 포장비
       '진짜로 받는 가격'은 보통 list가 아니라 시세이므로, list 기준과 시세 기준을
       모두 계산해 둘을 비교한다(시세추적기 + 공급단가추적을 한 표에서 함께 본다).
"""

import json
import os

# ── 비용/수수료 (당근 공식 안내 기준) ────────────────────────────────────
# 출처: 당근 비즈프로필 상품 판매 안내 — "구매확정된 주문에 대해 결제 수수료를 포함한
#       3.3%(부가세 포함)가 부과됩니다. 정산은 구매확정일로부터 영업일 3일 뒤."
# → 결제+판매 통합 단일 수수료 3.3%. 별도 결제수수료가 추가되지 않음.
CARROT_FEE_RATE = 0.033   # 당근 통합 수수료(결제+판매 합산, VAT 포함)
PACKAGING_COST  = 0       # 산지직송·무료배송(공급가에 포함) → 추가 물류비 0 가정
MARGIN_FLOOR    = 0.05    # 손익 안전선(이 아래면 ⚠️)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def won(n):
    if n is None:
        return "—"
    return f"{round(n):,}원"


def pct(x):
    if x is None:
        return "—"
    return f"{x*100:.1f}%"


def signed_won(n):
    if n is None:
        return "—"
    return f"{'+' if n > 0 else ''}{n:,}원"


def signed_pct(x):
    if x is None:
        return "—"
    return f"{'+' if x > 0 else ''}{x*100:.1f}%"


def opt_label(it):
    """스냅샷 항목 → 짧은 옵션 라벨. 예: '중품 5개', '특품 10개', '애플 20개'."""
    grade = "애플" if "애플" in it.get("line", "") else it.get("grade", "")
    return f"{grade} {it['qty']}개".strip()


def fee_on(sale):
    return round(sale * CARROT_FEE_RATE) + PACKAGING_COST


def margin(sale, supply):
    """판매가/공급가 → (순마진액, 마진율). sale 없으면 (None, None)."""
    if not sale:
        return None, None
    net = sale - supply - fee_on(sale)
    return net, net / sale


def main():
    supply_doc = load(os.path.join(ROOT, "pricing", "supply_prices.json"))
    market_doc = load(os.path.join(ROOT, "pricing", "market_prices.json"))
    products = load(os.path.join(ROOT, "listings", "products.json"))

    snaps = sorted(supply_doc["snapshots"], key=lambda s: s["seq"])
    latest, prev = snaps[-1], (snaps[-2] if len(snaps) >= 2 else None)
    base_date = latest["date"]

    # 판매가(list) 조회: product_id+qty → price, 상품 메타
    list_price, prod_meta = {}, {}
    for p in products["products"]:
        prod_meta[p["id"]] = p
        for o in p.get("options", []):
            if "qty" in o:
                list_price[(p["id"], o["qty"])] = o["price"]

    # 시세 조회: product_id+qty → price (+sample 여부)
    market = {}
    for ref in market_doc["references"]:
        for pid in ref.get("applies_to", []):
            for o in ref["options"]:
                market[(pid, o["qty"])] = (o["price"], ref.get("sample", False))

    def supply_map(snap):
        return {(it["product_id"], it["qty"]): it["supply"] for it in snap["items"]}

    now_supply = supply_map(latest)
    prev_supply = supply_map(prev) if prev else {}

    # 출력 순서: latest 스냅샷의 product_id 등장순 → qty 오름차순
    order, seen = [], set()
    for it in latest["items"]:
        if it["product_id"] not in seen:
            seen.add(it["product_id"])
            order.append(it["product_id"])

    L = []
    w = L.append
    w("# 🌽 공급단가 + 시세 마진 리포트")
    w("")
    w(f"> **기준일 {base_date}** · 통화 KRW · `pricing/build_report.py` 자동 생성 — 직접 편집 금지")
    w(f"> 공급가 출처: {latest['source']}")
    w(f"> 비용: **당근 통합 수수료 {CARROT_FEE_RATE*100:.1f}%(결제+판매, VAT 포함, 당근 공식 안내 기준)** + 포장비 {won(PACKAGING_COST)} "
      "(산지직송·무료배송 → 물류비 0 가정)")
    w("")
    w("> **핵심**: 실제로 '받는 가격'은 보통 등록 판매가(list)가 아니라 **시세(경쟁사 가격)**다. "
      "그래서 마진은 *판매가 − 공급가*가 아니라 **시세 − 공급가**로 봐야 현실적이다. "
      "→ 시세추적기(시장가) + 공급단가추적(매입가)을 **함께** 봐야 하는 이유.")
    w("")

    # ── 1. 최신 공급가 스냅샷 ───────────────────────────────────────────
    w("## 1. 최신 공급가 스냅샷 (매입가, 비공개)")
    w("")
    w(f"PBF Company 파트너 어드민 기준 · {base_date} · 비과세 · 무료배송 포함")
    w("")
    cur_line = None
    for pid in order:
        for it in [i for i in latest["items"] if i["product_id"] == pid]:
            if it["line"] != cur_line:
                cur_line = it["line"]
                w(f"**{cur_line}**  ·  `{pid}`")
                w("")
                w("| 구성 | 공급가 | 개당 매입가 |")
                w("|---|---:|---:|")
            w(f"| {it['qty']}개 | {won(it['supply'])} | {won(it['supply']/it['qty'])} |")
        w("")

    # ── 2. 공급가 변동 (직전 → 현재) ────────────────────────────────────
    if prev:
        w(f"## 2. 공급가 변동 — {prev['label']} → {latest['label']}")
        w("")
        w("| 옵션 | 직전 공급가 | 현재 공급가 | 변동액 | 변동률 |")
        w("|---|---:|---:|---:|---:|")
        for pid in order:
            for it in [i for i in latest["items"] if i["product_id"] == pid]:
                key = (pid, it["qty"])
                p = prev_supply.get(key)
                cur = it["supply"]
                if p is None:
                    w(f"| {opt_label(it)} | — | {won(cur)} | (신규) | — |")
                    continue
                d = cur - p
                dr = d / p
                flag = " 🔻" if dr <= -0.05 else (" 🔺" if dr >= 0.05 else "")
                w(f"| {opt_label(it)} | {won(p)} | {won(cur)} | {signed_won(d)} | {signed_pct(dr)}{flag} |")
        w("")
        w("> 🔻 = 5%+ 하락, 🔺 = 5%+ 상승. 협상 없이도 **중품 공급가가 크게 빠진 것**이 핵심.")
        w("")

    # ── 3. 마진 분석 (판매가 기준 vs 시세 기준) ─────────────────────────
    w("## 3. 마진 분석 — 등록 판매가(list) 기준 vs 시세 기준")
    w("")
    w("| 옵션 | 등록판매가 | 공급가 | 수수료(3.3%) | 순마진(판매가) | 마진율(판매가) | 시세 | 마진율(시세) |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|")
    for pid in order:
        for it in [i for i in latest["items"] if i["product_id"] == pid]:
            qty = it["qty"]
            supply = it["supply"]
            sale = list_price.get((pid, qty))
            net_l, mr_l = margin(sale, supply)
            mk = market.get((pid, qty))
            mk_price = mk[0] if mk else None
            mk_sample = mk[1] if mk else False
            net_m, mr_m = margin(mk_price, supply)
            warn_l = " ⚠️" if (mr_l is not None and mr_l < MARGIN_FLOOR) else ""
            warn_m = " ⚠️" if (mr_m is not None and mr_m < MARGIN_FLOOR) else ""
            mk_label = (won(mk_price) + ("*" if mk_sample else "")) if mk_price else "—"
            w(f"| {opt_label(it)} | {won(sale)} | {won(supply)} | {won(fee_on(sale) if sale else None)} "
              f"| {won(net_l)} | {pct(mr_l)}{warn_l} | {mk_label} | {pct(mr_m)}{warn_m} |")
    w("")
    w(f"> `*` = 임시 시세(추적기 가동 전 예시값). ⚠️ = 마진율 {MARGIN_FLOOR*100:.0f}% 미만(안전선 아래). "
      "시세 열이 비면 추적기 수집 대기.")
    w("")

    # ── 4. 인사이트 & 권장 ──────────────────────────────────────────────
    # 시세 기준 마진율이 잡히는 옵션들의 직전 대비 회복폭 계산
    insights, danger = [], []
    for pid in order:
        for it in [i for i in latest["items"] if i["product_id"] == pid]:
            qty, supply = it["qty"], it["supply"]
            mk = market.get((pid, qty))
            if not mk:
                continue
            mk_price, mk_sample = mk
            _, mr_now = margin(mk_price, supply)
            if mr_now is not None and mr_now < MARGIN_FLOOR:
                danger.append((opt_label(it), mr_now, mk_sample))
            p = prev_supply.get((pid, qty))
            if p is None:
                continue
            _, mr_then = margin(mk_price, p)
            if abs(mr_now - mr_then) >= 0.005:
                insights.append((opt_label(it), mr_then, mr_now))

    w("## 4. 인사이트 & 권장")
    w("")
    if insights:
        w("**같은 시세에서 공급가 변동만으로 움직인 마진율** (변동폭 0.5% 미만은 생략)")
        w("")
        w("| 옵션 | 시즌피크 공급가 기준 | 현재 공급가 기준 | 회복폭 |")
        w("|---|---:|---:|---:|")
        for name, then, now in insights:
            w(f"| {name} | {pct(then)} | {pct(now)} | {signed_pct((now-then))} |")
        w("")
    if danger:
        names = ", ".join(f"{n}({pct(m)}{'*' if s else ''})" for n, m, s in danger)
        w(f"- ⚠️ **시세 기준 안전선({MARGIN_FLOOR*100:.0f}%) 아래 옵션:** {names}. "
          "시세 추정이 보수적이라 그런 경우가 많으니 추적기 실측으로 검증 후 가격/공급가 재검토 권장.")
    w("- **협상 보류 OK.** 시즌 종료로 중품 공급가가 자연 하락(−18~29%)했고, 등록가도 시세 근처로 조정했다. "
      "추가 단가 인하 압박의 실익은 작다.")
    w("- **list = 시세 매칭 완료(2026-06-13).** 옥수수 12개 옵션 모두 시세에 산지직송 프리미엄(중품 +1,000원 / "
      "특품 +2,000원 / 애플 +2,000원)만 얹은 수준으로 내렸다. 받을 가격과 표시가가 거의 같아져 list 마진 ≈ 시세 마진.")
    w("- **다음 액션은 실측 추적:** ①시세추적기를 라이브로 돌려 일·주 단위 시세 변동 감지 "
      "②특품/애플의 sample 시세를 실측으로 교체(특히 애플 — 현재 +20% 추정값) "
      "③PBF 캡처 받을 때마다 `supply_prices.json`에 스냅샷 추가.")
    w("")
    w("---")
    w("")
    w("### 가정 / 한계")
    w(f"- 통합 수수료 {CARROT_FEE_RATE*100:.1f}%는 **당근 공식 안내**(비즈프로필 상품판매 — 결제수수료 포함 3.3% VAT 포함, "
      f"구매확정 후 영업일 3일 정산). 별도 결제수수료 없음. 포장비 {won(PACKAGING_COST)}은 산지직송·무료배송 가정.")
    w("- 광고비는 옵션별 변동이라 단위 마진에서 제외(별도 관리).")
    w("- 시세는 임시 예시값(`*`) 위주 — 추적기 실측이 모이면 `market_prices.json` 갱신 후 재생성.")
    w("- 공급가는 비공개 데이터. 이 리포트와 `supply_prices.json`을 고객 노출 산출물에 노출 금지.")
    w("")
    w(f"*재생성: `python3 pricing/build_report.py` · 입력 스냅샷 {len(snaps)}개(최신 {base_date})*")
    w("")

    out = os.path.join(ROOT, "pricing", "MARGIN_REPORT.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"wrote {out}  ({len(L)} lines, {len(snaps)} snapshots, base {base_date})")


if __name__ == "__main__":
    main()

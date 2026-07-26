"""소싱 파이프라인 — 키워드 → 신호 수집 → 마진 게이트 → 기회 점수 → 판정.

한 키워드에 대해:
    1) 쿠팡 검색결과 크롤링(coupang-naver-crawler 재사용) → 경쟁강도
    2) 네이버 검색광고 API → 월간 검색량 (키 없으면 생략)
    3) 도매 묶음 사입가 + 경쟁사 시세 → 마진계산기로 진짜 마진 판정
    4) 위 신호를 기회 점수로 합성 → GO/보류/SKIP

크롤링은 이 개발 샌드박스에선 프록시에 막히지만(coupang-naver-crawler 참고),
사용자 PC에서 실행하면 실데이터로 동작한다. 크롤러가 없거나 실패하면
`competition_items`를 직접 주입해 오프라인으로도 평가할 수 있다(테스트가 그렇게 한다).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from . import competition, naver_ads, score
from .margin import BundleSourcing, CoupangCost, compute, verdict

log = logging.getLogger("sourcing.pipeline")
CONFIG = Path(__file__).resolve().parent.parent / "config"


def load_config() -> dict:
    cfg = {"weights": None, "margin_floor": 0.10, "coupang_fees": {}, "defaults": {}}
    sp = CONFIG / "sourcing.json"
    if sp.exists():
        cfg.update(json.loads(sp.read_text(encoding="utf-8")))
    fp = CONFIG / "coupang_fees.json"
    if fp.exists():
        cfg["coupang_fees"] = json.loads(fp.read_text(encoding="utf-8"))
    return cfg


def fee_rate(category: str, fees: dict, default: float = 0.108) -> float:
    """카테고리명 → 판매수수료율. 부분일치 허용."""
    table = fees.get("categories", {})
    if category in table:
        return table[category]
    for name, rate in table.items():
        if name in category or category in name:
            return rate
    return fees.get("default", default)


def _crawl_coupang(keyword: str, pages: int, limit: int):
    """coupang-naver-crawler를 재사용해 검색결과를 가져온다. 실패 시 예외."""
    import sys
    crawler_path = Path(__file__).resolve().parent.parent.parent / "coupang-naver-crawler"
    if str(crawler_path) not in sys.path:
        sys.path.insert(0, str(crawler_path))
    from crawler import coupang
    from crawler.common import FetchOptions
    return coupang.search(keyword, pages=pages, opts=FetchOptions(engine="stealthy"), limit=limit)


def evaluate(
    keyword: str,
    *,
    sourcing: BundleSourcing,
    category: str = "언더웨어",
    pages: int = 1,
    limit: int = 40,
    config: dict | None = None,
    competition_items: list[dict] | None = None,
    monthly_units: int | None = None,
) -> dict:
    """키워드 하나를 종합 평가한다.

    competition_items를 주면 크롤링을 건너뛰고 그 결과로 분석(오프라인/테스트용).
    """
    cfg = config or load_config()
    floor = cfg.get("margin_floor", 0.10)

    # 1) 경쟁강도
    if competition_items is None:
        try:
            competition_items = _crawl_coupang(keyword, pages, limit)
        except Exception as exc:  # noqa: BLE001
            log.warning("[%s] 쿠팡 크롤링 실패: %s", keyword, str(exc)[:120])
            competition_items = []
    comp = competition.analyze(competition_items)

    # 2) 검색량 (키 없으면 None)
    stats = naver_ads.keyword_stats(keyword)
    total_searches = stats["total"] if stats else None

    # 3) 마진 — 경쟁사 '중앙값 시세'로 팔 때 진짜 마진이 남는지
    sale_ref = comp.get("price_median") or comp.get("price_min")
    fees = cfg.get("coupang_fees", {})
    cost = CoupangCost(
        commission_rate=fee_rate(category, fees),
        outbound_shipping=cfg.get("defaults", {}).get("outbound_shipping", 0),
        packaging=cfg.get("defaults", {}).get("packaging", 200),
        return_rate=cfg.get("defaults", {}).get("return_rate", 0.02),
        vat_mode=cfg.get("defaults", {}).get("vat_mode", "none"),
    )
    margin_res = compute(sale_ref, sourcing, cost, monthly_units) if sale_ref else None
    margin_rate = margin_res["마진율"] if margin_res else None
    m_verdict = verdict(margin_res, floor) if margin_res else ("판정불가", "경쟁시세 없음")

    # 4) 기회 점수
    demand = score.demand_score(total_searches)
    opp = score.opportunity(
        demand=demand, competition=comp, margin_rate=margin_rate, weights=cfg.get("weights"),
    )

    return {
        "keyword": keyword,
        "category": category,
        "search": stats,
        "competition": comp,
        "sale_ref": sale_ref,
        "landed_unit_cost": round(sourcing.landed_unit_cost),
        "margin": margin_res,
        "margin_verdict": {"판정": m_verdict[0], "사유": m_verdict[1]},
        "opportunity": opp,
        "grade": score.grade(opp["score"]),
    }


def rank(results: list[dict]) -> list[dict]:
    """기회 점수 내림차순 정렬."""
    return sorted(results, key=lambda r: r["opportunity"]["score"], reverse=True)


def format_report(results: list[dict]) -> str:
    """랭킹 결과 → 사람이 읽는 표."""
    ranked = rank(results)
    lines = ["# 🛒 쿠팡 소싱 기회 리포트", ""]
    lines.append("| 순위 | 키워드 | 점수 | 등급 | 검색량 | 경쟁(리뷰중앙/광고%) | 시세 | 개당원가 | 마진 | 판정 |")
    lines.append("|---:|---|---:|---|---:|---|---:|---:|---:|---|")
    for i, r in enumerate(ranked, 1):
        c = r["competition"]
        s = r["search"]
        m = r["margin"]
        sv = f"{s['total']:,}" if s else "—"
        comp_txt = (f"{c['review_median']:,}/{c['ad_ratio']*100:.0f}%"
                    if not c.get("empty") else "차단/0")
        sale = f"{r['sale_ref']:,}" if r["sale_ref"] else "—"
        mr = f"{m['마진율']*100:.0f}%" if m and m["마진율"] is not None else "—"
        lines.append(
            f"| {i} | {r['keyword']} | {r['opportunity']['score']} | {r['grade']} | {sv} | "
            f"{comp_txt} | {sale} | {r['landed_unit_cost']:,} | {mr} | {r['margin_verdict']['판정']} |"
        )
    lines.append("")
    lines.append("> 점수↑ = 검색량 높고·경쟁(리뷰/광고/로켓) 낮고·마진 남는 순. "
                 "검색량 '—'는 네이버 검색광고 API 키 미설정.")
    return "\n".join(lines)

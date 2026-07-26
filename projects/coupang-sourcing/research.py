#!/usr/bin/env python3
"""쿠팡 소싱을 위한 실시간 시장조사 CLI (네이버 데이터랩 쇼핑인사이트).

이 샌드박스에서도 **지금 바로 실행되는** 시장조사 도구다.
쿠팡·네이버쇼핑 HTML은 봇 차단(403/418)으로 막히지만, 데이터랩 쇼핑인사이트는
공개 조회 기능이라 키 없이 응답한다.

명령:
  cat      — 카테고리 트리 탐색 (cid 찾기)
      python research.py cat                 # 대분류
      python research.py cat --cid 50000004  # 하위

  find     — 이름으로 카테고리 검색
      python research.py find --name 조명

  top      — 카테고리 인기검색어 TOP N
      python research.py top --cid 50001119 --pages 5
      python research.py top --cid 50001119 --filter 태양광,센서

  trend    — 카테고리/키워드 계절 트렌드 (막대그래프)
      python research.py trend --cid 50001119
      python research.py trend --cid 50001119 --keyword 태양광정원등

  scan     — ★소싱 스캔: 카테고리 인기검색어를 훑어 계절·순위를 한 표로
      python research.py scan --cid 50001119 --pages 5 --top 15
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta

from sourcing import datalab as dl


def _default_range(months: int = 12) -> tuple[str, str]:
    end = date.today().replace(day=1) - timedelta(days=1)
    start = (end.replace(day=1) - timedelta(days=30 * months)).replace(day=1)
    return start.isoformat(), end.isoformat()


def _bar(v: float, mx: float, width: int = 30) -> str:
    if not mx:
        return ""
    return "█" * max(0, int(v / mx * width))


def cmd_cat(a) -> int:
    rows = dl.categories(a.cid)
    if not rows:
        print("하위 카테고리가 없습니다(leaf이거나 조회 실패).", file=sys.stderr)
        return 1
    for c in rows:
        print(f"  {c['cid']:<12} {c['name']}")
    return 0


def cmd_find(a) -> int:
    print(f"'{a.name}' 검색 중… (트리 탐색은 시간이 걸립니다)", file=sys.stderr)
    rows = dl.find_category(a.name, max_depth=a.depth)
    if not rows:
        print("일치하는 카테고리가 없습니다.", file=sys.stderr)
        return 1
    for c in rows:
        print(f"  {c['cid']:<12} {c['path']}")
    return 0


def cmd_top(a) -> int:
    start, end = (a.start, a.end) if a.start and a.end else _default_range(1)
    rows = dl.keyword_rank_pages(a.cid, start, end, pages=a.pages, count=20,
                                 device=a.device, gender=a.gender, age=a.age)
    if not rows:
        print("결과 없음(cid·기간을 확인하세요).", file=sys.stderr)
        return 1
    if a.filter:
        keys = [k.strip() for k in a.filter.split(",") if k.strip()]
        rows = [r for r in rows if any(k in r["keyword"] for k in keys)]
        print(f"[{start} ~ {end}] '{a.filter}' 포함 {len(rows)}건")
    else:
        print(f"[{start} ~ {end}] 인기검색어 {len(rows)}건")
    for r in rows:
        print(f"  {r['rank']:>3}. {r['keyword']}")
    if a.json:
        print(json.dumps(rows, ensure_ascii=False))
    return 0


def cmd_trend(a) -> int:
    start, end = (a.start, a.end) if a.start and a.end else _default_range(12)
    if a.keyword:
        series = dl.keyword_trend(a.cid, a.keyword, start, end, a.unit)
        title = f"'{a.keyword}' (cid={a.cid})"
    else:
        series = dl.category_trend(a.cid, start, end, a.unit)
        title = f"카테고리 {a.cid}"
    if not series:
        print("트렌드 데이터 없음.", file=sys.stderr)
        return 1
    vals = [(p["period"][:7], p["value"]) for p in series
            if isinstance(p.get("value"), (int, float))]
    mx = max(v for _, v in vals) if vals else 0
    lo = min(vals, key=lambda x: x[1]) if vals else None
    hi = max(vals, key=lambda x: x[1]) if vals else None
    print(f"\n{title}  [{start} ~ {end}]")
    for per, v in vals:
        print(f"  {per}  {v:>6.1f}  {_bar(v, mx)}")
    if lo and hi:
        swing = (hi[1] - lo[1]) / hi[1] * 100 if hi[1] else 0
        print(f"\n  최고 {hi[0]} {hi[1]:.1f} · 최저 {lo[0]} {lo[1]:.1f} · 진폭 {swing:.0f}%")
        print(f"  → {'계절성 큼(비수기 대비 필요)' if swing >= 40 else '계절성 완만(연중 안정)'}")
    return 0


def cmd_scan(a) -> int:
    """카테고리 인기검색어를 훑고, 상위 키워드의 계절 진폭까지 붙여 한 표로."""
    kstart, kend = _default_range(1)
    tstart, tend = _default_range(12)
    rows = dl.keyword_rank_pages(a.cid, kstart, kend, pages=a.pages, count=20)
    if not rows:
        print("인기검색어 조회 실패.", file=sys.stderr)
        return 1
    if a.filter:
        keys = [k.strip() for k in a.filter.split(",") if k.strip()]
        rows = [r for r in rows if any(k in r["keyword"] for k in keys)]
    rows = rows[: a.top]

    print(f"\n소싱 스캔 · cid={a.cid} · 인기검색어 {kstart}~{kend} · 트렌드 {tstart}~{tend}")
    print(f"{'순위':>4} {'키워드':<18} {'성수기':<9}{'비수기':<9}{'진폭':>6}  판정")
    print("-" * 66)
    for r in rows:
        tr = dl.keyword_trend(a.cid, r["keyword"], tstart, tend, "month")
        vals = [(p["period"][:7], p["value"]) for p in tr
                if isinstance(p.get("value"), (int, float))]
        if not vals:
            print(f"{r['rank']:>4} {r['keyword']:<18} {'—':<9}{'—':<9}{'—':>6}  (트렌드 없음)")
            continue
        hi = max(vals, key=lambda x: x[1])
        lo = min(vals, key=lambda x: x[1])
        swing = (hi[1] - lo[1]) / hi[1] * 100 if hi[1] else 0
        verdict = "연중형 ✅" if swing < 35 else ("계절형 ⚠️" if swing < 55 else "강계절 ❗")
        print(f"{r['rank']:>4} {r['keyword']:<18} {hi[0]:<9}{lo[0]:<9}{swing:>5.0f}%  {verdict}")
        dl.polite()
    print("\n연중형 = 비수기에도 수요가 유지 → 캐시플로 안정. 강계절 = 비수기 대비 상품 필요.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="research.py", description="네이버 데이터랩 기반 시장조사 (키 불필요)",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("cat", help="카테고리 트리")
    p.add_argument("--cid", default=0)

    p = sub.add_parser("find", help="이름으로 카테고리 검색")
    p.add_argument("--name", required=True)
    p.add_argument("--depth", type=int, default=2)

    for name, helptext in (("top", "인기검색어 TOP N"), ("scan", "소싱 스캔(인기+계절)")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--cid", required=True)
        p.add_argument("--pages", type=int, default=5)
        p.add_argument("--filter", help="쉼표로 구분한 포함 키워드 (예: 태양광,센서)")
        p.add_argument("--start"); p.add_argument("--end")
        if name == "top":
            p.add_argument("--device", default=""); p.add_argument("--gender", default="")
            p.add_argument("--age", default=""); p.add_argument("--json", action="store_true")
        else:
            p.add_argument("--top", type=int, default=15)

    p = sub.add_parser("trend", help="계절 트렌드")
    p.add_argument("--cid", required=True)
    p.add_argument("--keyword")
    p.add_argument("--unit", default="month", choices=["date", "week", "month"])
    p.add_argument("--start"); p.add_argument("--end")

    a = ap.parse_args(argv)
    return {"cat": cmd_cat, "find": cmd_find, "top": cmd_top,
            "trend": cmd_trend, "scan": cmd_scan}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())

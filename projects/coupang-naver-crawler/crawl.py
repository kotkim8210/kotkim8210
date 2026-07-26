#!/usr/bin/env python3
"""쿠팡·네이버쇼핑 통합 크롤러 CLI.

예시:
    # 쿠팡 검색 2페이지 → JSON 저장
    python crawl.py coupang --query "무선 이어폰" --pages 2 --out out/coupang.json

    # 네이버쇼핑 검색, 상위 20개만 CSV로
    python crawl.py naver --query "무선 이어폰" --limit 20 --out out/naver.csv

    # 쿠팡 상품 상세
    python crawl.py coupang --product-id 1234567890

    # 차단이 심하면 브라우저 창을 띄워(headed) 직접 확인 + 프록시 사용
    python crawl.py coupang -q "커피" --no-headless --proxy http://user:pass@host:port
"""
from __future__ import annotations

import argparse
import json
import sys

from crawler import common, coupang, naver_shopping
from crawler.common import FetchOptions


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("-q", "--query", help="검색어")
    p.add_argument("-p", "--pages", type=int, default=1, help="가져올 페이지 수 (기본 1)")
    p.add_argument("--limit", type=int, default=None, help="최대 상품 수")
    p.add_argument("-o", "--out", help="저장 경로 (.json 또는 .csv). 생략 시 표준출력")
    p.add_argument("--engine", choices=["stealthy", "dynamic", "http"], default="stealthy",
                   help="페처 엔진 (기본 stealthy = 반봇 우회)")
    p.add_argument("--no-headless", action="store_true", help="브라우저 창을 띄워 실행")
    p.add_argument("--no-solve", action="store_true", help="Cloudflare 자동해결 끄기")
    p.add_argument("--no-adaptive", action="store_true", help="적응형 선택자 끄기")
    p.add_argument("--proxy", help="프록시 URL (예: http://user:pass@host:port)")
    p.add_argument("--timeout", type=int, default=30, help="타임아웃(초, 기본 30)")
    p.add_argument("--wait", type=int, default=0, help="로드 후 추가 대기(ms)")
    p.add_argument("--fast", action="store_true", help="이미지·불필요 리소스 차단(속도↑)")
    p.add_argument("--no-delay", action="store_true", help="페이지 간 예의 지연 끄기")
    p.add_argument("-v", "--verbose", action="store_true", help="디버그 로그")


def _opts_from_args(a: argparse.Namespace) -> FetchOptions:
    return FetchOptions(
        engine=a.engine,
        headless=not a.no_headless,
        solve_cloudflare=not a.no_solve,
        adaptive=not a.no_adaptive,
        proxy=a.proxy,
        timeout=a.timeout * 1000,
        wait=a.wait,
        disable_resources=a.fast,
        block_images=a.fast,
    )


def _output(rows, args) -> None:
    if args.out:
        path = common.save(rows, args.out)
        print(f"✅ {len(rows)}건 저장 → {path}", file=sys.stderr)
    else:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"총 {len(rows)}건", file=sys.stderr)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="crawl.py",
        description="쿠팡·네이버쇼핑 크롤러 (Scrapling 기반, 적응형·반봇 우회)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="site", required=True)

    pc = sub.add_parser("coupang", help="쿠팡 크롤링")
    _add_common_args(pc)
    pc.add_argument("--product-id", help="상품 상세 조회(검색 대신 ID 하나)")

    pn = sub.add_parser("naver", help="네이버쇼핑 크롤링")
    _add_common_args(pn)

    args = parser.parse_args(argv)
    common.setup_logging(args.verbose)
    opts = _opts_from_args(args)
    delay = not args.no_delay

    if args.site == "coupang":
        if getattr(args, "product_id", None):
            _output([coupang.product(args.product_id, opts)], args)
            return 0
        if not args.query:
            pc.error("검색어(--query) 또는 --product-id 중 하나가 필요합니다.")
        rows = coupang.search(args.query, args.pages, opts, args.limit, delay)
        _output(rows, args)
        return 0

    if args.site == "naver":
        if not args.query:
            pn.error("검색어(--query)가 필요합니다.")
        rows = naver_shopping.search(args.query, args.pages, opts, args.limit, delay)
        _output(rows, args)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

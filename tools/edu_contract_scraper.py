#!/usr/bin/env python3
"""시·도교육청 계약체결 현황 수집기 (비로그인 공개 데이터).

S2B(학교장터)는 사업자 공동인증서 로그인이 필요하지만, 각 시·도교육청이
K-에듀파인과 연계해 공개하는 '계약체결 현황'은 로그인 없이 조회된다.
계약명·계약금액·계약방법에 더해 **계약대상자(낙찰업체)명**까지 확인할 수 있어,
실제 낙찰 단가와 시장 집중도를 실측할 수 있다.

지원 지역(2026-08-15 실측):
    incheon  인천 — 목록에 낙찰업체·목적물구분 포함. 용역만 필터 가능. **권장**
    gyeongnam 경남 — 목록엔 없고 상세 페이지에서 낙찰업체 조회(--detail)

미지원: 서울(기관별 월간 파일 공개라 계약명 검색 없음), 경기(검색 파라미터 무시됨)

사용 예:
    python3 gne_contract_scraper.py 청소 --region incheon --service-only
    python3 gne_contract_scraper.py 저수조 --region gyeongnam --detail -o x.csv

주의: 공개된 행정정보이지만 서버에 부담을 주지 않도록 요청 간 지연을 둔다.
"""
import argparse
import csv
import html
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

REGIONS = {
    "incheon": {
        "list": "https://www.ice.go.kr/contract/ir/selectCntrInfoList.do",
        "base_params": {"mi": "11307"},
        "name_param": "schCntrNm",
        "page_param": "currPage",
        "service_param": ("schCntrPodiv", "3"),  # 1=공사 2=물품 3=용역
        # 목록 열: 번호 연도 기관 방법 목적물 계약명 일자 금액 계약상대자
        "cols": {"기관": 2, "방법": 3, "구분": 4, "계약명": 5, "일자": 6, "금액": 7, "업체": 8},
        "min_cells": 9,
        "detail": None,  # 목록에 이미 낙찰업체가 있어 상세 조회 불필요
    },
    "gyeongnam": {
        "list": "https://www.gne.go.kr/user/cntr/BD_cntrInfoList.do",
        "base_params": {"q_rowPerPage": "100"},
        "name_param": "q_cntrNm",
        "page_param": "q_currPage",
        "service_param": None,
        # 목록 열: 글번호 기관 방법 계약명 일자 금액
        "cols": {"기관": 1, "방법": 2, "계약명": 3, "일자": 4, "금액": 5},
        "min_cells": 6,
        "detail": "https://www.gne.go.kr/user/cntr/BD_cntrInfoDetail.do?cmSeqNo=",
        "seq_pattern": r"opCntrView\('(\d+)'\)",
    },
}


def build_opener():
    """사내 프록시/CA 번들 환경에서도 동작하는 opener."""
    ca = "/root/.ccr/ca-bundle.crt"
    ctx = ssl.create_default_context(cafile=ca if os.path.exists(ca) else None)
    handlers = [urllib.request.HTTPSHandler(context=ctx)]
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"https": proxy, "http": proxy}))
    op = urllib.request.build_opener(*handlers)
    op.addheaders = [("User-Agent", "Mozilla/5.0")]
    return op


def clean(fragment):
    """HTML 조각에서 표시 텍스트만 뽑아 공백을 정규화한다."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def parse_list(page_html, cfg):
    """목록 페이지의 <tr>에서 계약 레코드를 추출한다."""
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, re.S):
        cells = [c for c in (clean(x) for x in
                             re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)) if c]
        if len(cells) < cfg["min_cells"] or not cells[0].isdigit():
            continue
        rec = {"no": cells[0]}
        for key, idx in cfg["cols"].items():
            rec[key] = cells[idx]
        rec["금액"] = int(rec["금액"].replace(",", ""))
        if cfg.get("seq_pattern"):
            m = re.search(cfg["seq_pattern"], row)
            rec["seq"] = m.group(1) if m else ""
        out.append(rec)
    return out


def fetch_contractor(opener, detail_url, seq):
    """상세 페이지에서 계약대상자(낙찰업체)명을 읽는다 (경남 전용)."""
    body = opener.open(f"{detail_url}{seq}", timeout=60).read().decode("utf-8", "ignore")
    cells = [c for c in (clean(x) for x in
                         re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", body, re.S)) if c]
    if "계약대상자명" in cells:
        return cells[cells.index("계약대상자명") + 1]
    return ""


def main():
    ap = argparse.ArgumentParser(description="시·도교육청 계약체결 현황 수집")
    ap.add_argument("keyword", help="계약명 검색어 (예: 청소, 저수조, 방역)")
    ap.add_argument("--region", default="incheon", choices=sorted(REGIONS),
                    help="대상 교육청 (기본: incheon)")
    ap.add_argument("--service-only", action="store_true",
                    help="용역만 수집 (인천만 지원 — 물품·공사 제외)")
    ap.add_argument("--pages", type=int, default=200, help="최대 페이지 수")
    ap.add_argument("--detail", action="store_true",
                    help="상세 페이지로 낙찰업체 조회 (경남 전용, 건당 1요청)")
    ap.add_argument("-o", "--out", default=None, help="출력 파일 (.json 또는 .csv)")
    args = ap.parse_args()

    cfg = REGIONS[args.region]
    opener = build_opener()

    params = dict(cfg["base_params"])
    params[cfg["name_param"]] = args.keyword
    if args.service_only:
        if not cfg["service_param"]:
            sys.exit(f"--service-only는 {args.region}에서 지원되지 않습니다 (인천만 가능)")
        key, val = cfg["service_param"]
        params[key] = val

    records, seen = [], set()
    for page in range(1, args.pages + 1):
        params[cfg["page_param"]] = str(page)
        url = f"{cfg['list']}?{urllib.parse.urlencode(params)}"
        try:
            body = opener.open(url, timeout=90).read().decode("utf-8", "ignore")
        except Exception as exc:
            print(f"[중단] p{page}: {exc}", file=sys.stderr)
            break
        rows = [r for r in parse_list(body, cfg) if r["no"] not in seen]
        if not rows:
            break
        seen.update(r["no"] for r in rows)
        records += rows
        if page % 10 == 0:
            print(f"  p{page}: 누적 {len(records)}건", file=sys.stderr)
        time.sleep(0.15)

    if args.detail:
        if not cfg["detail"]:
            print(f"[알림] {args.region}은 목록에 이미 낙찰업체가 있어 --detail이 불필요합니다.",
                  file=sys.stderr)
        else:
            for i, rec in enumerate(records):
                try:
                    rec["업체"] = fetch_contractor(opener, cfg["detail"], rec["seq"])
                except Exception:
                    rec["업체"] = ""
                if i % 25 == 0:
                    print(f"  상세 {i}/{len(records)}", file=sys.stderr)
                time.sleep(0.1)

    out = args.out or f"{args.region}_{args.keyword}.json"
    if out.endswith(".csv"):
        cols = [c for c in ["일자", "기관", "방법", "구분", "계약명", "금액", "업체"]
                if any(c in r for r in records)]
        with open(out, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
    else:
        json.dump(records, open(out, "w"), ensure_ascii=False, indent=1)

    total = sum(r["금액"] for r in records)
    print(f"\n{len(records)}건 / 합계 {total/1e8:.2f}억원 → {out}")


if __name__ == "__main__":
    main()

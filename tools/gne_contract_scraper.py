#!/usr/bin/env python3
"""경상남도교육청 계약체결 현황 수집기 (비로그인 공개 데이터).

S2B(학교장터)는 사업자 공동인증서 로그인이 필요하지만, 각 시·도교육청이
K-에듀파인과 연계해 공개하는 '계약체결 현황'은 로그인 없이 조회된다.
계약명·계약금액·계약방법에 더해 상세 페이지에서 **계약대상자(낙찰업체)명**까지
확인할 수 있어, 실제 낙찰 단가와 시장 집중도를 실측할 수 있다.

사용 예:
    python3 gne_contract_scraper.py 청소                    # 목록만
    python3 gne_contract_scraper.py 저수조 --detail         # 낙찰업체까지
    python3 gne_contract_scraper.py 방역 --pages 20 -o x.json

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

BASE = "https://www.gne.go.kr/user/cntr"
LIST = f"{BASE}/BD_cntrInfoList.do"
DETAIL = f"{BASE}/BD_cntrInfoDetail.do"
ROWS_MAX = 100  # 서버가 허용하는 rowPerPage 상한 (500은 빈 응답)


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


def parse_list(page_html):
    """목록 페이지의 <tr>에서 계약 레코드와 상세조회 키(cmSeqNo)를 추출한다."""
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, re.S):
        seq = re.search(r"opCntrView\('(\d+)'\)", row)
        cells = [c for c in (clean(x) for x in
                             re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)) if c]
        if not seq or len(cells) < 6:
            continue
        out.append({
            "seq": seq.group(1),
            "기관": cells[1],
            "방법": cells[2],
            "계약명": cells[3],
            "일자": cells[4],
            "금액": int(cells[5].replace(",", "")),
        })
    return out


def fetch_contractor(opener, seq):
    """상세 페이지에서 계약대상자(낙찰업체)명을 읽는다."""
    body = opener.open(f"{DETAIL}?cmSeqNo={seq}", timeout=60).read().decode("utf-8", "ignore")
    cells = [c for c in (clean(x) for x in
                         re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", body, re.S)) if c]
    if "계약대상자명" in cells:
        return cells[cells.index("계약대상자명") + 1]
    return ""


def main():
    ap = argparse.ArgumentParser(description="경남교육청 계약체결 현황 수집")
    ap.add_argument("keyword", help="계약명 검색어 (예: 청소, 저수조, 방역)")
    ap.add_argument("--pages", type=int, default=100, help="최대 페이지 수 (100건/페이지)")
    ap.add_argument("--detail", action="store_true", help="낙찰업체명까지 조회 (건당 1요청, 느림)")
    ap.add_argument("-o", "--out", default=None, help="출력 파일 (.json 또는 .csv)")
    args = ap.parse_args()

    opener = build_opener()
    kw = urllib.parse.quote(args.keyword)
    records, seen = [], set()

    for page in range(1, args.pages + 1):
        url = f"{LIST}?q_cntrNm={kw}&q_rowPerPage={ROWS_MAX}&q_currPage={page}"
        try:
            body = opener.open(url, timeout=90).read().decode("utf-8", "ignore")
        except Exception as exc:
            print(f"[중단] p{page}: {exc}", file=sys.stderr)
            break
        rows = [r for r in parse_list(body) if r["seq"] not in seen]
        if not rows:
            break
        seen.update(r["seq"] for r in rows)
        records += rows
        print(f"  p{page}: 누적 {len(records)}건", file=sys.stderr)
        time.sleep(0.2)

    if args.detail:
        for i, rec in enumerate(records):
            try:
                rec["업체"] = fetch_contractor(opener, rec["seq"])
            except Exception:
                rec["업체"] = ""
            if i % 25 == 0:
                print(f"  상세 {i}/{len(records)}", file=sys.stderr)
            time.sleep(0.1)

    out = args.out or f"gne_{args.keyword}.json"
    if out.endswith(".csv"):
        cols = ["일자", "기관", "방법", "계약명", "금액"] + (["업체"] if args.detail else [])
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

#!/usr/bin/env python3
"""나라장터 개찰결과 수집기 — 경쟁강도(참가업체 수)를 재기 위한 도구.

## 왜 필요한가
교육청 계약공개 데이터에는 **낙찰자만** 있고 응찰자가 없다. 그 데이터로 HHI를 내면
"업체 17곳, 경쟁적이나 독점 아님" 같은 결론이 나오는데, 같은 시장의 실제 입찰
참가업체는 411~1,010개사였다. 낙찰 HHI가 낮은 것은 경쟁이 약해서가 아니라
매번 다른 업체가 이기기 때문이다. 경쟁강도는 응찰자 수로만 잴 수 있고,
그 데이터는 나라장터 개찰결과에만 있다.

## 서비스키 발급 (약 10분, 자동승인)
1. https://www.data.go.kr 회원가입
2. "조달청_나라장터 낙찰정보서비스"(데이터 15129397) 활용신청 — 심의 자동승인
3. 마이페이지에서 일반 인증키(Decoding) 복사

    export G2B_SERVICE_KEY='발급받은키'
    python3 tools/g2b_opening_results.py --from 20250101 --to 20251231 --keyword 청소

주의: 인코딩된 키가 아니라 **Decoding 키**를 넣어야 한다(스크립트가 알아서 인코딩한다).
"""
import argparse
import collections
import json
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://apis.data.go.kr/1230000/as/ScsbidInfoService"
# 키 없이 오퍼레이션 유효성만 검증해둔 목록 (대조군은 거부됨)
OPS = {
    "용역": "getOpengResultListInfoServc",
    "용역-조달청": "getOpengResultListInfoServcPPSSrch",
    "공사": "getOpengResultListInfoCnstwkPPSSrch",
    "물품": "getScsbidListSttusThngPPSSrch",
    "용역낙찰": "getScsbidListSttusServcPPSSrch",
}


def build_opener():
    ca = "/root/.ccr/ca-bundle.crt"
    ctx = ssl.create_default_context(cafile=ca if os.path.exists(ca) else None)
    handlers = [urllib.request.HTTPSHandler(context=ctx)]
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"https": proxy, "http": proxy}))
    op = urllib.request.build_opener(*handlers)
    op.addheaders = [("User-Agent", "Mozilla/5.0")]
    return op


def fetch(opener, operation, key, page, rows, extra):
    """한 페이지를 받아 (items, totalCount)를 돌려준다."""
    params = {"serviceKey": key, "pageNo": page, "numOfRows": rows, "type": "json"}
    params.update(extra)
    url = f"{BASE}/{operation}?{urllib.parse.urlencode(params)}"
    raw = opener.open(url, timeout=60).read().decode("utf-8", "ignore")
    if "SERVICE_KEY_IS_NULL" in raw or "SERVICE_ACCESS_DENIED" in raw:
        sys.exit("서비스키가 없거나 거부됐다. Decoding 키를 G2B_SERVICE_KEY에 넣었는지 확인할 것.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(f"JSON 파싱 실패. 응답 앞부분:\n{raw[:400]}")
    body = data.get("response", {}).get("body", {})
    items = body.get("items", [])
    if isinstance(items, dict):          # 단건이면 dict로 오는 경우가 있다
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    return items, int(body.get("totalCount", 0) or 0)


def pick(record, *candidates):
    """응답 필드명이 문서마다 달라 후보를 순서대로 찾는다."""
    for c in candidates:
        if c in record and record[c] not in (None, ""):
            return record[c]
    return ""


def main():
    ap = argparse.ArgumentParser(description="나라장터 개찰결과 수집 — 참가업체 수 집계")
    ap.add_argument("--from", dest="d_from", required=True, help="개찰일 시작 YYYYMMDD")
    ap.add_argument("--to", dest="d_to", required=True, help="개찰일 종료 YYYYMMDD")
    ap.add_argument("--keyword", default="", help="공고명 필터 (수집 후 로컬 필터)")
    ap.add_argument("--kind", default="용역", choices=sorted(OPS), help="업무 구분")
    ap.add_argument("--pages", type=int, default=50, help="최대 페이지")
    ap.add_argument("--rows", type=int, default=100, help="페이지당 건수")
    ap.add_argument("-o", "--out", default="g2b_opening.json")
    args = ap.parse_args()

    key = os.environ.get("G2B_SERVICE_KEY")
    if not key:
        sys.exit("G2B_SERVICE_KEY 환경변수가 없다. 파일 상단의 발급 절차를 볼 것.")

    opener = build_opener()
    operation = OPS[args.kind]
    extra = {"inqryDiv": "1", "inqryBgnDt": args.d_from + "0000", "inqryEndDt": args.d_to + "2359"}

    records, total = [], None
    for page in range(1, args.pages + 1):
        try:
            items, total = fetch(opener, operation, key, page, args.rows, extra)
        except Exception as exc:
            print(f"[중단] p{page}: {exc}", file=sys.stderr)
            break
        if not items:
            break
        records += items
        print(f"  p{page}: 누적 {len(records)}건 / 전체 {total}", file=sys.stderr)
        if len(records) >= total:
            break
        time.sleep(0.2)

    if args.keyword:
        records = [r for r in records
                   if args.keyword in str(pick(r, "bidNtceNm", "bidPbancNm", "ntceNm"))]
        print(f"  '{args.keyword}' 필터 후 {len(records)}건", file=sys.stderr)

    json.dump(records, open(args.out, "w"), ensure_ascii=False, indent=1)

    # 공고별 응찰자 수 = 개찰결과 행 수
    by_notice = collections.defaultdict(list)
    for r in records:
        no = pick(r, "bidNtceNo", "bidPbancNo")
        by_notice[no].append(r)

    print(f"\n수집 {len(records)}건 / 공고 {len(by_notice)}건 → {args.out}")
    if not by_notice:
        return
    counts = sorted((len(v) for v in by_notice.values()), reverse=True)
    mid = counts[len(counts) // 2]
    print(f"공고당 응찰자 수: 최대 {counts[0]} · 중앙 {mid} · 최소 {counts[-1]}")
    print("\n[응찰자 많은 공고 상위 10]")
    for no, rows in sorted(by_notice.items(), key=lambda x: -len(x[1]))[:10]:
        nm = str(pick(rows[0], "bidNtceNm", "bidPbancNm", "ntceNm"))[:44]
        inst = str(pick(rows[0], "ntceInsttNm", "dminsttNm"))[:16]
        print(f"  {len(rows):>5}개사 | {inst:<16} | {nm}")
    print("\n※ 이 '응찰자 수'가 경쟁강도의 진짜 지표다. 낙찰자 기반 HHI는 쓰지 말 것.")


if __name__ == "__main__":
    main()

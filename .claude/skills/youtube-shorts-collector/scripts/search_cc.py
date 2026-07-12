#!/usr/bin/env python3
"""
search_cc.py — YouTube Creative Commons 필터 검색

해시태그/키워드로 YouTube를 검색하되, Creative Commons 라이선스 필터를 적용한다.
flat 추출로 후보 목록만 빠르게 가져온다 (조회수 포함 시 정렬용).

경로 2단 구성:
  1차) yt-dlp의 검색결과 페이지 추출 (기존 방식)
  2차) 1차가 0개/실패면 YouTube 내부 검색 API(innertube)를 직접 호출해
       신형 쇼츠 결과 구조(shortsLockupViewModel)까지 파싱하는 폴백.
       (유튜브가 쇼츠 검색결과를 신형 뷰모델로 바꾸면서 yt-dlp flat 추출이
        빈손이 되는 환경이 있다 — 이 폴백이 그 경우를 구제한다.
        폴백의 조회수는 "5.1M" 같은 근사값이므로 정렬용으로만 쓰고,
        정확한 값은 collect.py의 상세 수집(fetch_meta)이 다시 확인한다.)

주의: CC 필터(sp=EgIwAQ%3D%3D)는 YouTube가 라이선스로 1차 필터링해주지만,
      영상 안의 배경음악 등 임베디드 저작권까지 보장하지는 않는다 (collect.py 경고 참고).

사용:
    python search_cc.py "#piano #shorts" --max 30
    python search_cc.py "#painting" --max 20 --json
"""
import re
import sys
import json
import time
import argparse
import urllib.request
from urllib.parse import quote

try:
    from yt_dlp import YoutubeDL
except ImportError:
    sys.exit("[ERROR] yt-dlp가 설치되지 않았습니다. `pip install -U yt-dlp` 실행 후 다시 시도하세요. (setup.md 참고)")

# YouTube 검색 필터 sp 파라미터 = Creative Commons
SP_CREATIVE_COMMONS = "EgIwAQ%3D%3D"
# innertube API용 (URL 인코딩 안 된 원형)
PARAMS_CREATIVE_COMMONS = "EgIwAQ=="

INNERTUBE_URL = "https://www.youtube.com/youtubei/v1/search?prettyPrint=false"
INNERTUBE_CONTEXT = {
    "client": {"clientName": "WEB", "clientVersion": "2.20250620.00.00", "hl": "en", "gl": "US"}
}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def _search_ytdlp(query: str, max_results: int):
    """1차: yt-dlp로 CC 필터 검색결과 페이지 flat 추출."""
    search_url = (
        f"https://www.youtube.com/results?search_query={quote(query)}"
        f"&sp={SP_CREATIVE_COMMONS}"
    )
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,      # 개별 영상 상세는 안 가져옴 (빠름)
        "skip_download": True,
        "playlistend": max_results,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(search_url, download=False)

    entries = (info or {}).get("entries", []) or []
    results = []
    for e in entries:
        if not e or not e.get("id"):
            continue
        vid = e.get("id")
        results.append({
            "id": vid,
            "title": e.get("title"),
            "url": f"https://www.youtube.com/watch?v={vid}",
            "view_count": e.get("view_count"),   # flat에선 None일 수 있음
            "channel": e.get("channel") or e.get("uploader"),
            "duration": e.get("duration"),
        })
    return results


def _parse_views_text(text: str):
    """'5.1 million views' / '1.2M views' / '1,234 views' / 'No views' → int 또는 None."""
    if not text:
        return None
    t = text.lower().replace(",", "").strip()
    if t.startswith("no views"):
        return 0
    m = re.search(r"([\d.]+)\s*(billion|million|thousand|b|m|k)?\s*views?", t)
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2) or ""
    mult = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "billion": 1e9}.get(unit, 1)
    return int(num * mult)


def _walk_collect(obj, out):
    """innertube 응답에서 videoRenderer + shortsLockupViewModel을 재귀 수집."""
    if isinstance(obj, dict):
        if "videoRenderer" in obj and isinstance(obj["videoRenderer"], dict):
            vr = obj["videoRenderer"]
            vid = vr.get("videoId")
            if vid:
                title = "".join(r.get("text", "") for r in (vr.get("title", {}).get("runs") or []))
                views = _parse_views_text((vr.get("viewCountText") or {}).get("simpleText", ""))
                ch = ""
                for r in (vr.get("ownerText", {}).get("runs") or []):
                    ch += r.get("text", "")
                out.append({"id": vid, "title": title or None, "view_count": views,
                            "channel": ch or None, "duration": None})
        if "shortsLockupViewModel" in obj and isinstance(obj["shortsLockupViewModel"], dict):
            lv = obj["shortsLockupViewModel"]
            vid = (((lv.get("onTap") or {}).get("innertubeCommand") or {})
                   .get("reelWatchEndpoint") or {}).get("videoId")
            if not vid:
                eid = lv.get("entityId", "")
                vid = eid.rsplit("-", 1)[-1] if eid.startswith("shorts-shelf-item-") else None
            if vid:
                acc = lv.get("accessibilityText") or ""
                # "제목, 5.1 million views - play Short" 형태에서 제목/조회수 분리
                m = re.match(r"^(?P<title>.*),\s*(?P<views>[^,]*?views?)\s*-\s*play Short$", acc, re.I)
                title = m.group("title") if m else (acc or None)
                views = _parse_views_text(m.group("views")) if m else None
                out.append({"id": vid, "title": title, "view_count": views,
                            "channel": None, "duration": None})
        for v in obj.values():
            _walk_collect(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_collect(v, out)


def _find_continuation(obj):
    """다음 페이지 continuation 토큰 탐색."""
    if isinstance(obj, dict):
        token = ((obj.get("continuationItemRenderer") or {})
                 .get("continuationEndpoint") or {}).get("continuationCommand", {}).get("token")
        if token:
            return token
        for v in obj.values():
            t = _find_continuation(v)
            if t:
                return t
    elif isinstance(obj, list):
        for v in obj:
            t = _find_continuation(v)
            if t:
                return t
    return None


def _innertube_call(body: dict):
    req = urllib.request.Request(
        INNERTUBE_URL, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _search_innertube(query: str, max_results: int):
    """2차 폴백: innertube 검색 API 직접 호출 (CC 필터 params 적용).

    유튜브가 간헐적으로 아이템이 1~3개뿐인 빈약한 페이지를 반환하므로
    첫 페이지가 얇으면 재시도하며 고유 결과를 누적한다.
    """
    results, seen = [], set()

    def collect_page(data):
        page = []
        _walk_collect(data, page)
        for it in page:
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            it["url"] = f"https://www.youtube.com/watch?v={it['id']}"
            results.append(it)

    first_body = {"context": INNERTUBE_CONTEXT, "query": query, "params": PARAMS_CREATIVE_COMMONS}
    data = None
    for attempt in range(3):
        try:
            data = _innertube_call(first_body)
            collect_page(data)
        except Exception:
            data = None
        if len(results) >= 5:
            break
        time.sleep(1)

    for _ in range(2):  # continuation 최대 2회
        if data is None or len(results) >= max_results:
            break
        token = _find_continuation(data)
        if not token:
            break
        try:
            data = _innertube_call({"context": INNERTUBE_CONTEXT, "continuation": token})
            collect_page(data)
        except Exception:
            break
    return results[:max_results]


def search(query: str, max_results: int = 30):
    """CC 필터를 적용한 YouTube 검색. flat 결과 리스트 반환.

    yt-dlp 경로가 플레이크로 1~5개짜리 빈약한 페이지를 반환하기도 하므로,
    결과가 적으면 innertube 폴백 결과를 병합해 후보 풀을 보강한다.
    """
    try:
        results = _search_ytdlp(query, max_results)
    except Exception:
        results = []
    if len(results) < min(8, max_results):
        seen = {r["id"] for r in results}
        for it in _search_innertube(query, max_results):
            if it["id"] not in seen:
                seen.add(it["id"])
                results.append(it)
    return results[:max_results]


def main():
    ap = argparse.ArgumentParser(description="YouTube CC 필터 검색")
    ap.add_argument("query", help="검색어 (해시태그 권장, 예: '#piano #shorts')")
    ap.add_argument("--max", type=int, default=30, help="최대 후보 수 (기본 30)")
    ap.add_argument("--json", action="store_true", help="JSON으로 출력")
    args = ap.parse_args()

    results = search(args.query, args.max)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"[검색어] {args.query}  (CC 필터 적용)")
        print(f"[후보 {len(results)}개]\n")
        for i, r in enumerate(results, 1):
            vc = r["view_count"]
            vc_str = f"{vc:,}회" if isinstance(vc, int) else "조회수 미상(flat)"
            print(f"{i:2d}. {r['title']}")
            print(f"    {r['url']}  | {vc_str} | {r['channel']}")
    return results


if __name__ == "__main__":
    main()

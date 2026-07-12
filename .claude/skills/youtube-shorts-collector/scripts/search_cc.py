#!/usr/bin/env python3
"""
search_cc.py — YouTube Creative Commons 필터 검색

해시태그/키워드로 YouTube를 검색하되, Creative Commons 라이선스 필터를 적용한다.
flat 추출로 후보 목록만 빠르게 가져온다 (조회수 포함 시 정렬용).

주의: CC 필터(sp=EgIwAQ%3D%3D)는 YouTube가 라이선스로 1차 필터링해주지만,
      영상 안의 배경음악 등 임베디드 저작권까지 보장하지는 않는다 (collect.py 경고 참고).

사용:
    python search_cc.py "#piano #shorts" --max 30
    python search_cc.py "#painting" --max 20 --json
"""
import sys
import json
import argparse
from urllib.parse import quote

try:
    from yt_dlp import YoutubeDL
except ImportError:
    sys.exit("[ERROR] yt-dlp가 설치되지 않았습니다. `pip install -U yt-dlp` 실행 후 다시 시도하세요. (setup.md 참고)")

# YouTube 검색 필터 sp 파라미터 = Creative Commons
SP_CREATIVE_COMMONS = "EgIwAQ%3D%3D"


def search(query: str, max_results: int = 30):
    """CC 필터를 적용한 YouTube 검색. flat 결과 리스트 반환."""
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

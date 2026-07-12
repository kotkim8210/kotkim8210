#!/usr/bin/env python3
"""
fetch_comments.py — 인기 댓글 수집 (좋아요순 재정렬)

큐레이션 스킬 Stage 3(댓글 기반 주제 결정)의 핵심 재료.
yt-dlp의 'top' 정렬로 가져온 뒤, like_count로 한 번 더 확실히 정렬한다.

사용:
    python fetch_comments.py "URL" --top 15
    python fetch_comments.py "URL" --top 20 --json
"""
import sys
import json
import argparse

try:
    from yt_dlp import YoutubeDL
except ImportError:
    sys.exit("[ERROR] yt-dlp 미설치. `pip install -U yt-dlp` 실행. (setup.md 참고)")


def fetch_comments(url: str, max_fetch: int = 100):
    """댓글을 최대 max_fetch개 가져와 좋아요순 정렬."""
    # 유튜브 봇 체크 우회 폴백은 fetch_meta의 것을 공용으로 사용
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    from fetch_meta import extract_info_botcheck_fallback

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "getcomments": True,
        "extractor_args": {
            "youtube": {
                "comment_sort": ["top"],       # 인기순
                "max_comments": [str(max_fetch)],
            }
        },
    }
    info = extract_info_botcheck_fallback(url, opts)

    comments = info.get("comments") or []
    # 좋아요순 재정렬 (top 정렬이 완벽하지 않을 수 있어 확실히 다시 정렬)
    comments.sort(key=lambda c: (c.get("like_count") or 0), reverse=True)

    cleaned = []
    for c in comments:
        cleaned.append({
            "author": c.get("author"),
            "text": (c.get("text") or "").strip(),
            "like_count": c.get("like_count") or 0,
            "reply_count": c.get("reply_count") or 0,
            "is_favorited": c.get("is_favorited"),   # 크리에이터 하트
        })
    return cleaned


def main():
    ap = argparse.ArgumentParser(description="인기 댓글 수집")
    ap.add_argument("url", help="영상 URL")
    ap.add_argument("--top", type=int, default=15, help="상위 몇 개 출력 (기본 15)")
    ap.add_argument("--fetch", type=int, default=100, help="긁어올 최대 댓글 수 (기본 100)")
    ap.add_argument("--json", action="store_true", help="JSON 출력")
    args = ap.parse_args()

    comments = fetch_comments(args.url, args.fetch)
    top = comments[: args.top]

    if args.json:
        print(json.dumps(top, ensure_ascii=False, indent=2))
    else:
        print(f"[인기 댓글 TOP {len(top)}]  (긁어온 총 {len(comments)}개 중)\n")
        for i, c in enumerate(top, 1):
            heart = " ❤️" if c["is_favorited"] else ""
            print(f"{i:2d}. 👍 {c['like_count']:,}  💬 {c['reply_count']}{heart}")
            print(f"    {c['text'][:200]}")
            print()
    return top


if __name__ == "__main__":
    main()

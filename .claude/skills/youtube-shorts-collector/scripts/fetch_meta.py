#!/usr/bin/env python3
"""
fetch_meta.py — 영상 메타데이터 수집 (조회수·구독자·라이선스 등)

한 영상 URL에서 큐레이션 판단에 필요한 사실 데이터를 가져온다.
V/S 비율(조회수÷구독자)과 CC 여부 판정의 근거가 된다.

사용:
    python fetch_meta.py "https://www.youtube.com/watch?v=XXXX"
    python fetch_meta.py "https://youtube.com/shorts/XXXX" --json
"""
import sys
import json
import argparse

try:
    from yt_dlp import YoutubeDL
except ImportError:
    sys.exit("[ERROR] yt-dlp 미설치. `pip install -U yt-dlp` 실행. (setup.md 참고)")


def is_creative_commons(info: dict) -> bool:
    """라이선스 필드에 Creative Commons 표기가 있는지."""
    lic = (info.get("license") or "").lower()
    return "creative commons" in lic or "cc by" in lic


_botcheck_seen = False  # 한 번 걸리면 이후 호출은 바로 tv 클라이언트로 (헛시도 절약)


def extract_info_botcheck_fallback(url: str, opts: dict) -> dict:
    """기본 클라이언트로 추출하되, 유튜브 봇 체크("Sign in to confirm")에 걸리면
    tv 클라이언트로 재시도한다. tv는 봇 체크를 안 걸지만 다운로드 포맷을 안 주므로
    ignore_no_formats_error가 필요하다 (메타데이터·댓글 수집에는 포맷이 필요 없음).
    데이터센터 IP에서 자주 걸리는 차단의 우회 경로이며, 메타데이터는 동일하게 나온다."""
    global _botcheck_seen
    if not _botcheck_seen:
        try:
            with YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            if "sign in to confirm" not in str(e).lower():
                raise
            _botcheck_seen = True
    fallback = dict(opts)
    fallback["ignore_no_formats_error"] = True
    ea = dict(fallback.get("extractor_args") or {})
    ea["youtube"] = {**(ea.get("youtube") or {}), "player_client": ["tv"]}
    fallback["extractor_args"] = ea
    with YoutubeDL(fallback) as ydl:
        return ydl.extract_info(url, download=False)


def fetch_meta(url: str) -> dict:
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    info = extract_info_botcheck_fallback(url, opts)

    view = info.get("view_count")
    subs = info.get("channel_follower_count")
    # V/S 비율 = 조회수 ÷ 구독자 (구독자 대비 얼마나 터졌나)
    vs_ratio = None
    if isinstance(view, int) and isinstance(subs, int) and subs > 0:
        vs_ratio = round(view / subs, 1)

    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "url": info.get("webpage_url"),
        "channel": info.get("channel") or info.get("uploader"),
        "channel_url": info.get("channel_url") or info.get("uploader_url"),
        "view_count": view,
        "like_count": info.get("like_count"),
        "channel_follower_count": subs,
        "vs_ratio": vs_ratio,
        "duration_sec": info.get("duration"),
        "upload_date": info.get("upload_date"),   # YYYYMMDD
        "license": info.get("license"),
        "is_creative_commons": is_creative_commons(info),
        "categories": info.get("categories"),
        "tags": (info.get("tags") or [])[:20],
        "description": info.get("description"),
    }


def main():
    ap = argparse.ArgumentParser(description="영상 메타데이터 수집")
    ap.add_argument("url", help="영상 URL")
    ap.add_argument("--json", action="store_true", help="JSON 출력")
    args = ap.parse_args()

    m = fetch_meta(args.url)

    if args.json:
        print(json.dumps(m, ensure_ascii=False, indent=2))
    else:
        dur = m["duration_sec"]
        dur_str = f"{dur//60}:{dur%60:02d}" if isinstance(dur, int) else "미상"
        print(f"제목      : {m['title']}")
        print(f"채널      : {m['channel']}  (구독자 {m['channel_follower_count']:,})"
              if isinstance(m['channel_follower_count'], int)
              else f"채널      : {m['channel']}  (구독자 미상)")
        print(f"조회수    : {m['view_count']:,}" if isinstance(m['view_count'], int) else "조회수    : 미상")
        print(f"V/S 비율  : {m['vs_ratio']}  (조회수÷구독자)")
        print(f"길이      : {dur_str}")
        print(f"업로드일  : {m['upload_date']}")
        print(f"라이선스  : {m['license']}")
        print(f"CC 여부   : {'✅ Creative Commons' if m['is_creative_commons'] else '❌ 아님 (제외 대상)'}")
    return m


if __name__ == "__main__":
    main()

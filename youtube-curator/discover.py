#!/usr/bin/env python3
"""CC 라이선스 트렌드 영상 발굴 (yt-dlp 기반, YouTube API 키 불필요).

저작권 안전 원칙:
  - YouTube 검색의 'Creative Commons' 필터로 1차 선별
  - 각 후보를 풀 추출해 license == 'Creative Commons Attribution license (reuse allowed)'
    인지 **이중 확인**한 것만 통과시킨다. (재업로드 권리 확보)
  - '떡상' 점수 = 하루 평균 조회수(조회수 / 업로드 후 경과일).
"""
from __future__ import annotations

import datetime as _dt
from urllib.parse import quote

from yt_dlp import YoutubeDL

# yt-dlp 가 정규화하는 CC 라이선스 문자열
CC_LICENSE = "Creative Commons Attribution license (reuse allowed)"
# YouTube 검색 결과를 'Creative Commons' 라이선스로 거르는 필터 파라미터(sp)
CC_SEARCH_SP = "EgIwAQ%3D%3D"


# 데이터센터 IP(샌드박스·CI)에서 YouTube 'bot 확인' 벽을 우회하는 플레이어 클라이언트.
# (android 클라이언트는 쿠키 없이도 라이선스·메타 추출이 됨)
YT_EXTRACTOR_ARGS = {"youtube": {"player_client": ["android"]}}


def _opts(insecure: bool, flat: bool, limit: int = 0, cookies: "str | None" = None) -> dict:
    o = {"quiet": True, "no_warnings": True, "skip_download": True,
         "nocheckcertificate": insecure, "extractor_args": YT_EXTRACTOR_ARGS}
    if flat:
        o["extract_flat"] = "in_playlist"
    if limit:
        o["playlistend"] = limit
    if cookies:
        o["cookiefile"] = cookies   # 선택: 봇 벽이 강해지면 YouTube 쿠키로 보강
    return o


def search_cc(query: str, limit: int = 20, *, insecure: bool = False) -> list[dict]:
    """CC 필터를 건 검색으로 후보(id·제목·조회수)를 가져온다."""
    url = f"https://www.youtube.com/results?search_query={quote(query)}&sp={CC_SEARCH_SP}"
    with YoutubeDL(_opts(insecure, flat=True, limit=limit)) as y:
        info = y.extract_info(url, download=False)
    out = []
    for e in info.get("entries") or []:
        if e.get("id"):
            out.append({"id": e["id"], "title": e.get("title", ""),
                        "view_count": e.get("view_count") or 0})
    return out


def details(video_id: str, *, insecure: bool = False) -> dict:
    """한 영상의 권리·통계 메타데이터를 풀 추출한다."""
    with YoutubeDL(_opts(insecure, flat=False)) as y:
        i = y.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    return {
        "id": i["id"],
        "title": i.get("title", ""),
        "channel": i.get("uploader", "") or i.get("channel", ""),
        "channel_url": i.get("uploader_url") or i.get("channel_url", ""),
        "url": i.get("webpage_url", f"https://youtu.be/{i['id']}"),
        "license": i.get("license"),
        "duration": i.get("duration") or 0,
        "views": i.get("view_count") or 0,
        "likes": i.get("like_count") or 0,
        "upload_date": i.get("upload_date"),
    }


def _days_since(yyyymmdd: "str | None") -> int:
    if not yyyymmdd:
        return 9999
    try:
        d = _dt.datetime.strptime(yyyymmdd, "%Y%m%d").date()
    except ValueError:
        return 9999
    return max(1, (_dt.date.today() - d).days)


def viral_score(d: dict) -> float:
    """떡상 점수 = 하루 평균 조회수."""
    return d["views"] / _days_since(d.get("upload_date"))


def is_creative_commons(d: dict) -> bool:
    return d.get("license") == CC_LICENSE


def discover(
    query: str, *, want: int = 3, pool: int = 25,
    min_dur: int = 60, max_dur: int = 1800, max_age_days: int = 365,
    insecure: bool = False,
) -> list[dict]:
    """카테고리(검색어)에서 CC·길이·신선도 조건을 통과한 떡상 영상을 점수순으로 반환."""
    candidates = search_cc(query, limit=pool, insecure=insecure)
    candidates.sort(key=lambda c: c.get("view_count") or 0, reverse=True)

    picked: list[dict] = []
    for c in candidates:
        try:
            d = details(c["id"], insecure=insecure)
        except Exception:
            continue
        if not is_creative_commons(d):          # ⚖️ 권리 게이트(이중 확인) — 통과 못하면 버림
            continue
        if not (min_dur <= d["duration"] <= max_dur):
            continue                            # 너무 짧거나(이미 숏츠) 너무 긴 건 제외
        days = _days_since(d.get("upload_date"))
        if days > max_age_days:
            continue                            # 오래된 영상 제외(트렌드만)
        d["days"] = days
        d["viral_score"] = round(viral_score(d))
        picked.append(d)
        if len(picked) >= want * 3:             # 점수 정렬을 위해 넉넉히 모은다
            break

    picked.sort(key=lambda x: x["viral_score"], reverse=True)
    return picked[:want]


def attribution_text(d: dict) -> str:
    """CC 라이선스 의무 — 출처 표기 문구."""
    return (f"출처: '{d['title']}' — {d['channel']} ({d['url']})\n"
            f"라이선스: Creative Commons Attribution (CC BY) — 원작자 표기 후 재사용")


if __name__ == "__main__":
    import argparse
    import json

    p = argparse.ArgumentParser(description="CC 트렌드 영상 발굴")
    p.add_argument("query", help="카테고리 검색어 (예: 'world cup 2026 highlights')")
    p.add_argument("--want", type=int, default=3)
    p.add_argument("--min-dur", type=int, default=60)
    p.add_argument("--max-dur", type=int, default=1800)
    p.add_argument("--insecure", action="store_true", help="TLS 검증 끄기(로컬 프록시 환경 전용)")
    a = p.parse_args()

    res = discover(a.query, want=a.want, min_dur=a.min_dur, max_dur=a.max_dur, insecure=a.insecure)
    for d in res:
        print(f"[떡상 {d['viral_score']:>7}/일] {d['duration']}s  {d['views']:,}views  "
              f"{d['days']}일전  {d['title'][:55]}")
        print(f"           {d['url']}  | {d['channel']}")
    print(json.dumps(res, ensure_ascii=False, indent=2)[:0])  # (조용히)

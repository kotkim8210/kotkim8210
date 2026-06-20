#!/usr/bin/env python3
"""채널 분석기 — 랭킹 + 성장 예측 (danbi 스타일, YouTube API 키 불필요).

수집(매일): 채널별 구독자 + 최근 영상 성과를 yt-dlp 로 뽑아 스냅샷을 history 에 누적.
분석: 누적 스냅샷으로 ① 구독자 랭킹 ② 일 성장(델타) ③ 7/30일 구독자 예측
      ④ 최근 영상의 일평균 조회수(떡상 속도)로 주간 조회수 예측.
(스냅샷이 쌓일수록 예측이 정확해진다 — danbi 가 2025년부터 모은 것과 같은 원리.)
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from yt_dlp import YoutubeDL

import discover as D  # YT_EXTRACTOR_ARGS, details(), viral_score() 재사용

HERE = Path(__file__).resolve().parent


def _flat(url: str, *, limit: int, insecure: bool, cookies: "str | None") -> dict:
    opts = {"quiet": True, "no_warnings": True, "skip_download": True,
            "nocheckcertificate": insecure, "extract_flat": "in_playlist",
            "playlistend": limit, "extractor_args": D.YT_EXTRACTOR_ARGS}
    if cookies:
        opts["cookiefile"] = cookies
    with YoutubeDL(opts) as y:
        return y.extract_info(url, download=False)


def channel_snapshot(ch: dict, *, insecure: bool, cookies: "str | None") -> "dict | None":
    """한 채널의 현재 스냅샷(구독자 + 최근 영상 성과)."""
    url = ch["url"].rstrip("/")
    if not url.endswith(("/videos", "/featured")):
        url += "/videos"
    info = _flat(url, limit=3, insecure=insecure, cookies=cookies)
    subs = info.get("channel_follower_count")
    if subs is None:
        return None
    recent = [e for e in (info.get("entries") or []) if e.get("id")][:3]

    latest = None
    if recent:
        try:
            d = D.details(recent[0]["id"], insecure=insecure)
            latest = {"title": d["title"], "views": d["views"],
                      "velocity": round(D.viral_score(d)), "url": d["url"]}
        except Exception:
            latest = None
    return {
        "date": _dt.date.today().isoformat(),
        "channel_id": info.get("channel_id") or ch.get("name"),
        "name": info.get("channel") or ch.get("name"),
        "url": ch["url"], "category": ch.get("category", ""),
        "subs": subs, "latest_video": latest,
    }


def collect(channels: list[dict], history_path: Path, *, insecure: bool, cookies: "str | None") -> int:
    """모든 채널 스냅샷을 찍어 history(JSONL)에 추가. 성공 개수 반환."""
    n = 0
    with history_path.open("a", encoding="utf-8") as f:
        for ch in channels:
            try:
                snap = channel_snapshot(ch, insecure=insecure, cookies=cookies)
            except Exception:
                snap = None
            if snap:
                f.write(json.dumps(snap, ensure_ascii=False) + "\n")
                n += 1
    return n


def _predict(snaps: list[dict]) -> dict:
    """한 채널의 스냅샷 시계열 → 성장·예측."""
    snaps = sorted(snaps, key=lambda s: s["date"])
    latest = snaps[-1]
    out = {
        "name": latest["name"], "url": latest["url"], "category": latest["category"],
        "subs": latest["subs"], "snapshots": len(snaps),
        "latest_video": latest.get("latest_video"),
        "daily_growth": None, "growth_pct": None,
        "pred_subs_7d": None, "pred_subs_30d": None, "status": "데이터 축적 중",
    }
    # 두 날짜 이상이면 일 성장률로 예측
    first = snaps[0]
    days = (_dt.date.fromisoformat(latest["date"]) - _dt.date.fromisoformat(first["date"])).days
    if days >= 1 and first["subs"]:
        daily = (latest["subs"] - first["subs"]) / days
        out["daily_growth"] = round(daily)
        out["growth_pct"] = round(daily / latest["subs"] * 100, 3)
        out["pred_subs_7d"] = round(latest["subs"] + daily * 7)
        out["pred_subs_30d"] = round(latest["subs"] + daily * 30)
        out["status"] = "예측 가능"
    # 최근 영상 주간 조회수 예측(일평균 × 7, 상한)
    lv = latest.get("latest_video")
    if lv and lv.get("velocity"):
        out["video_pred_7d"] = round(lv["views"] + lv["velocity"] * 7)
    return out


def build(history_path: Path, out_path: Path) -> list[dict]:
    """history → 채널별 예측 + 구독자 랭킹 → channels.json."""
    if not history_path.exists():
        out_path.write_text("[]", encoding="utf-8")
        return []
    by_ch: dict[str, list[dict]] = {}
    for line in history_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        s = json.loads(line)
        by_ch.setdefault(s["channel_id"], []).append(s)

    rows = [_predict(v) for v in by_ch.values()]
    rows.sort(key=lambda r: r["subs"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    # 급상승 랭크(일 성장순) 별도 표기
    rising = sorted([r for r in rows if r["daily_growth"]], key=lambda r: r["daily_growth"], reverse=True)
    for i, r in enumerate(rising, 1):
        r["rising_rank"] = i
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows


def load_channels(path: Path) -> list[dict]:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))["channels"]


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="채널 랭킹·예측 수집/분석")
    p.add_argument("--config", type=Path, default=HERE / "channels.yaml")
    p.add_argument("--output", type=Path, default=HERE / "output")
    p.add_argument("--collect", action="store_true", help="스냅샷 1회 수집(history 누적)")
    p.add_argument("--insecure", action="store_true")
    p.add_argument("--cookies", default=None)
    a = p.parse_args()

    a.output.mkdir(parents=True, exist_ok=True)
    history = a.output / "channels_history.jsonl"
    chjson = a.output / "channels.json"

    if a.collect:
        chans = load_channels(a.config)
        auto = a.output / "auto_channels.json"          # 디스커버리에서 자동 추가된 채널
        if auto.exists():
            seen = {c["url"].rstrip("/") for c in chans}
            for c in json.loads(auto.read_text(encoding="utf-8")):
                if c.get("url") and c["url"].rstrip("/") not in seen:
                    chans.append(c)
                    seen.add(c["url"].rstrip("/"))
        print(f"▶ {len(chans)}개 채널 스냅샷 수집(수동+자동)...")
        n = collect(chans, history, insecure=a.insecure, cookies=a.cookies)
        print(f"  수집 완료: {n}/{len(chans)}")

    rows = build(history, chjson)
    print(f"▶ 채널 분석 갱신: {len(rows)}개 → {chjson}")
    for r in rows[:10]:
        g = f"+{r['daily_growth']:,}/일" if r["daily_growth"] else r["status"]
        print(f"  #{r['rank']:<2} {r['name'][:24]:24} 구독 {r['subs']:>12,}  {g}")


if __name__ == "__main__":
    main()

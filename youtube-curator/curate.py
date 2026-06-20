#!/usr/bin/env python3
"""YouTube 큐레이터 — 카테고리별 CC 떡상 영상을 찾아 롱폼→숏츠로 자동 편집.

파이프라인: 발굴(discover) → 권리 게이트(CC만) → 다운로드 → 하이라이트 선택(LLM/휴리스틱)
            → 롱폼→숏츠 편집(video-editor, 9:16) → 매니페스트 + 출처(CC) 기록

저작권: CC 라이선스 영상만 편집·재유통(출처표기 의무 포함). 그 외는 발굴(분석)만.
실행: 카테고리 설정은 categories.yaml. 자동화는 .github/workflows/curate.yml(매일 크론).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
EDITOR = REPO / "video-editor" / "edit_videos.py"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "video-editor"))

import discover as D  # noqa: E402


def log(m: str) -> None:
    print(f"  {m}", flush=True)


def step(m: str) -> None:
    print(f"\n▶ {m}", flush=True)


def yt_download(video_id: str, dst: Path, *, insecure: bool, cookies: "str | None") -> Path:
    """CC 영상을 받는다(android 클라이언트로 봇 벽 우회, 720p 이하)."""
    from yt_dlp import YoutubeDL
    opts = {
        "quiet": True, "no_warnings": True, "outtmpl": str(dst.with_suffix(".%(ext)s")),
        "format": "bv*[height<=720]+ba/b[height<=720]/best",
        "merge_output_format": "mp4", "nocheckcertificate": insecure,
        "extractor_args": D.YT_EXTRACTOR_ARGS,
    }
    if cookies:
        opts["cookiefile"] = cookies
    with YoutubeDL(opts) as y:
        y.download([f"https://www.youtube.com/watch?v={video_id}"])
    for ext in (".mp4", ".mkv", ".webm"):
        if dst.with_suffix(ext).exists():
            return dst.with_suffix(ext)
    raise RuntimeError("다운로드 산출물을 찾지 못함")


def pick_highlight(segments: list[dict], target: float) -> tuple[float, float]:
    """숏츠로 쓸 ~target초짜리 '가장 알찬' 연속 구간을 고른다.

    ANTHROPIC_API_KEY 가 있으면 Claude 가 가장 후킹되는 구간을, 없으면
    말이 가장 빽빽한(글자수/초) 슬라이딩 윈도를 휴리스틱으로 고른다.
    """
    if not segments:
        return 0.0, target
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _llm_highlight(segments, target)
        except Exception as e:  # 실패 시 휴리스틱으로 폴백
            log(f"LLM 하이라이트 실패({e}) → 휴리스틱 사용")
    return _dense_window(segments, target)


def _dense_window(segments: list[dict], target: float) -> tuple[float, float]:
    best, best_density = None, -1.0
    for i in range(len(segments)):
        j, chars = i, 0
        while j < len(segments) and segments[j]["end"] - segments[i]["start"] <= target:
            chars += len(segments[j]["text"])
            j += 1
        span = segments[min(j, len(segments) - 1)]["end"] - segments[i]["start"]
        if span <= 0:
            continue
        density = chars / span
        if density > best_density:
            best_density, best = density, (segments[i]["start"], segments[min(j, len(segments) - 1)]["end"])
    return best or (segments[0]["start"], min(segments[-1]["end"], target))


def _llm_highlight(segments: list[dict], target: float) -> tuple[float, float]:
    import anthropic
    numbered = "\n".join(f"{i + 1}: [{s['start']:.0f}s] {s['text']}" for i, s in enumerate(segments))
    prompt = (
        f"다음은 한 영상의 자막입니다. 숏츠(약 {int(target)}초)로 만들 때 **가장 후킹되고 "
        "자체로 완결되는** 연속 구간을 고르세요.\n"
        "⭐ 구간은 반드시 **썸네일/주제와 연관된 가장 끌리는 후킹 문장으로 '시작'** 해야 합니다"
        "(도입 군말·인사로 시작 금지 — 첫 1~2초에 훅).\n"
        "시작 문장번호와 끝 문장번호만 JSON 으로: {\"start\":N,\"end\":M}\n\n" + numbered
    )
    c = anthropic.Anthropic()
    msg = c.messages.create(model=os.environ.get("CURATE_LLM_MODEL", "claude-opus-4-8"),
                            max_tokens=200, messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in msg.content if b.type == "text")
    m = re.search(r'\{[^}]*"start"[^}]*\}', text)
    if not m:
        return _dense_window(segments, target)
    obj = json.loads(m.group(0))
    a = max(1, int(obj["start"])) - 1
    b = min(len(segments), int(obj["end"])) - 1
    return segments[a]["start"], segments[max(a, b)]["end"]


def make_short(category: dict, item: dict, work: Path, out_dir: Path, *, insecure: bool,
               cookies: "str | None") -> dict:
    """한 영상 → 한 숏츠. 결과 메타(매니페스트 항목)를 반환."""
    from edit_videos import transcribe_segments  # video-editor 재사용

    step(f"[{category['name']}] {item['title'][:50]}  (떡상 {item['viral_score']}/일)")
    raw = yt_download(item["id"], work / "raw", insecure=insecure, cookies=cookies)
    log(f"다운로드 완료: {raw.name}")

    lang = category.get("lang", "ko")
    segs, _info = transcribe_segments(raw, model_name=category.get("model", "small"),
                                      language=lang, compute_type="int8",
                                      initial_prompt=category.get("hint", ""))
    target = float(category.get("short_len", 50))
    a, b = pick_highlight(segs, target)
    b = min(b, a + target * 1.4)            # 너무 길어지지 않게 상한
    log(f"하이라이트 구간: {a:.0f}s ~ {b:.0f}s ({b - a:.0f}초)")

    clip = work / "clip.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", f"{a:.2f}", "-to", f"{b:.2f}", "-i", str(raw),
                    "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", str(clip)],
                   check=True)

    # 롱폼→숏츠 편집: 9:16 채움 + 자막 + 무음컷 (메뉴 효과음·짤은 끔)
    in_dir = work / "in"
    in_dir.mkdir(exist_ok=True)
    shutil.copy(clip, in_dir / "clip.mp4")
    slug = re.sub(r"[^\w가-힣]+", "-", item["title"])[:40].strip("-") or item["id"]
    name = f"{category['slug']}_{slug}"
    translate = bool(category.get("translate"))
    cmd = [sys.executable, str(EDITOR), "--input", str(in_dir), "--output", str(out_dir),
           "--name", name, "--width", "1080", "--height", "1920", "--fit", "cover",
           "--margin-v", "120", "--language", lang, "--model", category.get("model", "small"),
           "--no-intro-sound", "--no-transition-sound"]
    if translate:
        cmd += ["--translate-ko"]                       # 외국어 원본 → 한국어 자막(분위기 반영)
        if category.get("llm_model"):
            cmd += ["--llm-model", category["llm_model"]]
    else:
        cmd += ["--initial-prompt", category.get("hint", "")]   # 한국어 원본은 도메인 힌트
    subprocess.run(cmd, check=True)

    short = out_dir / f"{name}.mp4"
    (out_dir / f"{name}.txt").write_text(  # CC 출처표기(설명란용)
        f"{category.get('caption', '')}\n\n{D.attribution_text(item)}\n", encoding="utf-8")
    return {
        "category": category["name"], "slug": category["slug"],
        "short": short.name, "srt": f"{name}.srt", "desc": f"{name}.txt",
        "source": {"title": item["title"], "channel": item["channel"], "url": item["url"],
                   "channel_url": item.get("channel_url", ""),
                   "license": item["license"], "views": item["views"], "viral_score": item["viral_score"]},
        "highlight": [round(a, 1), round(b, 1)], "created": _dt.datetime.now().isoformat(timespec="seconds"),
    }


def load_categories(path: Path) -> list[dict]:
    import yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["categories"]


def record_channel(out_dir: Path, entry: dict) -> None:
    """숏츠로 쓴 CC 원본의 채널을 자동 추적 목록에 추가(채널 분석 랭킹/예측용)."""
    s = entry.get("source", {})
    url = s.get("channel_url")
    if not url:
        return
    path = out_dir / "auto_channels.json"
    chans = json.loads(path.read_text()) if path.exists() else []
    if any(c.get("url") == url for c in chans):
        return
    chans.append({"name": s.get("channel", ""), "url": url, "category": entry.get("category", "")})
    path.write_text(json.dumps(chans, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description="CC 떡상 영상 → 숏츠 자동 큐레이터")
    p.add_argument("--config", type=Path, default=HERE / "categories.yaml")
    p.add_argument("--only", default="", help="이 slug 카테고리만 실행")
    p.add_argument("--per-category", type=int, default=1, help="카테고리당 만들 숏츠 수")
    p.add_argument("--output", type=Path, default=HERE / "output")
    p.add_argument("--cookies", default=os.environ.get("YT_COOKIES_FILE") or None,
                   help="YouTube 쿠키 파일(봇 벽 100%% 우회). CI는 secret 으로 주입")
    p.add_argument("--insecure", action="store_true", help="TLS 검증 끄기(로컬 프록시 전용)")
    args = p.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} 가 필요합니다.")

    cats = [c for c in load_categories(args.config) if not args.only or c["slug"] == args.only]
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []

    for cat in cats:
        step(f"카테고리: {cat['name']}  (검색='{cat['query']}')")
        found = D.discover(cat["query"], want=args.per_category,
                           min_dur=cat.get("min_dur", 90), max_dur=cat.get("max_dur", 1800),
                           insecure=args.insecure)
        if not found:
            log("CC 조건을 통과한 떡상 영상이 없습니다(다른 검색어/조건 시도).")
            continue
        for item in found:
            if any(m["source"]["url"] == item["url"] for m in manifest):
                log(f"이미 처리함, 건너뜀: {item['title'][:40]}")
                continue
            work = Path(tempfile.mkdtemp(prefix="curate_", dir=str(args.output)))
            try:
                entry = make_short(cat, item, work, args.output, insecure=args.insecure, cookies=args.cookies)
                manifest.insert(0, entry)
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                record_channel(args.output, entry)   # 원본 채널을 자동 추적 목록에 추가
                log(f"✅ 숏츠 완성: {entry['short']}")
            except Exception as e:
                log(f"✖ 실패({item['id']}): {e}")
            finally:
                shutil.rmtree(work, ignore_errors=True)

    step("완료")
    log(f"매니페스트: {manifest_path}  (총 {len(manifest)}개 숏츠)")


if __name__ == "__main__":
    main()

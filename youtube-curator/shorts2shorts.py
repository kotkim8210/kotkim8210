#!/usr/bin/env python3
"""쇼츠 투 쇼츠 — 틱톡/샤오홍수 떡상 소재 → 한국 쇼츠 (카테고리 공식 + 속도 최우선).

흐름: 입력(워치리스트 최신 + --urls) → 빠른 다운로드 → 전사(작은 모델) →
      LLM 편집기(카테고리 '공식'대로 구간/순서/번역 결정) → 후킹 앞배치 재정렬+조립
      → 9:16 + 한국어 자막 → 매니페스트 + 출처표기.

⚖️ 비-CC 소재(틱톡/샤오홍수)는 재업로드 시 권리 위험 → 출처표기 + 충분한 변형(번역·재편집·공식) 전제로 사용.
속도: 쇼츠는 짧아 작은 whisper 로 빠름. 트렌드는 늦으면 끝 — workflow_dispatch 로 링크 즉시 처리 가능.
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
ASSETS = REPO / "assets"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "video-editor"))

import discover as D            # noqa: E402  (YT_EXTRACTOR_ARGS, _flat 패턴)
from edit_videos import (       # noqa: E402  편집 엔진 재사용
    transcribe_segments, write_ass, run as ff_run,
)


def log(m: str) -> None:
    print(f"  {m}", flush=True)


def step(m: str) -> None:
    print(f"\n▶ {m}", flush=True)


# ── 소스 ─────────────────────────────────────────────────────────────────────
def latest_from_source(url: str, *, insecure: bool, cookies: "str | None", n: int = 1) -> list[str]:
    """크리에이터/소스 URL 에서 최신 영상 URL 들을 가져온다(워치리스트)."""
    from yt_dlp import YoutubeDL
    opts = {"quiet": True, "no_warnings": True, "skip_download": True,
            "extract_flat": "in_playlist", "playlistend": n, "nocheckcertificate": insecure}
    if cookies:
        opts["cookiefile"] = cookies
    with YoutubeDL(opts) as y:
        info = y.extract_info(url, download=False)
    out = []
    for e in (info.get("entries") or [])[:n]:
        u = e.get("url") or e.get("webpage_url") or (f"https://youtu.be/{e['id']}" if e.get("id") else None)
        if u:
            out.append(u)
    return out


def download(url: str, dst: Path, *, insecure: bool, cookies: "str | None") -> tuple[Path, dict]:
    """소스 쇼츠를 받고 메타(제목·업로더·URL)를 반환."""
    from yt_dlp import YoutubeDL
    opts = {"quiet": True, "no_warnings": True, "outtmpl": str(dst.with_suffix(".%(ext)s")),
            "format": "bv*[height<=1280]+ba/b/best", "merge_output_format": "mp4",
            "nocheckcertificate": insecure}
    if cookies:
        opts["cookiefile"] = cookies
    with YoutubeDL(opts) as y:
        info = y.extract_info(url, download=True)
    for ext in (".mp4", ".mkv", ".webm"):
        if dst.with_suffix(ext).exists():
            meta = {"title": info.get("title", ""), "uploader": info.get("uploader", ""),
                    "url": info.get("webpage_url", url), "duration": info.get("duration") or 0}
            return dst.with_suffix(ext), meta
    raise RuntimeError("다운로드 산출물 없음")


# ── LLM 편집기(카테고리 공식) ────────────────────────────────────────────────
def _tuning_block(category: dict) -> str:
    """카테고리의 정밀 튜닝 노브(있는 것만)를 LLM 프롬프트용 지시문으로 만든다."""
    knobs = [
        ("hook_sec", "훅(맨 앞 끌리는 구간) 목표 길이 ≈ {v}초 — 그 안에 가장 강한 한 방을 넣어라."),
        ("target_cuts", "목표 컷 수 ≈ {v}개 — 그만큼 빠른 호흡으로 쓸 문장을 추려라."),
        ("caption_chars", "한 컷 자막은 {v}자 이내로 짧게."),
        ("pace", "호흡: {v}"),
        ("retention", "체류율 전술: {v}"),
        ("cta", "마무리: {v}"),
    ]
    lines = [t.format(v=category[k]) for k, t in knobs if category.get(k) not in (None, "", 0)]
    return ("\n[정밀 튜닝 파라미터 — 반드시 반영]\n" + "\n".join(f"- {x}" for x in lines)) if lines else ""


def llm_edit_plan(segments: list[dict], *, category: dict, model: str) -> dict:
    """카테고리 '공식'대로 (쓸 구간·순서 + 분위기 한국어 번역 + 후킹 제목)을 정한다.

    키가 없으면 원본 순서 유지 + 원문 자막(폴백). order 는 0-기반 인덱스 리스트.
    """
    ident = {"order": list(range(len(segments))),
             "captions": [s["text"] for s in segments], "title": category.get("name", "")}
    if not segments:
        return {"order": [], "captions": [], "title": category.get("name", "")}
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log("LLM 편집기 건너뜀(키 없음) → 원본 순서·원문 자막")
        return ident
    try:
        import anthropic
        numbered = "\n".join(f"{i + 1}: {s['text']}" for i, s in enumerate(segments))
        prompt = (
            f"너는 한국 쇼츠 편집 디렉터다. 카테고리: {category['name']}.\n"
            f"이 카테고리의 떡상 공식:\n{category.get('formula', '')}\n"
            f"{_tuning_block(category)}\n"
            f"아래는 원본({category.get('lang', 'zh')}) 쇼츠의 자막(번호:문장)이다. 위 공식과 튜닝 "
            "파라미터에 맞게 한국 쇼츠로 재편집하라:\n"
            "① 쓸 문장과 '순서'를 정한다(후킹을 공식대로 맨 앞에, 군더더기 제거, 목표 컷 수에 맞춰).\n"
            "② 각 문장을 공식의 자막 톤·글자수에 맞는 한국어로 번역(직역 금지, 짧고 입에 붙게).\n"
            "오직 JSON 으로: {\"order\":[원본번호...], \"captions\":[\"번역문...\"(order와 같은 순서·길이)], "
            "\"title\":\"후킹 제목\"}\n\n" + numbered
        )
        c = anthropic.Anthropic()
        msg = c.messages.create(model=model, max_tokens=2000,
                                messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in msg.content if b.type == "text")
        obj = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
        order = [int(n) - 1 for n in obj["order"] if 1 <= int(n) <= len(segments)]
        caps = obj.get("captions", [])
        if not order:
            return ident
        captions = [caps[k] if k < len(caps) and isinstance(caps[k], str) else segments[order[k]]["text"]
                    for k in range(len(order))]
        return {"order": order, "captions": captions, "title": obj.get("title", category.get("name", ""))}
    except Exception as e:
        log(f"LLM 편집기 실패({e}) → 원본 순서·원문 자막")
        return ident


# ── 재정렬 조립(후킹 앞배치) + 9:16 ──────────────────────────────────────────
def reorder_and_caption(src: Path, segments: list[dict], plan: dict, dst: Path, *,
                        width: int, height: int, fps: int) -> None:
    """plan.order 순서대로 구간을 잘라 9:16 으로 이어붙이고, 번역 자막을 태운다."""
    order, caps = plan["order"], plan["captions"]
    # 1) ffmpeg concat 필터로 순서대로 재정렬 + 9:16 cover (한 패스)
    fc, parts = [], []
    for k, i in enumerate(order):
        a, b = segments[i]["start"], segments[i]["end"]
        fc.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS,fps={fps},"
                  f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                  f"crop={width}:{height},setsar=1,format=yuv420p[v{k}]")
        fc.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS,aresample=48000[a{k}]")
        parts.append(f"[v{k}][a{k}]")
    fc.append("".join(parts) + f"concat=n={len(order)}:v=1:a=1[v][a]")
    reordered = dst.parent / "reordered.mp4"
    ff_run(["ffmpeg", "-hide_banner", "-y", "-i", str(src), "-filter_complex", ";".join(fc),
            "-map", "[v]", "-map", "[a]", "-r", str(fps),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(reordered)])

    # 2) 새 타임라인 큐(번역 자막) 만들기
    cues, t = [], 0.0
    for k, i in enumerate(order):
        dur = max(0.1, segments[i]["end"] - segments[i]["start"])
        cues.append({"start": t, "end": t + dur, "text": caps[k]})
        t += dur

    # 3) 자막 ASS 만들고 태우기(GmarketSans, 중하단)
    ass = dst.parent / "subs.ass"
    write_ass(cues, ass, width=width, height=height, font="Gmarket Sans TTF",
              font_size=round(height * 0.072), orange_hex="#FF8C42", highlight=[],
              margin_v=round(height * 0.30), pop=True)
    ff_run(["ffmpeg", "-hide_banner", "-y", "-i", str(reordered.resolve()),
            "-vf", f"ass={ass.resolve().as_posix()}:fontsdir={ASSETS.resolve().as_posix()}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "copy", "-movflags", "+faststart", str(dst.resolve())])


def make_short(cat: dict, url: str, work: Path, out_dir: Path, *, insecure: bool, cookies: "str | None") -> dict:
    step(f"[{cat['name']}] {url}")
    raw, meta = download(url, work / "raw", insecure=insecure, cookies=cookies)
    log(f"다운로드: {meta['title'][:40]} ({meta['duration']}s)")
    segs, _ = transcribe_segments(raw, model_name=cat.get("model", "small"),
                                  language=cat.get("lang", "zh"), compute_type="int8")
    plan = llm_edit_plan(segs, category=cat, model=os.environ.get("CURATE_LLM_MODEL", "claude-opus-4-8"))
    slug = re.sub(r"[^\w가-힣]+", "-", meta["title"])[:32].strip("-") or "clip"
    name = f"{cat['slug']}_{slug}"
    short = out_dir / f"{name}.mp4"
    if plan["order"]:
        reorder_and_caption(raw, segs, plan, short, width=1080, height=1920, fps=30)
    else:   # 음성 없음 → 9:16 변환만
        ff_run(["ffmpeg", "-hide_banner", "-y", "-i", str(raw),
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", str(short)])
    (out_dir / f"{name}.txt").write_text(
        f"{cat.get('caption', '')}\n제목: {plan.get('title', '')}\n\n"
        f"출처: '{meta['title']}' — {meta['uploader']} ({meta['url']})\n"
        "⚠️ 비-CC 소재. 원작자 표기 + 번역·재편집 변형 전제로만 사용(권리 확인 필수).\n",
        encoding="utf-8")
    return {
        "category": cat["name"], "slug": cat["slug"], "kind": "shorts2shorts",
        "short": short.name, "desc": f"{name}.txt", "title": plan.get("title", ""),
        "source": {"title": meta["title"], "channel": meta["uploader"], "url": meta["url"],
                   "license": "non-CC (출처표기/변형 전제)", "views": None, "viral_score": None},
        "segments": len(segs), "created": _dt.datetime.now().isoformat(timespec="seconds"),
    }


def load_categories(path: Path) -> list[dict]:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))["categories"]


def main() -> None:
    p = argparse.ArgumentParser(description="쇼츠→쇼츠 (틱톡/샤오홍수 → 한국 쇼츠)")
    p.add_argument("--config", type=Path, default=HERE / "shorts_sources.yaml")
    p.add_argument("--only", default="", help="이 slug 카테고리만")
    p.add_argument("--urls", default="", help="떡상 링크 직접 처리(쉼표구분). 지정 시 --only 카테고리 공식 적용")
    p.add_argument("--per-source", type=int, default=1, help="워치리스트 소스당 최신 N개")
    p.add_argument("--output", type=Path, default=HERE / "output")
    p.add_argument("--cookies", default=os.environ.get("TIKTOK_COOKIES_FILE") or os.environ.get("YT_COOKIES_FILE") or None)
    p.add_argument("--insecure", action="store_true")
    args = p.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} 필요")

    cats = load_categories(args.config)
    if args.only:
        cats = [c for c in cats if c["slug"] == args.only]
    args.output.mkdir(parents=True, exist_ok=True)
    mpath = args.output / "manifest.json"
    manifest = json.loads(mpath.read_text()) if mpath.exists() else []

    # 작업 목록: --urls(즉시) 또는 카테고리 워치리스트 최신
    jobs: list[tuple[dict, str]] = []
    if args.urls:
        cat = cats[0] if cats else {"name": "직접", "slug": "manual", "lang": "zh"}
        for u in [x.strip() for x in args.urls.split(",") if x.strip()]:
            jobs.append((cat, u))
    else:
        for cat in cats:
            for src in cat.get("sources") or []:
                try:
                    for u in latest_from_source(src, insecure=args.insecure, cookies=args.cookies, n=args.per_source):
                        jobs.append((cat, u))
                except Exception as e:
                    log(f"워치리스트 수집 실패({src}): {e}")

    if not jobs:
        step("처리할 소재가 없습니다. --urls 로 떡상 링크를 주거나 shorts_sources.yaml 의 sources 를 채우세요.")
        return

    for cat, url in jobs:
        if any(m.get("source", {}).get("url") == url for m in manifest):
            log(f"이미 처리, 건너뜀: {url}")
            continue
        work = Path(tempfile.mkdtemp(prefix="s2s_", dir=str(args.output)))
        try:
            entry = make_short(cat, url, work, args.output, insecure=args.insecure, cookies=args.cookies)
            manifest.insert(0, entry)
            mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            log(f"✅ 숏츠 완성: {entry['short']}")
        except Exception as e:
            log(f"✖ 실패({url}): {e}")
        finally:
            shutil.rmtree(work, ignore_errors=True)

    step(f"완료 — 매니페스트 {mpath} (총 {len(manifest)})")


if __name__ == "__main__":
    main()

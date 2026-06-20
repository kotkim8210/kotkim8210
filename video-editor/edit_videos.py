#!/usr/bin/env python3
"""여러 영상을 자동 편집해 하나로 합치는 파이프라인.

동작 순서
  1) input 폴더의 영상들을 파일 이름 순서로 읽는다.
  2) 각 영상에서 말 없는(조용한) 구간을 자동으로 잘라낸다.   (silencedetect)
  3) 모든 클립을 동일한 규격으로 정규화한 뒤 이름 순서대로 이어 붙인다. (concat)
  4) 합쳐진 영상의 음성을 한국어로 자동 전사한다.            (faster-whisper)
  5) 한국어 자막(.srt)을 영상 위에 입혀 output 폴더에 저장한다. (libass burn-in)

기본 사용법 (저장소 루트에서):
    python video-editor/edit_videos.py

준비물은 video-editor/setup.sh 로 한 번에 설치할 수 있다.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ── 경로 기본값 ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent          # .../video-editor
REPO_ROOT = SCRIPT_DIR.parent                          # 저장소 루트
DEFAULT_INPUT = REPO_ROOT / "input"
DEFAULT_OUTPUT = REPO_ROOT / "output"
ASSETS_DIR = REPO_ROOT / "assets"            # 폰트·효과음·이미지

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
AUDIO_EXTS = (".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac")


def find_asset(stem: str, exts) -> "Path | None":
    """assets 폴더에서 stem.* 형태의 리소스를 찾는다(예: sound, image1)."""
    for ext in exts:
        p = ASSETS_DIR / f"{stem}{ext}"
        if p.exists():
            return p
    return None

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv", ".wmv", ".mpg", ".mpeg", ".ts"}

# 음성 정규화(EBU R128): 너무 작게 녹음된 영상도 들리게/인식되게 만든다.
# 무음 컷·자막 생성·출력 오디오에 일관되게 적용해, 마이크 볼륨이 낮은 녹화도 정상 처리한다.
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"


# ── 작은 유틸 ─────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def step(msg: str) -> None:
    print(f"\n▶ {msg}", flush=True)


def die(msg: str) -> None:
    print(f"\n✖ 오류: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def run(cmd: list[str], *, capture: bool = False, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """명령을 실행한다. capture=True 면 stdout/stderr 를 잡아 반환한다."""
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE,                # stderr 는 항상 잡아서 오류 메시지에 쓴다
        text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-15:]
        raise RuntimeError("명령 실패: " + " ".join(cmd) + "\n" + "\n".join(tail))
    return proc


# ── ffprobe 헬퍼 ──────────────────────────────────────────────────────────────
def ffprobe_duration(path: Path) -> float:
    proc = run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture=True,
    )
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return 0.0


def image_dims(path: Path) -> tuple[int, int]:
    proc = run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)],
        capture=True,
    )
    w, h = proc.stdout.strip().split("x")
    return int(w), int(h)


def has_audio_stream(path: Path) -> bool:
    proc = run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
        capture=True,
    )
    return bool(proc.stdout.strip())


# ── 1) 무음 구간 검출 ─────────────────────────────────────────────────────────
_SIL_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SIL_END = re.compile(r"silence_end:\s*(-?[\d.]+)")


def detect_silences(path: Path, noise: str, min_silence: float, normalize: bool) -> list[tuple[float, float]]:
    """ffmpeg silencedetect 로 (start, end) 무음 구간 목록을 얻는다.

    normalize=True 면 음성 정규화 후 검출한다(낮은 볼륨 녹화에서 전체가 무음으로
    잡혀 통째로 잘려나가는 문제를 막는다). 정규화는 타임스탬프를 바꾸지 않는다.
    """
    af = (f"{LOUDNORM}," if normalize else "") + f"silencedetect=noise={noise}:d={min_silence}"
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-af", af, "-f", "null", "-"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    text = proc.stderr or ""
    silences: list[tuple[float, float]] = []
    cur_start: float | None = None
    for line in text.splitlines():
        m = _SIL_START.search(line)
        if m:
            cur_start = float(m.group(1))
            continue
        m = _SIL_END.search(line)
        if m and cur_start is not None:
            silences.append((max(0.0, cur_start), float(m.group(1))))
            cur_start = None
    # 파일 끝까지 이어진 무음(닫히지 않은 구간)
    if cur_start is not None:
        silences.append((max(0.0, cur_start), ffprobe_duration(path)))
    return silences


def keep_segments_from_silences(
    duration: float,
    silences: list[tuple[float, float]],
    margin: float,
    min_speech: float,
) -> list[tuple[float, float]]:
    """무음 구간의 여집합(=말하는 구간)을 구하고 margin 만큼 여유를 둔 뒤 병합한다."""
    if duration <= 0:
        return []
    # 무음의 여집합 = 보존할 구간
    keep: list[tuple[float, float]] = []
    cursor = 0.0
    for s, e in sorted(silences):
        s = max(0.0, min(s, duration))
        e = max(0.0, min(e, duration))
        if s > cursor:
            keep.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < duration:
        keep.append((cursor, duration))

    # 말이 끊기지 않도록 앞뒤에 여유(margin)를 붙인다.
    padded = [(max(0.0, a - margin), min(duration, b + margin)) for a, b in keep]

    # 겹치거나 맞닿는 구간 병합
    merged: list[tuple[float, float]] = []
    for a, b in sorted(padded):
        if merged and a <= merged[-1][1] + 1e-3:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))

    # 너무 짧은 조각(잡음 한 번 튄 것 등) 제거
    return [(a, b) for a, b in merged if (b - a) >= min_speech]


# ── 2) 클립 정규화(+ 무음 컷) ─────────────────────────────────────────────────
def select_expr(segments: list[tuple[float, float]]) -> str:
    return "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in segments)


def process_clip(
    src: Path,
    dst: Path,
    segments: list[tuple[float, float]] | None,
    *,
    width: int,
    height: int,
    fps: int,
    normalize: bool,
) -> None:
    """한 번의 ffmpeg 패스로 (음성 정규화 + 무음 컷 + 규격 통일)을 수행한다.

    segments=None 이면 컷 없이 전체를 규격화한다(오디오가 없는 영상 등).
    normalize=True 면 작은 소리를 키워 출력 오디오를 들리게 만든다.
    """
    audio = has_audio_stream(src)

    vf_chain = []
    af_chain = []
    if audio and normalize:
        af_chain.append(LOUDNORM)              # 작은 소리도 들리게 정규화(컷보다 먼저)
    if segments is not None and segments:
        expr = select_expr(segments)
        vf_chain.append(f"select='{expr}'")
        vf_chain.append("setpts=N/FRAME_RATE/TB")
        if audio:
            af_chain.append(f"aselect='{expr}'")
            af_chain.append("asetpts=N/SR/TB")

    # 비디오 규격 통일: fps 고정 → 비율 유지 축소 → 레터박스 패딩 → SAR/픽셀포맷 고정
    vf_chain += [
        f"fps={fps}",
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
        "setsar=1",
        "format=yuv420p",
    ]

    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(src)]

    if not audio:
        # 오디오가 없으면 무음 트랙을 합성해 규격을 맞춘다(concat 호환성).
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]

    cmd += ["-vf", ",".join(vf_chain)]
    if audio:
        af_chain.append("aresample=48000:async=1:first_pts=0")
        cmd += ["-af", ",".join(af_chain)]
    else:
        cmd += ["-map", "0:v", "-map", "1:a", "-shortest"]

    cmd += [
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        str(dst),
    ]
    run(cmd)


# ── 3) 이어 붙이기 ────────────────────────────────────────────────────────────
def concat_clips(clips: list[Path], dst: Path, work: Path) -> None:
    listfile = work / "concat.txt"
    listfile.write_text(
        "".join(f"file '{c.resolve().as_posix()}'\n" for c in clips), encoding="utf-8"
    )
    run([
        "ffmpeg", "-hide_banner", "-y", "-f", "concat", "-safe", "0",
        "-i", str(listfile), "-c", "copy", "-movflags", "+faststart", str(dst),
    ])


# ── 4) 한국어 전사 → SRT ──────────────────────────────────────────────────────
def _srt_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    td = _dt.timedelta(seconds=seconds)
    total_ms = int(round(td.total_seconds() * 1000))
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def hex_to_ass(hex_color: str) -> str:
    """#RRGGBB → ASS 색상(&H00BBGGRR&)."""
    h = hex_color.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def _ass_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    cs = int(round(seconds * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def split_segment(text: str, start: float, end: float, max_chars: int) -> list[dict]:
    """한 문장을 단어 경계에서 ~max_chars 길이로 끊고, 글자 수에 비례해 시간을 배분한다.

    (단어 타임스탬프는 medium 모델에서 환청 토큰·깨진 글자를 만들기 쉬워, 깔끔한
     문장 단위 전사를 비례 분할하는 방식이 더 안정적이다.)
    """
    chunks: list[str] = []
    cur = ""
    for w in text.split():
        cand = f"{cur} {w}".strip()
        if cur and len(cand) > max_chars:
            chunks.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        chunks.append(cur)
    if not chunks:
        return []
    total = sum(len(c) for c in chunks) or 1
    out: list[dict] = []
    t, span = start, max(0.0, end - start)
    for c in chunks:
        ct = span * (len(c) / total)
        out.append({"start": t, "end": min(end, t + ct), "text": c})
        t += ct
    return out


def transcribe_segments(
    media: Path, *, model_name: str, language: str, compute_type: str, initial_prompt: str = "",
):
    """faster-whisper 로 문장(세그먼트) 단위로 전사한다. (내용 컷·자막의 공통 입력)

    initial_prompt 에 도메인 어휘(상품명·전문용어 등)를 주면 한국어 인식 정확도가 올라간다.
    """
    from faster_whisper import WhisperModel  # 지연 임포트(설치 안내를 위해)

    log(f"모델 로딩: {model_name} (compute_type={compute_type}) — 최초 1회 다운로드가 있을 수 있음")
    model = WhisperModel(model_name, device="cpu", compute_type=compute_type)
    segments, info = model.transcribe(
        str(media), language=language, vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500}, beam_size=5,
        initial_prompt=initial_prompt or None,
    )
    log(f"감지 언어: {info.language} (확률 {info.language_probability:.2f})")

    has_korean = re.compile(r"[가-힣]")
    out: list[dict] = []
    for seg in segments:
        text = seg.text.strip()
        if text and has_korean.search(text):   # 한글 없는 영어 환청 세그먼트는 버림
            out.append({"start": seg.start, "end": seg.end, "text": text})
    return out, info


def cues_from_segments(segments: list[dict], max_chars: int) -> list[dict]:
    """문장들을 ~max_chars 길이의 짧은 자막 큐로 끊는다."""
    cues: list[dict] = []
    for s in segments:
        cues.extend(split_segment(s["text"], s["start"], s["end"], max_chars))
    return cues


# ── 2.5) LLM 내용 컷 (무음이 아니라 '의미' — 군말·중복·횡설수설 제거) ────────────
def parse_index_spec(spec: str, n: int) -> set:
    """'1,4,7-9' 같은 1-기반 번호 스펙을 0-기반 인덱스 집합으로 바꾼다."""
    out: set = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a) - 1, int(b)))
        else:
            out.add(int(part) - 1)
    return {i for i in out if 0 <= i < n}


def llm_select_cuts(segments: list[dict], *, model: str) -> set:
    """ANTHROPIC_API_KEY 가 있으면 Claude 가 군말·중복 문장 번호를 골라준다."""
    import json
    import os

    if not os.environ.get("ANTHROPIC_API_KEY"):
        die("--llm-cut 에는 ANTHROPIC_API_KEY 가 필요합니다. (또는 내가 고른 번호를 --cut-segments 로 주세요)")
    try:
        import anthropic
    except ImportError:
        die("anthropic 패키지가 필요합니다:  pip install anthropic")

    numbered = "\n".join(f"{i + 1}: {s['text']}" for i, s in enumerate(segments))
    prompt = (
        "다음은 한 영상의 자막 문장 목록입니다 (번호: 문장).\n"
        "**빼도 되는 문장의 번호만** 골라주세요 — 군말·말 더듬기·같은 말 반복·횡설수설·"
        "의미 없는 추임새(어, 음, 그, 뭐냐 등). 핵심 정보가 담긴 문장은 반드시 남깁니다.\n"
        "보수적으로: 애매하면 남기세요.\n\n"
        f"{numbered}\n\n"
        "잘라낼 문장 번호만 JSON 배열로 답하세요. 예: [3, 7, 12]. 없으면 []."
    )
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=model, max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text")
    m = re.search(r"\[[\d,\s]*\]", text)
    idx: set = set()
    if m:
        for n in json.loads(m.group(0)):
            if 1 <= int(n) <= len(segments):
                idx.add(int(n) - 1)
    return idx


def apply_content_cut(merged: Path, segments: list[dict], cut_idx: set, dst: Path, *, fps: int):
    """cut_idx 문장 구간을 잘라낸 영상을 만들고, 남은 문장의 타임코드를 새 타임라인으로 보정한다."""
    keep = sorted((s["start"], s["end"]) for i, s in enumerate(segments) if i not in cut_idx)
    if not keep:
        return None, []
    ranges: list[list[float]] = []
    for a, b in keep:                       # 맞닿은 구간 병합
        if ranges and a <= ranges[-1][1] + 0.05:
            ranges[-1][1] = max(ranges[-1][1], b)
        else:
            ranges.append([a, b])

    expr = select_expr([(a, b) for a, b in ranges])
    run([
        "ffmpeg", "-hide_banner", "-y", "-i", str(merged),
        "-vf", f"select='{expr}',setpts=N/FRAME_RATE/TB,fps={fps}",
        "-af", f"aselect='{expr}',asetpts=N/SR/TB,aresample=48000",
        "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(dst),
    ])

    offsets, acc = [], 0.0                  # 원본 t → 새 타임라인 t 매핑
    for a, b in ranges:
        offsets.append((a, b, acc))
        acc += b - a

    def remap(t: float):
        for a, b, off in offsets:
            if a - 1e-3 <= t <= b + 1e-3:
                return off + (max(a, min(t, b)) - a)
        return None

    new_segs: list[dict] = []
    for i, s in enumerate(segments):
        if i in cut_idx:
            continue
        ns, ne = remap(s["start"]), remap(s["end"])
        if ns is not None and ne is not None:
            new_segs.append({"start": ns, "end": max(ns, ne), "text": s["text"]})
    return dst, new_segs


def write_srt(cues: list[dict], path: Path, *, offset: float = 0.0) -> None:
    lines: list[str] = []
    for i, c in enumerate(cues, 1):
        lines += [str(i),
                  f"{_srt_time(c['start'] + offset)} --> {_srt_time(c['end'] + offset)}",
                  c["text"], ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def _highlight(text: str, keywords: list[str], orange: str, white: str) -> str:
    """중요 단어를 주황색 ASS 태그로 감싼다."""
    spans: list[list[int]] = []
    for kw in keywords:
        if not kw:
            continue
        start = 0
        while (i := text.find(kw, start)) >= 0:
            spans.append([i, i + len(kw)])
            start = i + len(kw)
    if not spans:
        return text
    spans.sort()
    merged: list[list[int]] = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    out, prev = [], 0
    for s, e in merged:
        out.append(text[prev:s])
        out.append(f"{{\\1c{orange}}}{text[s:e]}{{\\1c{white}}}")
        prev = e
    out.append(text[prev:])
    return "".join(out)


def write_ass(
    cues: list[dict], path: Path, *, width: int, height: int, font: str,
    font_size: int, orange_hex: str, highlight: list[str], margin_v: int,
    pop: bool = True,
) -> None:
    """스타일 ASS 자막 생성: 흰색 굵게 + 검은 외곽선, 하단, 중요단어 주황색.

    pop=True 면 자막이 등장할 때 살짝 커졌다 제자리로 돌아오는 줌팝 효과를 준다.
    """
    orange, white = hex_to_ass(orange_hex), "&H00FFFFFF&"
    outline = max(2, round(font_size * 0.07))
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {width}\nPlayResY: {height}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{font},{font_size},{white},&H000000FF,&H00000000,&H64000000,"
        f"1,0,0,0,100,100,0,0,1,{outline},1,2,60,60,{margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    # 줌팝: 등장 시 58%→106%→100% 로 빠르게 튀어오르는 효과(\t 변환 태그)
    pop_tag = (r"{\fscx58\fscy58\t(0,120,\fscx106\fscy106)\t(120,210,\fscx100\fscy100)}"
               if pop else "")
    rows = [
        f"Dialogue: 0,{_ass_time(c['start'])},{_ass_time(c['end'])},Default,,0,0,0,,"
        f"{pop_tag}{_highlight(c['text'], highlight, orange, white)}"
        for c in cues
    ]
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


# ── 5) 자막 입히기(번인) ──────────────────────────────────────────────────────
def burn_subtitles(video: Path, srt: Path, dst: Path, *, font: str, font_size: int) -> None:
    """libass(subtitles 필터)로 SRT 를 영상에 태운다. SRT 는 작업 폴더 기준 상대경로로 참조."""
    style = (
        f"FontName={font},FontSize={font_size},"
        "PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,BackColour=&H80000000&,"
        "BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=40"
    )
    # subtitles 필터는 경로의 특수문자에 민감하므로, 작업 폴더에서 파일명만 참조한다.
    run(
        [
            "ffmpeg", "-hide_banner", "-y", "-i", str(video.resolve()),
            "-vf", f"subtitles={srt.name}:force_style='{style}'",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "copy", "-movflags", "+faststart",
            str(dst.resolve()),
        ],
        cwd=srt.parent,
    )


def mux_soft_subtitles(video: Path, srt: Path, dst: Path) -> None:
    """자막을 태우지 않고 소프트 자막 트랙(mov_text)으로 넣는다(--soft-subs)."""
    run([
        "ffmpeg", "-hide_banner", "-y", "-i", str(video), "-i", str(srt),
        "-c", "copy", "-c:s", "mov_text", "-metadata:s:s:0", "language=kor",
        "-movflags", "+faststart", str(dst),
    ])


# ── 6) 짤(이미지) 오버레이 · 효과음 · 인트로 ─────────────────────────────────
def find_cue_time(cues: list[dict], keyword: str) -> "float | None":
    """자막 큐에서 keyword 가 처음 나오는 시점을 찾는다(짤 삽입 타이밍)."""
    for c in cues:
        if keyword and keyword in c["text"]:
            return c["start"]
    return None


def build_overlays(specs: list[str], cues: list[dict], vid_w: int, vid_h: int) -> list[dict]:
    """'경로@키워드@지속초' 스펙들을 SRT 타이밍에 맞춘 오버레이 목록으로 변환한다."""
    box_w, box_h = vid_w * 0.42, vid_h * 0.50
    overlays: list[dict] = []
    for spec in specs or []:
        parts = spec.split("@")
        path = Path(parts[0])
        keyword = parts[1].strip() if len(parts) > 1 else ""
        dur = float(parts[2]) if len(parts) > 2 and parts[2] else 2.6
        if not path.exists():
            log(f"⚠ 짤 파일 없음: {path} → 건너뜀")
            continue
        # 키워드는 '만렙|장비템|레전드' 처럼 | 로 여러 후보를 줄 수 있다(전사 흔들림 대비)
        alts = [k.strip() for k in keyword.split("|") if k.strip()]
        t = 0.0 if not alts else next(
            (c["start"] for c in cues if any(a in c["text"] for a in alts)), None)
        if t is None:
            log(f"⚠ 짤 키워드 '{keyword}' 를 자막에서 못 찾음 → 건너뜀")
            continue
        iw, ih = image_dims(path)
        scale = min(box_w / iw, box_h / ih)
        h = max(2, int(round(ih * scale / 2)) * 2)
        overlays.append({"path": str(path), "start": max(0.0, t - 0.2),
                         "dur": dur, "height": h, "mx": 60, "my": 70})
        log(f"짤 삽입: {path.name} @ {_srt_time(t)} ('{keyword}')")
    return overlays


def build_intro(merged: Path, sound: Path, dst: Path, *, width: int, height: int, fps: int) -> float:
    """합본 첫 프레임을 정지화면으로 두고 인트로 효과음(두둥)을 깐 짧은 인트로. 길이를 반환."""
    first = dst.parent / "first.png"
    run(["ffmpeg", "-hide_banner", "-y", "-i", str(merged), "-frames:v", "1", str(first)])
    dur = max(1.0, ffprobe_duration(sound))
    run([
        "ffmpeg", "-hide_banner", "-y",
        "-loop", "1", "-t", f"{dur:.3f}", "-i", str(first), "-i", str(sound),
        "-vf", f"scale={width}:{height},fps={fps},format=yuv420p,fade=t=in:st=0:d=0.4",
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest",
        str(dst),
    ])
    return dur


def render_rich(
    merged: Path, ass: Path, dst: Path, *,
    overlays: list[dict], transitions: list[dict], fontsdir: Path,
    fps: int, zoom: bool = True,
) -> None:
    """오버레이 이미지 + 자막(ASS) 번인 + 전환 효과음 믹스를 한 번에 렌더한다.

    zoom=True 면 짤이 등장할 때 줌인, 사라질 때 줌아웃으로 보이도록 크기를 시간에 따라 키운다.
    """
    total = ffprobe_duration(merged) + 0.5
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(merged.resolve())]
    for ov in overlays:
        if zoom:  # 시간에 따라 크기를 바꾸려면 정지 이미지를 프레임 흐름으로 만들어야 한다
            cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{total:.2f}",
                    "-i", str(Path(ov["path"]).resolve())]
        else:
            cmd += ["-i", str(Path(ov["path"]).resolve())]
    trans_base = 1 + len(overlays)
    for tr in transitions:
        cmd += ["-i", str(Path(tr["sound"]).resolve())]

    fc: list[str] = []
    last = "[0:v]"
    for i, ov in enumerate(overlays):
        s, e, H = ov["start"], ov["start"] + ov["dur"], ov["height"]
        if zoom:
            ti, to, floor, amp = 0.22, 0.20, 0.42, 0.58   # 등장 줌인 / 퇴장 줌아웃
            hexpr = (f"{H}*({floor}+{amp}*min(min(max((t-{s:.3f})/{ti},0),1),"
                     f"min(max(({e:.3f}-t)/{to},0),1)))")
            fc.append(f"[{1 + i}:v]scale=w=-2:h='{hexpr}':eval=frame[ov{i}]")
        else:
            fc.append(f"[{1 + i}:v]scale=-2:{H}[ov{i}]")
        fc.append(f"{last}[ov{i}]overlay=x=W-w-{ov['mx']}:y={ov['my']}:"
                  f"enable='between(t,{s:.2f},{e:.2f})'[v{i}]")
        last = f"[v{i}]"
    fc.append(f"{last}ass={ass.resolve().as_posix()}:fontsdir={fontsdir.resolve().as_posix()}[vout]")

    if transitions:
        amix = ["[0:a]"]
        for j, tr in enumerate(transitions):
            d = int(round(tr["at"] * 1000))
            fc.append(f"[{trans_base + j}:a]adelay={d}|{d},volume=1.0[tr{j}]")
            amix.append(f"[tr{j}]")
        fc.append("".join(amix) + f"amix=inputs={len(amix)}:duration=first:normalize=0[aout]")
        amap = "[aout]"
    else:
        amap = "0:a"

    cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", amap,
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(dst.resolve())]
    run(cmd)


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main() -> None:
    p = argparse.ArgumentParser(
        description="여러 영상의 무음 구간을 자동으로 잘라 이어 붙이고 한국어 자막을 입힌다.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="원본 영상 폴더")
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="결과물 폴더")
    p.add_argument("--name", default=None, help="결과 파일 이름(미지정 시 시간으로 자동 생성)")
    # 무음 컷 옵션
    p.add_argument("--noise", default="-30dB", help="이보다 작은 소리는 무음으로 간주")
    p.add_argument("--min-silence", type=float, default=0.6, help="이 길이(초) 이상 조용해야 컷 대상")
    p.add_argument("--margin", type=float, default=0.20, help="말 구간 앞뒤로 남길 여유(초)")
    p.add_argument("--min-speech", type=float, default=0.20, help="이보다 짧은 조각은 버림(초)")
    p.add_argument("--no-trim", action="store_true", help="무음 컷을 끄고 합치기만 한다")
    p.add_argument("--no-normalize-audio", action="store_true",
                   help="음성 정규화를 끈다(작게 녹음된 영상은 거의 잘려나갈 수 있어 권장 안 함)")
    # 규격
    p.add_argument("--width", type=int, default=1920, help="결과 가로 해상도")
    p.add_argument("--height", type=int, default=1080, help="결과 세로 해상도")
    p.add_argument("--fps", type=int, default=30, help="결과 프레임레이트")
    # 자막 옵션
    p.add_argument("--model", default="medium",
                   help="faster-whisper 모델: tiny/base/small/medium/large-v3/large-v3-turbo "
                        "(GPU 있으면 large-v3-turbo 권장 — 정확·빠름)")
    p.add_argument("--initial-prompt", default="",
                   help="도메인 어휘 힌트(상품명·전문용어). 한국어 인식 정확도↑. 예: '피그마,상세페이지,초당옥수수'")
    p.add_argument("--language", default="ko", help="전사 언어 코드")
    p.add_argument("--compute-type", default="int8", help="ctranslate2 연산 타입 (int8 권장)")
    p.add_argument("--font", default="Gmarket Sans TTF", help="자막 폰트(assets 폴더 폰트도 사용 가능)")
    p.add_argument("--font-size", type=int, default=0, help="자막 글자 크기(0=해상도에 맞춰 자동)")
    p.add_argument("--max-chars", type=int, default=12, help="자막 한 줄당 글자수(이 정도로 끊음)")
    p.add_argument("--margin-v", type=int, default=20, help="자막을 화면 아래에서 띄울 거리(px)")
    p.add_argument("--orange", default="#FF8C42", help="중요 단어 강조 색(밝은 주황)")
    p.add_argument("--highlight", default="", help="주황색으로 강조할 단어들(쉼표로 구분)")
    p.add_argument("--overlay", action="append", default=[],
                   help="짤 삽입: '경로@자막키워드@지속초' (반복 가능). 예: assets/image.jpg@만렙@2.6")
    p.add_argument("--no-intro-sound", action="store_true", help="인트로 효과음(두둥)을 넣지 않는다")
    p.add_argument("--no-transition-sound", action="store_true", help="영상 전환 효과음(휘릭)을 넣지 않는다")
    p.add_argument("--no-text-pop", action="store_true", help="자막 등장 줌팝 효과를 끈다")
    p.add_argument("--no-image-zoom", action="store_true", help="짤 등장 줌인/퇴장 줌아웃 효과를 끈다")
    # LLM 내용 컷 (2단계: 무음이 아니라 군말·중복 제거)
    p.add_argument("--llm-cut", action="store_true",
                   help="Claude(ANTHROPIC_API_KEY)로 군말·중복 문장을 자동 제거한다")
    p.add_argument("--llm-model", default="claude-opus-4-8", help="내용 컷에 쓸 Claude 모델")
    p.add_argument("--cut-segments", default="",
                   help="직접 제거할 문장 번호(1-기반): 예 '3,7,12-15'  (--llm-cut 대신 수동 지정)")
    p.add_argument("--no-subs", action="store_true", help="자막 단계를 건너뛴다")
    p.add_argument("--soft-subs", action="store_true", help="자막을 태우지 않고 트랙으로만 넣는다")
    p.add_argument("--keep-work", action="store_true", help="중간 산출물(작업 폴더)을 지우지 않는다")
    args = p.parse_args()

    # 의존성 점검
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            die(f"{tool} 가 필요합니다. 먼저 'bash video-editor/setup.sh' 를 실행하세요.")

    args.input.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)

    normalize = not args.no_normalize_audio

    videos = sorted(
        [f for f in args.input.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXTS],
        key=lambda f: f.name.lower(),
    )
    if not videos:
        die(f"입력 영상이 없습니다. '{args.input}' 폴더에 영상을 넣어주세요.")

    step(f"입력 영상 {len(videos)}개 (이름 순서)")
    for v in videos:
        log(v.name)

    work = Path(tempfile.mkdtemp(prefix="videoedit_", dir=str(args.output)))
    try:
        # ── 클립별: 무음 컷 + 정규화 ──
        processed: list[Path] = []
        for idx, v in enumerate(videos, 1):
            step(f"[{idx}/{len(videos)}] 처리: {v.name}")
            dur = ffprobe_duration(v)
            segments: list[tuple[float, float]] | None
            if args.no_trim or not has_audio_stream(v):
                segments = None
                if not args.no_trim:
                    log("오디오 없음 → 무음 컷 생략, 전체 사용")
            else:
                silences = detect_silences(v, args.noise, args.min_silence, normalize)
                segments = keep_segments_from_silences(dur, silences, args.margin, args.min_speech)
                kept = sum(b - a for a, b in segments)
                log(f"무음 {len(silences)}곳 검출 → {dur:.1f}s 중 {kept:.1f}s 유지 "
                    f"({(1 - kept / dur) * 100:.0f}% 컷)" if dur else "구간 분석 완료")
                if not segments:
                    log("말하는 구간이 없어 이 영상은 건너뜁니다.")
                    continue

            out_clip = work / f"clip_{idx:03d}.mp4"
            process_clip(v, out_clip, segments, width=args.width, height=args.height,
                         fps=args.fps, normalize=normalize)
            processed.append(out_clip)

        if not processed:
            die("편집 후 남은 영상이 없습니다. --noise/--min-silence 값을 조정해 보세요.")

        # ── 이어 붙이기 ──
        step(f"{len(processed)}개 클립 이어 붙이기")
        merged = work / "merged.mp4"
        if len(processed) == 1:
            shutil.copy(processed[0], merged)
        else:
            concat_clips(processed, merged, work)
        log(f"합본 길이: {ffprobe_duration(merged):.1f}s")

        # ── 클립 경계(전환 효과음 위치) ──
        clip_durs = [ffprobe_duration(c) for c in processed]
        boundaries, acc = [], 0.0
        for d in clip_durs[:-1]:
            acc += d
            boundaries.append(acc)

        # ── 결과 파일명 ──
        stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        base = args.name or f"edited_{stamp}"
        final = args.output / f"{base}.mp4"
        srt_out = args.output / f"{base}.srt"

        if args.no_subs:
            step("자막 단계 생략 → 합본 저장")
            shutil.copy(merged, final)
        else:
            step("한국어 자막 자동 생성 (문장 단위 전사)")
            segments, _info = transcribe_segments(
                merged, model_name=args.model, language=args.language,
                compute_type=args.compute_type, initial_prompt=args.initial_prompt,
            )
            video = merged   # 내용 컷을 하면 잘린 영상으로 바뀐다

            # ── 2단계: LLM 내용 컷 (무음이 아니라 군말·중복 제거) ──
            if (args.cut_segments or args.llm_cut) and segments:
                step("LLM 내용 컷 (군말·중복 문장 제거)")
                cut_idx = (parse_index_spec(args.cut_segments, len(segments))
                           if args.cut_segments else llm_select_cuts(segments, model=args.llm_model))
                if cut_idx:
                    cut_vid = work / "content_cut.mp4"
                    video, segments = apply_content_cut(merged, segments, cut_idx, cut_vid, fps=args.fps)
                    if video:
                        log(f"문장 {len(cut_idx)}개 제거 → {ffprobe_duration(video):.1f}s "
                            f"(원본 {ffprobe_duration(merged):.1f}s)")
                    else:
                        die("내용 컷 후 남은 문장이 없습니다. 컷 목록을 줄여보세요.")
                else:
                    log("LLM 이 자를 문장을 고르지 않았습니다 (전부 유지).")

            cues = cues_from_segments(segments, args.max_chars)
            log(f"자막 {len(cues)}개 생성")

            if not cues:
                log("전사된 음성이 없어 자막 없이 저장합니다.")
                shutil.copy(video, final)
            elif args.soft_subs:
                srt = work / "subs.srt"
                write_srt(cues, srt)
                shutil.copy(srt, srt_out)
                step("소프트 자막 트랙으로 합치기")
                mux_soft_subtitles(video, srt, final)
            else:
                # 자막(ASS): 흰색 굵게 + 검은 외곽선, 하단, 중요단어 주황색
                font_size = args.font_size or max(20, round(args.height * 0.076))
                highlight = [w.strip() for w in args.highlight.split(",") if w.strip()]
                ass = work / "subs.ass"
                write_ass(cues, ass, width=args.width, height=args.height, font=args.font,
                          font_size=font_size, orange_hex=args.orange,
                          highlight=highlight, margin_v=args.margin_v,
                          pop=not args.no_text_pop)

                # 짤(이미지) 오버레이 + 전환 효과음
                overlays = build_overlays(args.overlay, cues, args.width, args.height)
                transitions = []
                tsound = find_asset("sound1", AUDIO_EXTS)
                if tsound and boundaries and not args.no_transition_sound:
                    transitions = [{"sound": str(tsound), "at": b} for b in boundaries]
                    log(f"전환 효과음(휘릭) {len(transitions)}곳 삽입")

                step("자막·짤·효과음 합성 렌더")
                content = work / "content.mp4"
                render_rich(video, ass, content, overlays=overlays,
                            transitions=transitions, fontsdir=ASSETS_DIR,
                            fps=args.fps, zoom=not args.no_image_zoom)

                # 인트로 효과음(두둥) 붙이기
                intro_dur = 0.0
                isound = find_asset("sound", AUDIO_EXTS)
                if isound and not args.no_intro_sound:
                    step("인트로 효과음(두둥) 붙이기")
                    intro = work / "intro.mp4"
                    intro_dur = build_intro(video, isound, intro,
                                            width=args.width, height=args.height, fps=args.fps)
                    concat_clips([intro, content], final, work)
                else:
                    shutil.copy(content, final)

                write_srt(cues, srt_out, offset=intro_dur)   # 최종 타임라인 기준 자막 파일
                log(f"자막 {len(cues)}개 → {srt_out.name}")

        step("완료 🎬")
        log(f"결과물: {final}")
        print(flush=True)

    finally:
        if args.keep_work:
            log(f"작업 폴더 보존: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        die(str(e))
    except KeyboardInterrupt:
        die("사용자 중단")

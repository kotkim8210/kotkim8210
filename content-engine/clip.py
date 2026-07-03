#!/usr/bin/env python3
"""오리지널 영상의 한 구간 → 9:16(또는 1:1) 쇼츠로 컷 + 자막 번인.

증폭기(amplify)의 영상 재가공 코어. '내 오리지널'의 하이라이트 구간을 잘라
세로 숏폼으로 만든다(정책 안전 — 내 콘텐츠의 재가공).

자막은 두 경로:
  - --transcript transcript.json + 구간[start,end] → 자동 슬라이스·리베이스·문장 분할
  - --cues cues.json (이미 [{start,end,text}] 가진 경우, 0초 기준 상대시간)
훅(첫 ~2.5초 강조 한 줄)과 크레딧(하단 지속 표기)을 얹을 수 있다.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ASSETS = REPO / "assets"

# 한글 폰트(시스템 설치 확인됨). Gmarket 을 쓰려면 fontsdir 로 assets 지정.
FONT_MAIN = "NanumSquare"
FONT_CREDIT = "NanumGothic"


def _ass_time(t: float) -> str:
    if t < 0:
        t = 0.0
    h = int(t // 3600); m = int((t % 3600) // 60)
    s = int(t % 60); cs = int(round((t - int(t)) * 100))
    if cs == 100:
        s += 1; cs = 0
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _ass_esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def _split_by_chars(text: str, start: float, end: float, max_chars: int) -> "list[dict]":
    text = " ".join(text.split())
    if not text:
        return []
    if max_chars <= 0 or len(text) <= max_chars:
        return [{"start": start, "end": end, "text": text}]
    chunks: "list[str]" = []
    buf = ""
    for w in text.split(" "):
        cand = (buf + " " + w).strip()
        if len(cand) <= max_chars or not buf:
            buf = cand
        else:
            chunks.append(buf); buf = w
    if buf:
        chunks.append(buf)
    flat: "list[str]" = []
    for c in chunks:
        while len(c) > max_chars:
            flat.append(c[:max_chars]); c = c[max_chars:]
        if c:
            flat.append(c)
    total = sum(len(c) for c in flat) or 1
    out = []; t = start; span = end - start
    for c in flat:
        dur = span * (len(c) / total)
        out.append({"start": round(t, 3), "end": round(t + dur, 3), "text": c})
        t += dur
    out[-1]["end"] = round(end, 3)
    return out


def cues_from_transcript(transcript: dict, start: float, end: float, max_chars: int) -> "list[dict]":
    """transcript.json 의 segments 에서 [start,end] 와 겹치는 부분을 잘라 0초 기준으로 리베이스."""
    cues: "list[dict]" = []
    for seg in transcript.get("segments", []):
        s = max(seg["start"], start); e = min(seg["end"], end)
        if e - s <= 0.05:
            continue
        rel_s = round(s - start, 3); rel_e = round(e - start, 3)
        cues.extend(_split_by_chars(seg.get("text", ""), rel_s, rel_e, max_chars))
    return cues


def build_ass(cues: "list[dict]", *, hook: "str|None", credit: "str|None",
              width: int, height: int) -> str:
    # 해상도 비례 폰트 크기.
    base = min(width, height)
    main_fs = int(base * 0.072)
    hook_fs = int(base * 0.090)
    credit_fs = int(base * 0.034)
    margin_v = int(height * 0.16)          # 자막을 아래에서 띄움(하단 1/6 지점)
    hook_mv = int(height * 0.20)           # 훅은 상단
    outline = max(3, int(base * 0.006))

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook, {FONT_MAIN}, {hook_fs}, &H00429CFF, &H000000FF, &H00000000, &H64000000, 1,0,0,0, 100,100,0,0, 1,{outline+1},3, 8, 60,60,{hook_mv}, 1
Style: Main, {FONT_MAIN}, {main_fs}, &H00FFFFFF, &H000000FF, &H00000000, &H64000000, 1,0,0,0, 100,100,0,0, 1,{outline},2, 2, 70,70,{margin_v}, 1
Style: Credit, {FONT_CREDIT}, {credit_fs}, &H00DDDDDD, &H000000FF, &H00000000, &H64000000, 0,0,0,0, 100,100,0,0, 1,2,1, 2, 40,40,50, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    if hook:
        lines.append(f"Dialogue: 0,{_ass_time(0)},{_ass_time(2.6)},Hook,,0,0,0,,{_ass_esc(hook)}")
    for c in cues:
        lines.append(f"Dialogue: 0,{_ass_time(c['start'])},{_ass_time(c['end'])},Main,,0,0,0,,{_ass_esc(c['text'])}")
    if credit:
        dur = cues[-1]["end"] if cues else 30
        lines.append(f"Dialogue: 0,{_ass_time(0)},{_ass_time(dur)},Credit,,0,0,0,,{_ass_esc(credit)}")
    return head + "\n".join(lines) + "\n"


def make_short(src: "str|Path", start: float, end: float, out: "str|Path", *,
               cues: "list[dict]|None" = None, transcript: "dict|None" = None,
               hook: "str|None" = None, credit: "str|None" = None,
               fit: str = "blur", width: int = 1080, height: int = 1920,
               fps: int = 30, max_chars: int = 16, crf: int = 20) -> Path:
    src = Path(src); out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    dur = round(end - start, 3)
    if cues is None and transcript is not None:
        cues = cues_from_transcript(transcript, start, end, max_chars)
    cues = cues or []

    ass_path = out.with_suffix(".ass")
    ass_path.write_text(build_ass(cues, hook=hook, credit=credit, width=width, height=height),
                        encoding="utf-8")

    if fit == "blur":
        vf = (f"[0:v]split=2[bg][fg];"
              f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,"
              f"crop={width}:{height},gblur=sigma=22[bgb];"
              f"[fg]scale={width}:{height}:force_original_aspect_ratio=decrease[fgs];"
              f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,"
              f"subtitles='{ass_path.as_posix()}',format=yuv420p[v]")
    elif fit == "cover":
        vf = (f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
              f"crop={width}:{height},subtitles='{ass_path.as_posix()}',format=yuv420p[v]")
    else:  # contain
        vf = (f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
              f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,"
              f"subtitles='{ass_path.as_posix()}',format=yuv420p[v]")

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-ss", str(start), "-t", str(dur), "-i", str(src),
           "-filter_complex", vf, "-map", "[v]", "-map", "0:a?",
           "-r", str(fps), "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="오리지널 구간 → 9:16 쇼츠(자막 번인)")
    p.add_argument("src", type=Path)
    p.add_argument("--start", type=float, required=True)
    p.add_argument("--end", type=float, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--transcript", type=Path, help="transcript.json (자동 자막)")
    p.add_argument("--cues", type=Path, help="cues.json (0초 기준 상대시간)")
    p.add_argument("--hook", default=None, help="첫 2.6초 상단 강조 한 줄")
    p.add_argument("--credit", default=None, help="하단 지속 표기(예: @채널 · 원본 링크)")
    p.add_argument("--fit", choices=["blur", "cover", "contain"], default="blur")
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--height", type=int, default=1920)
    p.add_argument("--max-chars", type=int, default=16)
    a = p.parse_args()

    transcript = json.loads(a.transcript.read_text(encoding="utf-8")) if a.transcript else None
    cues = json.loads(a.cues.read_text(encoding="utf-8")) if a.cues else None
    out = make_short(a.src, a.start, a.end, a.out, cues=cues, transcript=transcript,
                     hook=a.hook, credit=a.credit, fit=a.fit,
                     width=a.width, height=a.height, max_chars=a.max_chars)
    print(f"✅ 쇼츠: {out}")


if __name__ == "__main__":
    main()

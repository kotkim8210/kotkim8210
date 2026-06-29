#!/usr/bin/env python3
"""오디오그램 — 브랜드 배경 + 원본 오디오 + 큰 자막으로 만드는 '깔끔한' 9:16 쇼츠.

영상 소스가 없거나(팟캐스트·라디오) 비주얼이 약할 때(화면녹화·세로 안 맞는 영상),
오리지널 '오디오'를 살려 폴리시된 캡션 쇼츠로 재가공한다. 강의/인터뷰/사연낭독에 강함.

clip.py 의 자막 빌더(문장 슬라이스·ASS)를 재사용한다.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import clip as C  # cues_from_transcript, _ass_time, _ass_esc 재사용

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
BG = (16, 18, 22)
FG = (245, 246, 248)
SUB = (165, 172, 180)
ACCENT = (255, 140, 66)
FONT_BOLD = ASSETS / "GmarketSansTTFBold.ttf"
FONT_BODY = Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
if not FONT_BODY.exists():
    FONT_BODY = ASSETS / "GmarketSansTTFMedium.ttf"


def _wrap(draw, text, font, max_w):
    lines, buf = [], ""
    for w in text.split(" "):
        cand = (buf + " " + w).strip()
        if draw.textlength(cand, font=font) <= max_w or not buf:
            buf = cand
        else:
            lines.append(buf); buf = w
    if buf:
        lines.append(buf)
    return lines


def _make_bg(title: str, handle: str, kicker: str, w: int, h: int) -> Path:
    img = Image.new("RGB", (w, h), BG); d = ImageDraw.Draw(img)
    for y in range(h):  # 미세 그라디언트
        t = y / h
        d.line([(0, y), (w, y)], fill=(int(16 + t * 8), int(18 + t * 6), int(22 + t * 12)))
    pad = 80
    # 상단 키커(채널/주제 태그)
    kf = ImageFont.truetype(str(FONT_BOLD), 38)
    d.rounded_rectangle([pad, 150, pad + d.textlength(kicker, font=kf) + 44, 218],
                        radius=14, fill=ACCENT)
    d.text((pad + 22, 160), kicker, font=kf, fill=(18, 18, 18))
    # 큰 따옴표
    d.text((pad - 6, 250), "“", font=ImageFont.truetype(str(FONT_BOLD), 200), fill=(60, 64, 72))
    # 타이틀(상단부) — \n 은 강제 개행으로 처리(폰트가 백슬래시를 ₩로 렌더하는 문제 회피)
    tf = ImageFont.truetype(str(FONT_BOLD), 72)
    y = 430
    for para in title.split("\n"):
        for ln in _wrap(d, para, tf, w - 2 * pad):
            d.text((pad, y), ln, font=tf, fill=FG); y += 92
    # 하단 핸들 + 라인
    hf = ImageFont.truetype(str(FONT_BODY), 40)
    d.line([pad, h - 150, pad + 80, h - 150], fill=ACCENT, width=6)
    d.text((pad, h - 130), handle, font=hf, fill=SUB)
    p = Path(tempfile.mktemp(suffix=".png")); img.save(p, "PNG")
    return p


def build_caption_ass(cues, w, h):
    base = min(w, h)
    fs = int(base * 0.075)
    out = int(base * 0.006)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap, NanumSquare, {fs}, &H00FFFFFF, &H000000FF, &H00101010, &H64000000, 1,0,0,0, 100,100,0,0, 1,{out},2, 5, 80,80,0, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [f"Dialogue: 0,{C._ass_time(c['start'])},{C._ass_time(c['end'])},Cap,,0,0,0,,{C._ass_esc(c['text'])}"
             for c in cues]
    return head + "\n".join(lines) + "\n"


def make(src, start, end, out, *, transcript, title, handle="@channel",
         kicker="SHORTS", w=1080, h=1920, max_chars=14):
    src = Path(src); out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    dur = round(end - start, 3)
    cues = C.cues_from_transcript(transcript, start, end, max_chars)
    ass = out.with_suffix(".ass")
    ass.write_text(build_caption_ass(cues, w, h), encoding="utf-8")
    bg = _make_bg(title, handle, kicker, w, h)
    vf = f"subtitles='{ass.as_posix()}'"
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-loop", "1", "-i", str(bg),
           "-ss", str(start), "-t", str(dur), "-i", str(src),
           "-filter_complex", f"[0:v]{vf},format=yuv420p[v]",
           "-map", "[v]", "-map", "1:a",
           "-t", str(dur), "-r", "30", "-c:v", "libx264", "-preset", "medium",
           "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-shortest",
           "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    bg.unlink(missing_ok=True)
    return out


def main():
    p = argparse.ArgumentParser(description="오디오그램(브랜드 배경 + 오디오 + 큰 자막) 9:16")
    p.add_argument("src", type=Path)
    p.add_argument("--start", type=float, required=True)
    p.add_argument("--end", type=float, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--transcript", type=Path, required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--handle", default="@channel")
    p.add_argument("--kicker", default="SHORTS")
    p.add_argument("--max-chars", type=int, default=14)
    a = p.parse_args()
    tr = json.loads(a.transcript.read_text(encoding="utf-8"))
    out = make(a.src, a.start, a.end, a.out, transcript=tr, title=a.title,
               handle=a.handle, kicker=a.kicker, max_chars=a.max_chars)
    print(f"✅ 오디오그램: {out}")


if __name__ == "__main__":
    main()

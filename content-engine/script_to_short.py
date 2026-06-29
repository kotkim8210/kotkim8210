#!/usr/bin/env python3
"""대본(텍스트) → TTS 내레이션 → 9:16 오디오그램 쇼츠 (소스 영상 없는 '주제→영상' 경로).

증폭기의 두 입력 경로 중 'B. 대본/주제' 경로. 영상 소스가 없을 때 대본을 TTS로 읽고
문장 타이밍으로 자막을 싱크해 브랜드 배경 쇼츠를 만든다. (전사 불필요 — 타이밍은 TTS가 줌.)

tts.py(합성·타이밍) + audiogram.py(배경·자막 ASS)를 조립한다.
"""
from __future__ import annotations

import argparse
import subprocess
from dataclasses import asdict
from pathlib import Path

import audiogram as A
import tts as T


def make(script: str, out: "str|Path", *, title: str, handle: str = "@channel",
         kicker: str = "SHORTS", voice: str = "male", rate: str = "+6%",
         w: int = 1080, h: int = 1920, max_chars: int = 14) -> Path:
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    voice_id = T.KO_VOICES.get(voice, voice)
    mp3 = out.with_suffix(".mp3")
    cues = T.synthesize(script, mp3, voice=voice_id, rate=rate, max_chars=max_chars)
    cue_dicts = [asdict(c) for c in cues]

    ass = out.with_suffix(".ass")
    ass.write_text(A.build_caption_ass(cue_dicts, w, h), encoding="utf-8")
    bg = A._make_bg(title, handle, kicker, w, h)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-loop", "1", "-i", str(bg), "-i", str(mp3),
           "-filter_complex", f"[0:v]subtitles='{ass.as_posix()}',format=yuv420p[v]",
           "-map", "[v]", "-map", "1:a", "-r", "30", "-c:v", "libx264",
           "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
           "-shortest", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    bg.unlink(missing_ok=True)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="대본 → TTS → 9:16 오디오그램 쇼츠")
    p.add_argument("--script", type=Path, required=True, help="대본 텍스트 파일")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--title", required=True, help="배경 상단 타이틀(\\n 개행)")
    p.add_argument("--handle", default="@channel")
    p.add_argument("--kicker", default="SHORTS")
    p.add_argument("--voice", default="male", help="female/male/multi 또는 보이스ID")
    p.add_argument("--rate", default="+6%")
    p.add_argument("--max-chars", type=int, default=14)
    a = p.parse_args()
    script = a.script.read_text(encoding="utf-8").strip()
    out = make(script, a.out, title=a.title.replace("\\n", "\n"), handle=a.handle,
               kicker=a.kicker, voice=a.voice, rate=a.rate, max_chars=a.max_chars)
    print(f"✅ 쇼츠(TTS): {out}")


if __name__ == "__main__":
    main()

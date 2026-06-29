#!/usr/bin/env python3
"""오리지널 영상 → 전사(transcript.json) — 증폭기의 'URL/영상 소스' 경로.

faster-whisper 로 문장 세그먼트(start/end/text)를 뽑는다. 이 타임코드가 쇼츠 자막·
하이라이트 선택의 근거가 된다. (대본 TTS 경로는 타이밍을 TTS가 직접 주므로 이 단계 불필요.)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def transcribe(src: "str|Path", *, model: str = "small", language: str = "ko",
               compute_type: str = "int8", initial_prompt: str = "") -> dict:
    from faster_whisper import WhisperModel

    m = WhisperModel(model, device="cpu", compute_type=compute_type)
    segs, info = m.transcribe(str(src), language=language, vad_filter=True,
                              initial_prompt=initial_prompt or None)
    out_segs = []
    for s in segs:
        t = (s.text or "").strip()
        if t:
            out_segs.append({"start": round(s.start, 3), "end": round(s.end, 3), "text": t})
    return {
        "source": str(src),
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(info.duration, 3) if getattr(info, "duration", None) else None,
        "segments": out_segs,
        "text": " ".join(s["text"] for s in out_segs),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="영상 → transcript.json (faster-whisper)")
    p.add_argument("src", type=Path)
    p.add_argument("--out", type=Path, default=Path("transcript.json"))
    p.add_argument("--model", default="small",
                   help="tiny/base/small/medium/large-v3 (CPU는 small 무난, 정확도↑는 medium)")
    p.add_argument("--language", default="ko")
    p.add_argument("--initial-prompt", default="", help="도메인 어휘 힌트(정확도↑)")
    a = p.parse_args()

    data = transcribe(a.src, model=a.model, language=a.language, initial_prompt=a.initial_prompt)
    a.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 전사: {a.out}  ({len(data['segments'])} segments, lang={data['language']} "
          f"p={data['language_probability']})")


if __name__ == "__main__":
    main()

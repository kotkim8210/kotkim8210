#!/usr/bin/env python3
"""로컬 한국어/영어 음성 내레이션 (edge-tts) + 문장 타이밍 추출.

핵심 설계(검증됨):
  - edge-tts 는 무료·API키 불필요·한국어 보이스 품질 우수.
  - 한국어는 ``SentenceBoundary`` 이벤트로 문장별 타이밍(offset/duration)을 준다.
    → 대본을 우리가 이미 알고 타이밍은 TTS가 주므로 **whisper 전사 불필요**.
  - TLS 가로채기 프록시(샌드박스/사내망) 환경: edge-tts(aiohttp)가 certifi 를
    하드코딩해 시스템 CA 를 못 본다 → 모듈 전역 ``_SSL_CTX`` 를 시스템 CA(또는
    ``SSL_CERT_FILE``) 컨텍스트로 교체해 통과시킨다(전역 certifi 변조 없이 깔끔).

오프라인/에어갭/네트워크 차단 환경에서는 ``--engine piper`` 폴백을 쓴다(piper 설치 시).

⚠️ 라이선스 주의(중요):
  edge-tts 는 Microsoft Edge 의 **온라인 읽어주기 서비스**를 호출한다 → 빠르고 한국어 품질이
  좋지만, MS 서비스 약관상 **상업적/대량 자동화 사용은 보장되지 않는다**(개인·프로토타입 권장).
  **판매용·상업 산출물**에는 MIT 라이선스 + 한국어 정식 지원 + CPU 실시간인 **MeloTTS** 로
  전환하라(영어 보강은 Apache-2.0 Kokoro-82M). 이 모듈은 그래서 ``engine`` 을 분리해 두었다:
  edge=빠른 프로토타입, piper=오프라인, (예정) melotts=상업 안전.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import ssl
from dataclasses import asdict, dataclass
from pathlib import Path

# 한국어 추천 보이스(성별/톤). 영어 등은 list-voices 로 확인.
KO_VOICES = {
    "female": "ko-KR-SunHiNeural",       # 밝고 또렷 — 정보/리뷰/하이라이트 내레이션 기본
    "male": "ko-KR-InJoonNeural",        # 안정적 남성 — 다큐/해설 톤
    "multi": "ko-KR-HyunsuMultilingualNeural",  # 다국어 혼용(영어 고유명사 섞일 때)
}
DEFAULT_VOICE = KO_VOICES["female"]


@dataclass
class Cue:
    start: float  # 초
    end: float    # 초
    text: str


def _system_ca() -> "str | None":
    """프록시를 신뢰하는 CA 번들 경로(없으면 None → 기본 certifi 사용)."""
    for p in (os.environ.get("SSL_CERT_FILE"),
              os.environ.get("REQUESTS_CA_BUNDLE"),
              "/etc/ssl/certs/ca-certificates.crt"):
        if p and Path(p).exists():
            return p
    return None


def _patch_edge_ssl() -> None:
    """edge-tts 의 하드코딩 SSL 컨텍스트를 시스템 CA 로 교체(프록시 통과)."""
    ca = _system_ca()
    if not ca:
        return
    try:
        import edge_tts.communicate as ec
        ec._SSL_CTX = ssl.create_default_context(cafile=ca)
    except Exception:
        pass  # edge-tts 미설치/구조변경 시 조용히 패스(기본 동작)


def _split_cue(text: str, start: float, end: float, max_chars: int) -> "list[Cue]":
    """긴 문장 cue 를 글자수 비례로 잘게 쪼갠다(가독성/체류율).

    단어 타임스탬프(깨진 글자·환청 유발) 대신 **문장 비례 분할** — video-editor 와 동일 원칙.
    """
    text = text.strip()
    if not text:
        return []
    if max_chars <= 0 or len(text) <= max_chars:
        return [Cue(start, end, text)]
    # 공백 우선으로 max_chars 근처에서 끊되, 한국어는 공백이 적어 글자수로 폴백.
    chunks: "list[str]" = []
    buf = ""
    for word in text.split(" "):
        cand = (buf + " " + word).strip()
        if len(cand) <= max_chars or not buf:
            buf = cand
        else:
            chunks.append(buf)
            buf = word
    if buf:
        chunks.append(buf)
    # 한 덩이가 여전히 너무 길면(공백 없는 한국어) 글자수로 강제 분할.
    flat: "list[str]" = []
    for c in chunks:
        while len(c) > max_chars:
            flat.append(c[:max_chars])
            c = c[max_chars:]
        if c:
            flat.append(c)
    total = sum(len(c) for c in flat) or 1
    out: "list[Cue]" = []
    t = start
    span = end - start
    for c in flat:
        dur = span * (len(c) / total)
        out.append(Cue(round(t, 3), round(t + dur, 3), c))
        t += dur
    if out:
        out[-1].end = round(end, 3)
    return out


async def _edge_synth(text: str, out_mp3: Path, *, voice: str, rate: str,
                      volume: str, pitch: str, max_chars: int) -> "list[Cue]":
    _patch_edge_ssl()
    import edge_tts

    comm = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
    cues_raw: "list[Cue]" = []
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    with open(out_mp3, "wb") as f:
        async for chunk in comm.stream():
            ct = chunk["type"]
            if ct == "audio":
                f.write(chunk["data"])
            elif ct in ("SentenceBoundary", "WordBoundary"):
                s = chunk["offset"] / 1e7            # 100ns → 초
                e = (chunk["offset"] + chunk["duration"]) / 1e7
                cues_raw.append(Cue(round(s, 3), round(e, 3), chunk["text"]))
    # 문장 cue 를 max_chars 로 분할(자막용).
    cues: "list[Cue]" = []
    for c in cues_raw:
        cues.extend(_split_cue(c.text, c.start, c.end, max_chars))
    return cues


def synthesize(text: str, out_mp3: "str | Path", *, voice: str = DEFAULT_VOICE,
               rate: str = "+0%", volume: str = "+0%", pitch: str = "+0Hz",
               max_chars: int = 18, engine: str = "edge") -> "list[Cue]":
    """대본을 음성(mp3)으로 합성하고, 자막용 cue 목록을 반환한다.

    Returns: [Cue(start, end, text), ...]  (초 단위, 자막 burn 에 그대로 사용)
    """
    out_mp3 = Path(out_mp3)
    if engine == "edge":
        return asyncio.run(_edge_synth(text, out_mp3, voice=voice, rate=rate,
                                       volume=volume, pitch=pitch, max_chars=max_chars))
    if engine == "piper":
        return _piper_synth(text, out_mp3, max_chars=max_chars)
    raise ValueError(f"알 수 없는 TTS 엔진: {engine}")


def _piper_synth(text: str, out_mp3: Path, *, max_chars: int) -> "list[Cue]":
    """오프라인 폴백(piper). piper 와 한국어 보이스 모델이 설치돼 있어야 한다.

    piper 는 단어 타이밍을 직접 주지 않으므로, 오디오 길이를 문장 글자수로 비례 배분한다.
    """
    import shutil
    import subprocess
    import wave

    if not shutil.which("piper"):
        raise RuntimeError(
            "오프라인 엔진 piper 가 없습니다. `pip install piper-tts` 후 한국어 보이스 모델을 "
            "받으세요(PIPER_VOICE 환경변수로 .onnx 경로 지정). 또는 --engine edge 를 쓰세요.")
    voice = os.environ.get("PIPER_VOICE", "")
    if not voice or not Path(voice).exists():
        raise RuntimeError("PIPER_VOICE 에 한국어 piper .onnx 모델 경로를 지정하세요.")
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    wav = out_mp3.with_suffix(".wav")
    subprocess.run(["piper", "--model", voice, "--output_file", str(wav)],
                   input=text.encode(), check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                    "-codec:a", "libmp3lame", "-q:a", "3", str(out_mp3)], check=True)
    with wave.open(str(wav)) as w:
        dur = w.getnframes() / float(w.getframerate())
    wav.unlink(missing_ok=True)
    # 문장 단위로 나눠 비례 배분(타임스탬프가 없으므로 근사).
    import re
    sents = [s for s in re.split(r"(?<=[.!?。])\s+", text.strip()) if s]
    cues: "list[Cue]" = []
    t = 0.0
    total = sum(len(s) for s in sents) or 1
    for s in sents:
        seg = dur * (len(s) / total)
        cues.extend(_split_cue(s, t, t + seg, max_chars))
        t += seg
    return cues


def cues_to_srt(cues: "list[Cue]") -> str:
    def ts(x: float) -> str:
        h = int(x // 3600); m = int((x % 3600) // 60)
        s = int(x % 60); ms = int(round((x - int(x)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    out = []
    for i, c in enumerate(cues, 1):
        out.append(f"{i}\n{ts(c.start)} --> {ts(c.end)}\n{c.text}\n")
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser(description="로컬 한국어 TTS 내레이션 + 문장 타이밍")
    p.add_argument("text", nargs="?", help="합성할 텍스트(생략 시 --file)")
    p.add_argument("--file", type=Path, help="텍스트 파일 입력")
    p.add_argument("--out", type=Path, default=Path("narration.mp3"))
    p.add_argument("--voice", default=DEFAULT_VOICE, help=f"보이스(기본 {DEFAULT_VOICE}). 키워드: female/male/multi")
    p.add_argument("--rate", default="+0%", help="말속도 예: +10% / -5%")
    p.add_argument("--volume", default="+0%")
    p.add_argument("--pitch", default="+0Hz")
    p.add_argument("--max-chars", type=int, default=18, help="자막 한 조각 최대 글자수")
    p.add_argument("--engine", default="edge", choices=["edge", "piper"])
    p.add_argument("--srt", type=Path, help="자막(SRT) 저장 경로")
    p.add_argument("--json", type=Path, help="cue JSON 저장 경로")
    a = p.parse_args()

    text = a.text or (a.file.read_text(encoding="utf-8") if a.file else None)
    if not text:
        p.error("text 또는 --file 이 필요합니다.")
    voice = KO_VOICES.get(a.voice, a.voice)

    cues = synthesize(text, a.out, voice=voice, rate=a.rate, volume=a.volume,
                      pitch=a.pitch, max_chars=a.max_chars, engine=a.engine)
    if a.srt:
        a.srt.write_text(cues_to_srt(cues), encoding="utf-8")
    if a.json:
        a.json.write_text(json.dumps([asdict(c) for c in cues], ensure_ascii=False, indent=2),
                          encoding="utf-8")
    dur = cues[-1].end if cues else 0
    print(f"✅ 음성: {a.out}  ({dur:.1f}s, {len(cues)} cues)")
    if a.srt:
        print(f"✅ 자막: {a.srt}")


if __name__ == "__main__":
    main()

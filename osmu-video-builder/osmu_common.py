#!/usr/bin/env python3
"""
osmu_common.py — 모든 모듈이 공유하는 설정 로더 + 경로 규칙.

자동화 핵심 ①: "lean config".
  예전엔 segment마다 image/audio 경로를 손으로 다 적어야 했다.
  이제는 id만 있으면 규칙으로 자동 유도한다:
      image -> assets/<id>.jpg
      audio -> assets/<id>.mp3
  그래서 대본 config는 id/text/caption 만 적으면 된다.

자동화 핵심 ②: 빠진 기본값(해상도/자막/voice)을 전부 채워서
  어떤 모듈이든 KeyError 없이 동작.
"""
import json
import os

DEFAULTS = {
    "out_dir": "out",
    "fps": 30,
    "longform_resolution": [1920, 1080],
    "clip_resolution": [1080, 1920],
    "images_per_segment": 1,   # 롱폼 화면 전환용. config에서 5~6 권장.
    "motion": True,            # 켄번즈(느린 줌/팬) on/off
}
DEFAULT_VOICE = {"backend": "files"}
DEFAULT_CAPTIONS = {
    "mode": "whisper", "model_size": "small", "device": "cpu",
    "compute_type": "int8", "language": "ko",
    "max_chars": 18, "max_gap": 0.6, "max_dur": 3.0, "vad": True,
}
DEFAULT_IMAGES = {"backend": "prompts"}  # prompts(기본) / openai / gemini


def config_root(path):
    return os.path.dirname(os.path.abspath(path))


def load_config(path):
    """config.json 로드 + 기본값/경로 규칙 주입."""
    cfg = json.load(open(path, encoding="utf-8"))
    for k, v in DEFAULTS.items():
        cfg.setdefault(k, v)
    cfg.setdefault("voice", dict(DEFAULT_VOICE))
    # captions/images는 부분 지정도 허용 → 빠진 키만 보강
    cfg["captions"] = {**DEFAULT_CAPTIONS, **cfg.get("captions", {})}
    cfg["images"] = {**DEFAULT_IMAGES, **cfg.get("images", {})}
    for s in cfg.get("segments", []):
        sid = s["id"]
        s.setdefault("image", f"assets/{sid}.jpg")
        s.setdefault("audio", f"assets/{sid}.mp3")
    return cfg


def segment_images(seg, cfg):
    """세그먼트가 쓸 이미지 파일 목록(롱폼 화면 전환용).
    우선순위: segment.images(직접 목록) > n장 규칙(s{id}_1..N) > 단일 image.
    promptgen·build·auto·handoff 가 모두 이걸 써서 파일명이 일치한다.
    """
    if seg.get("images"):
        return seg["images"]
    n = seg.get("n_images") or cfg.get("images_per_segment", 1) or 1
    if n > 1:
        return [f"assets/{seg['id']}_{i}.jpg" for i in range(1, n + 1)]
    return [seg.get("image", f"assets/{seg['id']}.jpg")]


def resolve(root, p):
    """root 기준 절대경로."""
    if not p:
        return None
    return p if os.path.isabs(p) else os.path.join(root, p)


def narration(seg):
    """음성 합성에 쓸 텍스트: tts_text(있으면) 우선, 없으면 text."""
    return seg.get("tts_text") or seg.get("text", "")


def total_chars(cfg):
    return sum(len(s.get("text", "")) for s in cfg.get("segments", []))

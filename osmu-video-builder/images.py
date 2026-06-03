#!/usr/bin/env python3
"""
images.py — (선택) 배경 이미지 '자동 생성' 백엔드.

기본값은 backend="prompts": 아무것도 생성하지 않고 promptgen이 뽑은 프롬프트를
사람이 ChatGPT/ImageFX에 붙여 만든다(대화에서 정한 분업, 무비용).

나중에 완전 자동화를 원하면 config의 images.backend 만 바꾸면 된다:
  images: { "backend": "openai", "model": "gpt-image-1", "size": "1792x1024" }
  → assets/<id>.jpg 가 없으면 프롬프트로 자동 생성해서 채운다(있으면 건너뜀=idempotent).
  필요: 환경변수 OPENAI_API_KEY, pip install openai

이미지 '생성'은 약점 영역이라 기본 OFF. 켜도 발행 전 사람 눈 점검은 필수(시대·소품 고증).
"""
import base64
import os

from osmu_common import resolve


def ensure_images(cfg, root, prompts_by_id, force=False):
    """빠진 이미지를 backend에 따라 생성. 생성한 id 리스트 반환."""
    backend = cfg.get("images", {}).get("backend", "prompts")
    if backend == "prompts":
        return []
    made = []
    for seg in cfg["segments"]:
        sid = seg["id"]
        target = resolve(root, seg["image"])
        if os.path.exists(target) and not force:
            continue
        prompt = prompts_by_id.get(sid, {}).get("prompt_en", seg.get("text", ""))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if backend == "openai":
            _openai(prompt, target, cfg["images"])
        elif backend == "gemini":
            _gemini(prompt, target, cfg["images"])
        else:
            raise ValueError(f"알 수 없는 images.backend: {backend}")
        made.append(sid)
    return made


def _openai(prompt, target, icfg):
    from openai import OpenAI  # pip install openai
    client = OpenAI()  # OPENAI_API_KEY 환경변수
    r = client.images.generate(
        model=icfg.get("model", "gpt-image-1"),
        prompt=prompt,
        size=icfg.get("size", "1792x1024"),
    )
    data = base64.b64decode(r.data[0].b64_json)
    with open(target, "wb") as f:
        f.write(data)


def _gemini(prompt, target, icfg):
    from google import genai  # pip install google-genai
    client = genai.Client()  # GEMINI_API_KEY 환경변수
    r = client.models.generate_images(
        model=icfg.get("model", "imagen-3.0-generate-002"),
        prompt=prompt,
    )
    r.generated_images[0].image.save(target)

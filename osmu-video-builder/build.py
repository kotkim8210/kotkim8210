#!/usr/bin/env python3
"""
build.py (v4) — OSMU 영상 조립 + Whisper 동기화 자막 + 다중 이미지/켄번즈.

흐름: 대본(config.json) → 세그먼트별 음성(voice.py) → [선택] Whisper 단어 타임스탬프
  → 음성 길이에 맞춰 조립 → 본편(16:9) + OSMU 클립(9:16), 자막 번인.

v4 변경(롱폼 화면 죽음 방지):
  - 세그먼트당 이미지 N장(osmu_common.segment_images) → 음성 길이를 N장에 균등 분배.
  - 켄번즈(느린 줌/팬) 모션 — 정지 이미지도 살아 움직임. config.motion=false면 끔.
  - 음성 합성에 tts_text(있으면) 우선.

자막 모드(config.captions.mode): "whisper" / "static"
사용:  python build.py config.json
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (ImageClip, AudioFileClip, CompositeVideoClip,
                     concatenate_videoclips)

import voice as voicemod
from osmu_common import config_root, load_config, resolve, narration, segment_images


def cover_fit(img_path, size):
    W, H = size
    im = Image.open(img_path).convert("RGB")
    iw, ih = im.size
    s = max(W / iw, H / ih)
    nw, nh = int(iw * s + 0.5), int(ih * s + 0.5)
    im = im.resize((nw, nh), Image.LANCZOS)
    l, t = (nw - W) // 2, (nh - H) // 2
    return np.array(im.crop((l, t, l + W, t + H)))


def ken_burns(arr, size, dur, idx=0, zoom=0.10, motion=True):
    """정지 이미지에 느린 줌(켄번즈). idx 짝/홀로 줌인/줌아웃 번갈아 → 단조로움 방지."""
    base = ImageClip(arr).with_duration(dur)
    if not motion or dur <= 0.05:
        return base
    z0, z1 = (1.0, 1.0 + zoom) if idx % 2 == 0 else (1.0 + zoom, 1.0)
    moving = base.resized(lambda t: z0 + (z1 - z0) * (min(t, dur) / dur))
    return CompositeVideoClip([moving.with_position("center")],
                              size=size).with_duration(dur)


def _wrap(text, font, max_w):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for token in para.split(" "):
            pieces = [token]
            if font.getlength(token) > max_w:
                pieces, buf = [], ""
                for ch in token:
                    if font.getlength(buf + ch) <= max_w:
                        buf += ch
                    else:
                        pieces.append(buf)
                        buf = ch
                if buf:
                    pieces.append(buf)
            for p in pieces:
                cand = (cur + " " + p).strip()
                if font.getlength(cand) <= max_w:
                    cur = cand
                else:
                    if cur:
                        lines.append(cur)
                    cur = p
        lines.append(cur)
    return lines


def render_caption(text, box_w, font_path, font_size, pad=26,
                   fg=(255, 255, 255, 255), box=(0, 0, 0, 150), stroke=0):
    font = ImageFont.truetype(font_path, font_size)
    inner = box_w - 2 * pad
    lines = _wrap(text, font, inner)
    asc, desc = font.getmetrics()
    lh = asc + desc + 10
    H = pad * 2 + lh * len(lines)
    img = Image.new("RGBA", (box_w, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if box[3] > 0:
        d.rounded_rectangle([0, 0, box_w - 1, H - 1], radius=20, fill=box)
    y = pad
    for ln in lines:
        w = font.getlength(ln)
        x = (box_w - w) / 2
        if stroke:
            d.text((x, y), ln, font=font, fill=fg,
                   stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
        else:
            d.text((x, y), ln, font=font, fill=fg)
        y += lh
    return np.array(img)


def _rgba_clip(arr, dur, start=0.0):
    rgb = arr[:, :, :3]
    mask = ImageClip(arr[:, :, 3] / 255.0, is_mask=True).with_duration(dur)
    return ImageClip(rgb).with_duration(dur).with_mask(mask).with_start(start)


def build_segment(A, size, font, margin, cap_size, cap_mode,
                  cap_cfg, hook=None, hook_size=None, motion=True):
    # 배경: 세그먼트 음성 길이를 이미지 N장에 균등 분배 + 켄번즈
    imgs = A["images"]
    per = A["dur"] / len(imgs)
    bg_parts = [ken_burns(cover_fit(img, size), size, per, i, motion=motion)
                for i, img in enumerate(imgs)]
    bg = concatenate_videoclips(bg_parts, method="compose").with_duration(A["dur"])
    layers = [bg]
    if hook:
        h = render_caption(hook, size[0] - 2 * margin, font, hook_size,
                           box=(0, 0, 0, 170))
        layers.append(_rgba_clip(h, A["dur"]).with_position(("center", margin)))
    if cap_mode == "whisper" and A.get("chunks"):
        for ck in A["chunks"]:
            dur = max(0.3, ck["end"] - ck["start"])
            arr = render_caption(ck["text"], size[0] - 2 * margin, font,
                                 cap_size, box=(0, 0, 0, 0), stroke=4)
            layers.append(_rgba_clip(arr, dur, start=ck["start"]).with_position(
                ("center", size[1] - arr.shape[0] - margin)))
    elif A.get("caption"):
        arr = render_caption(A["caption"], size[0] - 2 * margin, font, cap_size)
        layers.append(_rgba_clip(arr, A["dur"]).with_position(
            ("center", size[1] - arr.shape[0] - margin)))
    return CompositeVideoClip(layers, size=size).with_duration(
        A["dur"]).with_audio(AudioFileClip(A["audio"]))


def main(cfg_path):
    cfg = load_config(cfg_path)
    root = config_root(cfg_path)
    out_dir = os.path.join(root, cfg.get("out_dir", "out"))
    work = os.path.join(out_dir, "_audio")
    os.makedirs(work, exist_ok=True)
    font = cfg.get("font", os.path.join(root, "NanumGothic.ttf"))
    fps = cfg.get("fps", 30)
    motion = cfg.get("motion", True)
    vcfg = cfg["voice"]
    cap_conf = cfg.get("captions", {"mode": "static"})
    cap_mode = cap_conf.get("mode", "static")
    if cap_mode == "whisper":
        import captions as capmod

    seg_assets = {}
    for seg in cfg["segments"]:
        ap = os.path.join(work, f"{seg['id']}.mp3")
        seg_audio = resolve(root, seg["audio"]) if seg.get("audio") else None
        voicemod.synth(narration(seg), ap, vcfg, segment_audio=seg_audio)
        dur = AudioFileClip(ap).duration
        chunks = None
        imgs = [resolve(root, p) for p in segment_images(seg, cfg)]
        if cap_mode == "whisper":
            chunks = capmod.whisper_chunks(ap, cap_conf)
            print(f"  - {seg['id']}: {dur:.1f}s, imgs {len(imgs)}, captions {len(chunks)} chunks")
        else:
            print(f"  - {seg['id']}: {dur:.1f}s, imgs {len(imgs)}")
        seg_assets[seg["id"]] = dict(
            audio=ap, dur=dur, images=imgs,
            caption=seg.get("caption", ""), chunks=chunks)

    LF = tuple(cfg.get("longform_resolution", [1920, 1080]))
    lf = concatenate_videoclips(
        [build_segment(seg_assets[s["id"]], LF, font, 60, 48, cap_mode, cap_conf,
                       motion=motion)
         for s in cfg["segments"]], method="compose")
    lf_path = os.path.join(out_dir, "longform.mp4")
    lf.write_videofile(lf_path, fps=fps, codec="libx264", audio_codec="aac",
                       logger=None)
    dur_min = lf.duration / 60
    print(f"[LONGFORM] {lf_path}  ({lf.duration:.0f}s = {dur_min:.1f}min)")
    if dur_min < 10:
        print("  WARNING: under 10min (midroll ads need >8min). Extend the script.")

    CL = tuple(cfg.get("clip_resolution", [1080, 1920]))
    for clip in cfg.get("clips", []):
        parts = [build_segment(seg_assets[sid], CL, font, 70, 50, cap_mode,
                               cap_conf, hook=clip.get("hook"), hook_size=66,
                               motion=motion)
                 for sid in clip["from_segments"]]
        cv = concatenate_videoclips(parts, method="compose")
        cp = os.path.join(out_dir, f"clip_{clip['name']}.mp4")
        cv.write_videofile(cp, fps=fps, codec="libx264", audio_codec="aac",
                           logger=None)
        print(f"[CLIP] {cp}  ({cv.duration:.0f}s)")
    print("done.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python build.py config.json")
        sys.exit(1)
    main(sys.argv[1])

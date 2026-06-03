#!/usr/bin/env python3
"""
build.py (v3) — OSMU 영상 조립 + Whisper 동기화 자막.

흐름: 대본(config.json) → 세그먼트별 음성(voice.py) → [선택] Whisper 단어 타임스탬프
  → 음성 길이에 맞춰 조립 → 본편(16:9) + OSMU 클립(9:16), 자막 번인.

v3 변경(자동화):
  - osmu_common.load_config 사용 → image/audio 경로 자동 유도(lean config).
  - 음성 합성에 tts_text(있으면) 우선 사용 → ttsfix 결과가 자동 반영.

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
from osmu_common import config_root, load_config, resolve, narration


def cover_fit(img_path, size):
    W, H = size
    im = Image.open(img_path).convert("RGB")
    iw, ih = im.size
    s = max(W / iw, H / ih)
    nw, nh = int(iw * s + 0.5), int(ih * s + 0.5)
    im = im.resize((nw, nh), Image.LANCZOS)
    l, t = (nw - W) // 2, (nh - H) // 2
    return np.array(im.crop((l, t, l + W, t + H)))


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
                  cap_cfg, hook=None, hook_size=None):
    base = ImageClip(cover_fit(A["image"], size)).with_duration(A["dur"])
    layers = [base]
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
    return CompositeVideoClip(layers, size=size).with_audio(
        AudioFileClip(A["audio"]))


def main(cfg_path):
    cfg = load_config(cfg_path)
    root = config_root(cfg_path)
    out_dir = os.path.join(root, cfg.get("out_dir", "out"))
    work = os.path.join(out_dir, "_audio")
    os.makedirs(work, exist_ok=True)
    font = cfg.get("font", os.path.join(root, "NanumGothic.ttf"))
    fps = cfg.get("fps", 30)
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
        if cap_mode == "whisper":
            chunks = capmod.whisper_chunks(ap, cap_conf)
            print(f"  - {seg['id']}: {dur:.1f}s, captions {len(chunks)} chunks")
        else:
            print(f"  - {seg['id']}: {dur:.1f}s")
        seg_assets[seg["id"]] = dict(
            audio=ap, dur=dur, image=resolve(root, seg["image"]),
            caption=seg.get("caption", ""), chunks=chunks)

    LF = tuple(cfg.get("longform_resolution", [1920, 1080]))
    lf = concatenate_videoclips(
        [build_segment(seg_assets[s["id"]], LF, font, 60, 48, cap_mode, cap_conf)
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
                               cap_conf, hook=clip.get("hook"), hook_size=66)
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

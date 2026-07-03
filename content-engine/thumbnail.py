#!/usr/bin/env python3
"""유튜브 썸네일 렌더러 (1280×720) — 프레임 추출 + 대비 게이트 + 한글 타이틀.

검증된 CTR 원칙: 큰 글자(소수 단어)·강한 대비·핵심 키워드 강조. 320×180 으로 줄여도
읽히게(모바일 피드). 영상 프레임 위에 어둡게 깔고 큰 타이틀을 얹는다.
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
W, H = 1280, 720
FONT_BOLD = ASSETS / "GmarketSansTTFBold.ttf"
ACCENT = (255, 140, 66)


def _grab_frame(src: Path, ts: float) -> Image.Image:
    tmp = Path(tempfile.mktemp(suffix=".png"))
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-ss", str(ts), "-i", str(src), "-frames:v", "1", str(tmp)], check=True)
    img = Image.open(tmp).convert("RGB")
    tmp.unlink(missing_ok=True)
    return img


def _cover(img: Image.Image) -> Image.Image:
    iw, ih = img.size
    scale = max(W / iw, H / ih)
    img = img.resize((int(iw * scale), int(ih * scale)), Image.LANCZOS)
    x = (img.width - W) // 2; y = (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def _wrap(draw, text, font, max_w):
    lines, buf = [], ""
    for w in text.replace("\n", " ").split(" "):
        cand = (buf + " " + w).strip()
        if draw.textlength(cand, font=font) <= max_w or not buf:
            buf = cand
        else:
            lines.append(buf); buf = w
    if buf:
        lines.append(buf)
    return lines


def render(src: "str|Path", title: str, out: "str|Path", *, ts: float = 1.0,
           bg_image: "str|Path|None" = None, accent_word: str = "") -> Path:
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    if bg_image:
        base = Image.open(bg_image).convert("RGB")
    else:
        base = _grab_frame(Path(src), ts)
    img = _cover(base)

    # 대비 게이트: 하단 강한 어둠 그라디언트(텍스트 가독성).
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for yy in range(H):
        a = int(235 * max(0, (yy - H * 0.30) / (H * 0.70)))  # 위→아래로 짙어짐
        od.line([(0, yy), (W, yy)], fill=(8, 9, 12, min(a, 225)))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    # 좌측 강조 바
    draw.rectangle([0, 0, 16, H], fill=ACCENT)

    # 타이틀 자동 크기(2~3줄에 맞게)
    size = 110
    while size > 52:
        font = ImageFont.truetype(str(FONT_BOLD), size)
        lines = _wrap(draw, title, font, W - 130)
        asc, desc = font.getmetrics()
        lh = asc + desc + 14
        if len(lines) <= 3 and len(lines) * lh <= H * 0.5:
            break
        size -= 6

    y = H - 70 - len(lines) * lh
    for ln in lines:
        # 강조 단어 색 분리(간단: 줄 전체 흰색, accent_word 포함 줄은 주황)
        fill = ACCENT if accent_word and accent_word in ln else (248, 249, 250)
        # 외곽선(가독성)
        for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2)]:
            draw.text((64 + dx, y + dy), ln, font=font, fill=(0, 0, 0))
        draw.text((64, y), ln, font=font, fill=fill)
        y += lh

    img.save(out, "PNG")
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="유튜브 썸네일(1280×720)")
    p.add_argument("src", type=Path, help="영상 파일(프레임 추출) 또는 --bg-image")
    p.add_argument("--title", required=True)
    p.add_argument("--out", type=Path, default=Path("thumbnail.png"))
    p.add_argument("--ts", type=float, default=1.0, help="프레임 추출 시점(초)")
    p.add_argument("--accent-word", default="", help="주황으로 강조할 단어")
    p.add_argument("--bg-image", type=Path, default=None)
    a = p.parse_args()
    out = render(a.src, a.title, a.out, ts=a.ts, bg_image=a.bg_image, accent_word=a.accent_word)
    print(f"✅ 썸네일: {out}")


if __name__ == "__main__":
    main()

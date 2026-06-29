#!/usr/bin/env python3
"""인스타그램 캐러셀 슬라이드 렌더러 (4:5, 1080×1350).

검증된 플랫폼 규칙: 캐러셀은 4:5 가 표준, **첫 슬라이드 비율이 전체를 강제**하므로
모든 슬라이드를 1080×1350 으로 고정. 8~10장 권장(스와이프·체류시간이 보상 신호).
1장=훅, 2장=재노출 훅(2-hook), 마지막=저장 유도 CTA.

입력 JSON 예:
{
  "handle": "@my_channel",
  "cover":  {"title": "상세페이지 전환율\\n색상이 50%다", "subtitle": "디자인 초보가 가장 많이 틀리는 것"},
  "slides": [{"heading": "왜 색상인가", "body": "본문..."}, ...],
  "outro":  {"title": "저장해두고\\n그대로 따라하세요", "cta": "팔로우하면 더 많은 팁"}
}
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
W, H = 1080, 1350
PAD = 92

# 색상(다크 프리미엄 + 주황 강조 — 레포 톤과 통일)
BG = (18, 20, 24)
FG = (245, 246, 248)
SUB = (170, 176, 184)
ACCENT = (255, 140, 66)  # #FF8C42

FONT_BOLD = ASSETS / "GmarketSansTTFBold.ttf"
FONT_MED = ASSETS / "GmarketSansTTFMedium.ttf"
FONT_BODY = Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
if not FONT_BODY.exists():
    FONT_BODY = FONT_MED  # 폴백


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
          max_w: int) -> "list[str]":
    """측정 기반 줄바꿈(한국어=공백 적어 글자단위 폴백 포함). \\n 은 강제 개행."""
    lines: "list[str]" = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append("")
            continue
        words = para.split(" ")
        buf = ""
        for w in words:
            cand = (buf + " " + w).strip()
            if draw.textlength(cand, font=font) <= max_w or not buf:
                # 단어 자체가 너무 길면 글자단위로 쪼갬
                if draw.textlength(cand, font=font) > max_w and not buf:
                    cur = ""
                    for ch in cand:
                        if draw.textlength(cur + ch, font=font) <= max_w:
                            cur += ch
                        else:
                            lines.append(cur); cur = ch
                    buf = cur
                else:
                    buf = cand
            else:
                lines.append(buf); buf = w
        if buf:
            lines.append(buf)
    return lines


def _draw_block(draw, text, font, x, y, max_w, fill, line_gap):
    for ln in _wrap(draw, text, font, max_w):
        draw.text((x, y), ln, font=font, fill=fill)
        asc, desc = font.getmetrics()
        y += asc + desc + line_gap
    return y


def _base() -> "tuple[Image.Image, ImageDraw.ImageDraw]":
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def _badge(draw, text: str, y: int = PAD):
    f = _font(FONT_BOLD, 30)
    tw = draw.textlength(text, font=f)
    draw.rounded_rectangle([PAD, y, PAD + tw + 36, y + 50], radius=12, fill=ACCENT)
    draw.text((PAD + 18, y + 8), text, font=f, fill=(20, 20, 20))


def _handle(draw, handle: str):
    f = _font(FONT_MED, 30)
    draw.line([PAD, H - PAD - 8, PAD + 70, H - PAD - 8], fill=ACCENT, width=5)
    draw.text((PAD, H - PAD + 6), handle, font=f, fill=SUB)


def render(data: dict, outdir: "str|Path") -> "list[Path]":
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    handle = data.get("handle", "")
    pages: "list[dict]" = []
    pages.append({"kind": "cover", **data.get("cover", {})})
    for s in data.get("slides", []):
        pages.append({"kind": "slide", **s})
    if data.get("outro"):
        pages.append({"kind": "outro", **data["outro"]})
    total = len(pages)

    paths: "list[Path]" = []
    for i, pg in enumerate(pages, 1):
        img, draw = _base()
        if pg["kind"] == "cover":
            _badge(draw, "SAVE 저장각", PAD)
            y = int(H * 0.30)
            y = _draw_block(draw, pg.get("title", ""), _font(FONT_BOLD, 84),
                            PAD, y, W - 2 * PAD, FG, 12)
            if pg.get("subtitle"):
                y += 24
                _draw_block(draw, pg["subtitle"], _font(FONT_MED, 40),
                            PAD, y, W - 2 * PAD, ACCENT, 8)
            draw.text((PAD, H - PAD - 60), "넘겨보세요  →", font=_font(FONT_BOLD, 38), fill=SUB)
        elif pg["kind"] == "outro":
            _badge(draw, "DONE", PAD)
            y = int(H * 0.30)
            y = _draw_block(draw, pg.get("title", ""), _font(FONT_BOLD, 76),
                            PAD, y, W - 2 * PAD, FG, 12)
            if pg.get("cta"):
                y += 30
                draw.rounded_rectangle([PAD, y, W - PAD, y + 110], radius=20, outline=ACCENT, width=4)
                cf = _font(FONT_BOLD, 40)
                cw = draw.textlength(pg["cta"], font=cf)
                draw.text(((W - cw) / 2, y + 32), pg["cta"], font=cf, fill=ACCENT)
        else:
            _badge(draw, f"{i-1:02d} / {total-2:02d}", PAD)
            y = PAD + 110
            y = _draw_block(draw, pg.get("heading", ""), _font(FONT_BOLD, 60),
                            PAD, y, W - 2 * PAD, FG, 8)
            y += 28
            _draw_block(draw, pg.get("body", ""), _font(FONT_BODY, 44),
                        PAD, y, W - 2 * PAD, (220, 224, 230), 16)
        _handle(draw, handle)
        out = outdir / f"slide_{i:02d}.png"
        img.save(out, "PNG")
        paths.append(out)
    return paths


def main() -> None:
    p = argparse.ArgumentParser(description="인스타 캐러셀 렌더(4:5 1080×1350)")
    p.add_argument("json", type=Path, help="캐러셀 정의 JSON")
    p.add_argument("--outdir", type=Path, default=Path("carousel"))
    a = p.parse_args()
    data = json.loads(a.json.read_text(encoding="utf-8"))
    paths = render(data, a.outdir)
    print(f"✅ 캐러셀 {len(paths)}장 → {a.outdir}")


if __name__ == "__main__":
    main()

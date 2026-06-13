#!/usr/bin/env python3
"""
promptgen.py — 대본(config.json) → 세그먼트별 '이미지 생성 프롬프트' 자동 추출.

주제 인식형(topic-aware). 우선순위(높을수록 먼저):
  1) segment.image_prompt  — 그 장면 영문 프롬프트를 직접 지정(완전 수동).
  2) segment.image_hint    — 짧은 장면 힌트(영/한) → 그대로 장면으로 사용(반자동, 추천).
  3) config.image_style.motifs — [{ "kw": "정규식", "scene": "영문장면" }, ...] 키워드 매칭.
  4) 내장 MOTIFS           — 기본(역사·유럽 버블) 폴백.

config.image_style 로 채널/주제별 톤을 한 곳에서 조정:
  {
    "suffix": "1980s Japan, Tokyo, Showa-era, no European elements",  // 모든 컷에 시대·장소 앵커
    "base": "...스타일 문장...",        // 생략 시 기본 시네마틱 다큐 스타일
    "people_guard": "...",              // 인물 회피 가드 override
    "negative": "...",                  // negative override
    "motifs": [ {"kw": "환율|플라자", "scene": "..."} ],
    "default_motif": "..."
  }
사용:  python promptgen.py config.json [--ar 9x16]
"""
import json
import os
import re
import sys

from osmu_common import config_root, load_config

DEFAULT_STYLE = ("cinematic documentary still, moody dramatic lighting, muted desaturated "
                 "color grade, fine film grain, shallow depth of field, painterly historical "
                 "atmosphere, no text, no watermark, no on-screen captions")
DEFAULT_GUARD = ("no recognizable real person, no celebrity likeness, faces hidden or "
                 "turned away or silhouetted")
DEFAULT_NEG = ("text, letters, watermark, logo, modern objects, smartphone, car, "
               "deformed hands, extra fingers, lowres, jpeg artifacts")

# 내장 모티프(역사·유럽 버블) — config.image_style.motifs 없을 때만 사용
BUILTIN_MOTIFS = [
    (r"거짓말|신화|전설|착각|오해|진짜", "an old leather-bound history book half-open in dim candlelight, dust motes in a single shaft of light"),
    (r"튤립|구근|줄무늬|바이러스|꽃잎", "a single dramatic striped tulip in a dark Dutch still-life style, deep shadows, 17th-century oil painting mood"),
    (r"계약|선물|레버리지|2\.5|종이|문서|구근의", "antique parchment contracts and a quill on a wooden merchant's desk, candlelight, 17th-century Amsterdam"),
    (r"기대|군중|광풍|열풍|모두|비싸게", "a crowded 17th-century Dutch tavern marketplace, blurred crowd, tense speculative atmosphere, lantern light"),
    (r"붕괴|폭락|무너|추락|크래시|떨어|사라|한 줌|방아쇠", "a shattered glass and a collapsing house of cards on a dark table, dramatic chiaroscuro, sense of sudden ruin"),
    (r"심리|자만|확신|편향|탐욕|비웃|다르다", "a lone figure silhouetted before a vast dark sky, small against towering clouds, contemplative and ominous"),
    (r"교훈|반복|패턴|순간|신호", "an antique hourglass and old coins on weathered parchment, candlelit, symbolic of time and value"),
    (r"예고|뉴턴|남해|구독|항해|다음 편", "a dramatic stormy sea with a distant 18th-century sailing ship, dark clouds, foreboding cinematic wide shot"),
]
DEFAULT_MOTIF = ("a symbolic still life with candlelight and deep shadows, evocative and cinematic")
AR = {"16x9": "--ar 16:9", "9x16": "--ar 9:16"}
AR_WORD = {"16x9": "wide cinematic 16:9 composition",
           "9x16": "vertical 9:16 composition, subject centered with headroom"}


def get_motifs(style):
    """config.image_style.motifs 가 있으면 (정규식, 장면) 리스트로, 없으면 내장."""
    m = style.get("motifs")
    if m:
        return [(item["kw"], item["scene"]) for item in m]
    return BUILTIN_MOTIFS


def motif_for(text, caption, motifs, default_motif):
    best, best_score = default_motif, 0
    for pat, scene in motifs:
        score = 0
        if caption and re.search(pat, caption):
            score += 3
        if re.search(pat, text):
            score += 1
        if score > best_score:
            best, best_score = scene, score
    return best


def scene_for(seg, style, motifs, default_motif):
    """우선순위에 따라 이 세그먼트의 '장면' 결정."""
    if seg.get("image_prompt"):
        return seg["image_prompt"], "image_prompt(직접지정)"
    if seg.get("image_hint"):
        return seg["image_hint"], "image_hint(힌트)"
    return motif_for(seg.get("text", ""), seg.get("caption", ""), motifs, default_motif), "자동추론"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ar = "16x9"
    if "--ar" in sys.argv:
        ar = sys.argv[sys.argv.index("--ar") + 1]
    cfg_path = args[0]
    root = config_root(cfg_path)
    cfg = load_config(cfg_path)

    style = cfg.get("image_style", {})
    STYLE = style.get("base", DEFAULT_STYLE)
    GUARD = style.get("people_guard", DEFAULT_GUARD)
    NEG = style.get("negative", DEFAULT_NEG)
    SUFFIX = style.get("suffix", "")
    motifs = get_motifs(style)
    default_motif = style.get("default_motif", DEFAULT_MOTIF)

    out_json, manifest = {}, []
    md = ["# 이미지 생성 프롬프트 (자동 생성)\n",
          f"> 비율: {ar}" + (f" · 시대/장소 앵커: {SUFFIX}" if SUFFIX else "") + " · 사람 얼굴 없음(초상권 회피)\n",
          "> ChatGPT/미드저니/ImageFX에 prompt_en 또는 midjourney 줄을 붙여넣고,\n",
          "> 나온 이미지를 각 항목의 파일명 그대로 저장하세요.\n"]
    for seg in cfg["segments"]:
        sid = seg["id"]
        target = seg.get("image", f"assets/{sid}.jpg")
        scene, src = scene_for(seg, style, motifs, default_motif)
        parts = [scene]
        if SUFFIX:
            parts.append(SUFFIX)
        parts += [AR_WORD[ar], STYLE, GUARD]
        en = ", ".join(parts)
        p = {"prompt_en": en, "negative": NEG,
             "midjourney": f"{en} {AR[ar]} --style raw --v 6",
             "note_ko": f"장면 출처: {src}"}
        out_json[sid] = p
        manifest.append({"id": sid, "save_as": target, "prompt": en})
        md += [f"\n## {sid}  → 저장 파일명: `{target}`  ({src})",
               f"- **EN**: {en}",
               f"- **MJ**: `{p['midjourney']}`",
               f"- **negative**: {NEG}"]

    json.dump(out_json, open(os.path.join(root, f"image_prompts.{ar}.json"), "w",
              encoding="utf-8"), ensure_ascii=False, indent=2)
    open(os.path.join(root, f"image_prompts.{ar}.md"), "w",
         encoding="utf-8").write("\n".join(md))
    if ar == "16x9":
        json.dump(manifest, open(os.path.join(root, "image_manifest.json"), "w",
                  encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"promptgen: {len(out_json)} prompts (ar={ar}) -> image_prompts.{ar}.md")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python promptgen.py config.json [--ar 9x16]")
        sys.exit(1)
    main()

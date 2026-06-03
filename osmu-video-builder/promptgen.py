#!/usr/bin/env python3
"""
promptgen.py — 대본(config.json) → 세그먼트별 '이미지 생성 프롬프트' 자동 추출.

ChatGPT/미드저니/ImageFX에 붙여넣을 영문 프롬프트를 세그먼트마다 생성.
자동화 개선:
  - --ar 별로 파일을 따로 저장(image_prompts.16x9.md / image_prompts.9x16.md) → 덮어쓰기 충돌 없음.
  - image_manifest.json 생성: "이 프롬프트 → 이 파일명(assets/sN.jpg)" 매핑.
    사람은 만든 이미지를 적힌 파일명 그대로 저장만 하면 끝(이름 헷갈릴 일 없음).
"""
import json
import os
import re
import sys

from osmu_common import config_root, load_config

STYLE = ("cinematic documentary still, moody dramatic lighting, muted desaturated "
         "color grade, fine film grain, shallow depth of field, painterly historical "
         "atmosphere, no text, no watermark, no on-screen captions")
PEOPLE_GUARD = ("no recognizable real person, no celebrity likeness, faces hidden or "
                "turned away or silhouetted")
NEG = ("text, letters, watermark, logo, modern objects, smartphone, car, "
       "deformed hands, extra fingers, lowres, jpeg artifacts")

MOTIFS = [
    (r"거짓말|신화|전설|착각|오해|진짜", "an old leather-bound history book half-open in dim candlelight, dust motes in a single shaft of light"),
    (r"튤립|구근|줄무늬|바이러스|꽃잎", "a single dramatic striped tulip in a dark Dutch still-life style, deep shadows, 17th-century oil painting mood"),
    (r"계약|선물|레버리지|2\.5|종이|문서|구근의", "antique parchment contracts and a quill on a wooden merchant's desk, candlelight, 17th-century Amsterdam"),
    (r"기대|군중|광풍|열풍|모두|비싸게", "a crowded 17th-century Dutch tavern marketplace, blurred crowd, tense speculative atmosphere, lantern light"),
    (r"붕괴|폭락|무너|추락|크래시|떨어|사라|한 줌|방아쇠", "a shattered glass and a collapsing house of cards on a dark table, dramatic chiaroscuro, sense of sudden ruin"),
    (r"심리|자만|확신|편향|탐욕|비웃|다르다", "a lone figure silhouetted before a vast dark sky, small against towering clouds, contemplative and ominous"),
    (r"교훈|반복|패턴|순간|신호", "an antique hourglass and old coins on weathered parchment, candlelit, symbolic of time and value"),
    (r"예고|뉴턴|남해|구독|항해|다음 편", "a dramatic stormy sea with a distant 18th-century sailing ship, dark clouds, foreboding cinematic wide shot"),
]
DEFAULT_MOTIF = ("a symbolic historical still life with candlelight and deep shadows, "
                 "evocative and cinematic")
AR = {"16x9": "--ar 16:9", "9x16": "--ar 9:16"}
AR_WORD = {"16x9": "wide cinematic 16:9 composition",
           "9x16": "vertical 9:16 composition, subject centered with headroom"}


def motif_for(text, caption):
    best, best_score = DEFAULT_MOTIF, 0
    for pat, motif in MOTIFS:
        score = 0
        if caption and re.search(pat, caption):
            score += 3
        if re.search(pat, text):
            score += 1
        if score > best_score:
            best, best_score = motif, score
    return best


def build_prompt(text, caption, ar):
    motif = motif_for(text, caption)
    en = f"{motif}, {AR_WORD[ar]}, {STYLE}, {PEOPLE_GUARD}"
    return {
        "prompt_en": en,
        "negative": NEG,
        "midjourney": f"{en} {AR[ar]} --style raw --v 6",
        "note_ko": f"장면 모티프 자동추론: '{caption.splitlines()[0] if caption else text[:20]}' → 필요시 1줄 수정",
    }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ar = "16x9"
    if "--ar" in sys.argv:
        ar = sys.argv[sys.argv.index("--ar") + 1]
    cfg_path = args[0]
    root = config_root(cfg_path)
    cfg = load_config(cfg_path)

    out_json, manifest = {}, []
    md = ["# 이미지 생성 프롬프트 (자동 생성)\n",
          f"> 비율: {ar} · 스타일: 시네마틱 역사 다큐 · 사람 얼굴 없음(초상권 회피)\n",
          "> ChatGPT/미드저니/ImageFX에 prompt_en 또는 midjourney 줄을 붙여넣고,\n",
          "> 나온 이미지를 각 항목의 파일명 그대로 저장하세요.\n"]
    for seg in cfg["segments"]:
        sid = seg["id"]
        target = seg.get("image", f"assets/{sid}.jpg")
        p = build_prompt(seg.get("text", ""), seg.get("caption", ""), ar)
        out_json[sid] = p
        manifest.append({"id": sid, "save_as": target, "prompt": p["prompt_en"]})
        md += [f"\n## {sid}  → 저장 파일명: `{target}`",
               f"- **EN**: {p['prompt_en']}",
               f"- **MJ**: `{p['midjourney']}`",
               f"- **negative**: {p['negative']}",
               f"- {p['note_ko']}"]

    json.dump(out_json, open(os.path.join(root, f"image_prompts.{ar}.json"), "w",
              encoding="utf-8"), ensure_ascii=False, indent=2)
    open(os.path.join(root, f"image_prompts.{ar}.md"), "w",
         encoding="utf-8").write("\n".join(md))
    # 본편(16:9) 기준으로 manifest 1개 유지(파일명 매핑은 비율 무관)
    if ar == "16x9":
        json.dump(manifest, open(os.path.join(root, "image_manifest.json"), "w",
                  encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"promptgen: {len(out_json)} prompts (ar={ar}) -> image_prompts.{ar}.md")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python promptgen.py config.json [--ar 9x16]")
        sys.exit(1)
    main()

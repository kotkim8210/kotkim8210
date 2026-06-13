#!/usr/bin/env python3
"""
handoff.py — '사람이 할 일'을 보기 쉽게 한 곳에 모아 출력한다.

생성물:
  - voice_script.md : 🎙️ 음성 녹음용 대본. 세그먼트별로 (저장 파일명 + 읽을 내용)을
        깔끔히 분리 → 브루에 그대로 복붙. 맨 아래 '전체 한 번에 복사' 블록도 제공.
  - human_tasks.md  : ✅ 마스터 체크리스트. 대본 ★승인 / 음성 / 이미지 / (고증 대기)
        를 체크박스로. "내가 뭘 해야 하지?"를 이 파일 하나로 끝낸다.

읽을 내용(tts_text)은 config.tts.json(있으면) 우선, 없으면 ttsfix로 즉석 생성.
사용:  python handoff.py config.json
"""
import json
import os
import re
import sys

from osmu_common import config_root, load_config, resolve, segment_images
import ttsfix


def _tts_map(root):
    """config.tts.json 이 있으면 {id: tts_text} 로딩."""
    p = os.path.join(root, "config.tts.json")
    if os.path.exists(p):
        cfg = json.load(open(p, encoding="utf-8"))
        return {s["id"]: s.get("tts_text", s.get("text", "")) for s in cfg.get("segments", [])}
    return {}


def reading_text(seg, ttsmap):
    """녹음용으로 읽을 텍스트(숫자·영문 한글화된 tts_text)."""
    if seg["id"] in ttsmap:
        return ttsmap[seg["id"]]
    fixed, _ = ttsfix.fix_text(seg.get("text", ""))
    return fixed


def gen_voice_script(cfg, root):
    ttsmap = _tts_map(root)
    lines = [
        "# 🎙️ 음성 녹음용 대본 (브루에 붙여넣기)\n",
        "> 사용법: 세그먼트별 **읽을 내용**을 브루(보이저 X)에 붙여 음성 생성 →",
        "> 표시된 **저장 파일명** 그대로 `assets/`에 저장하세요.",
        "> (한 번에 녹음하려면 맨 아래 '전체 대본' 사용 — `[s1]` 마커에서 잘라 저장)\n",
        "---\n",
    ]
    full = []
    for seg in cfg["segments"]:
        sid = seg["id"]
        target = seg.get("audio", f"assets/{sid}.mp3")
        rt = reading_text(seg, ttsmap)
        lines += [f"\n## {sid}  →  저장: `{target}`", "", rt, ""]
        full.append(f"[{sid}]\n{rt}")
    lines += ["\n---\n", "## 📋 전체 대본 (한 번에 복사)", "",
              "```", "\n\n".join(full), "```"]
    open(os.path.join(root, "voice_script.md"), "w", encoding="utf-8").write("\n".join(lines))


def gen_human_tasks(cfg, root):
    backend_v = cfg.get("voice", {}).get("backend", "files")
    backend_i = cfg.get("images", {}).get("backend", "prompts")

    # ★관점 세그먼트 추출: "pov":true 필드 또는 text/caption의 ★ 마커
    star = [s["id"] for s in cfg["segments"]
            if s.get("pov") is True or "★" in s.get("text", "") or "★" in s.get("caption", "")]

    # 고증 대기 건수
    pend = 0
    tp = os.path.join(root, "factcheck_todo.json")
    if os.path.exists(tp):
        d = json.load(open(tp, encoding="utf-8"))
        pend = d.get("pending", 0)

    # 자산 현황(이미 있는 건 ☑)
    def box(p):
        return "x" if os.path.exists(resolve(root, p)) else " "

    L = ["# ✅ 사람이 할 일 (이 파일 하나면 끝)\n"]

    L.append("## 1) 대본 ★관점 승인")
    if star:
        L.append(f"- ★ 세그먼트: {', '.join(star)} — 본인 말투/경험으로 확인·승인")
    else:
        L.append("- ★ 마커가 아직 없음. 심리·교훈 블록을 본인 말투로 한 번 손보세요"
                 " (text에 `★`를 넣으면 다음부터 자동 표시).")
    L.append("")

    L.append("## 2) 🎙️ 음성 녹음 → `assets/` 저장")
    if backend_v != "files":
        L.append(f"- voice.backend=`{backend_v}` → 자동 생성됨(녹음 불필요).")
    else:
        L.append("- 복붙용 대본: **`voice_script.md`**  (브루에 붙여넣기)")
        for s in cfg["segments"]:
            ap = s.get("audio", f"assets/{s['id']}.mp3")
            L.append(f"  - [{box(ap)}] `{ap}`  ({s['id']})")
    L.append("")

    total_img = sum(len(segment_images(s, cfg)) for s in cfg["segments"])
    L.append(f"## 3) 🖼️ 이미지 생성 → `assets/` 저장  (총 {total_img}장)")
    if backend_i != "prompts":
        L.append(f"- images.backend=`{backend_i}` → 자동 생성됨(작업 불필요).")
    else:
        L.append("- 프롬프트: **`image_prompts.16x9.md`** / 한 줄씩 묶음: **`image_prompts_batch.txt`**")
        L.append("- 💡 무료 제작 파이프라인 (2026 기준):")
        L.append("  1. **이미지: Flow(gemini.google.com/flow) = Nano Banana Pro** — 무료, 프롬프트 1개당 4장, **워터마크 없음**.")
        L.append("     (Gemini 앱·일반 Nano Banana 무료판은 로고 워터마크가 박힘 → 반드시 Flow에서.)")
        L.append("  2. 브라우저 **탭 5~6개**에 `image_prompts_batch.txt`를 나눠 넣어 배치 생성 → 4장씩 나오니 컷이 금방 참.")
        L.append("  3. (선택) **영상화: Kling AI** — 정지컷을 3~5초 영상으로. 무료 66크레딧/일 = 5초 ×6컷/일.")
        L.append("     → 전 컷은 무리(약 12일). '훅·정점·심리' 핵심 컷만 Kling, 나머지는 이 도구의 켄번즈로.")
        L.append("  4. **편집/자막: CapCut**(16:9·9:16 무료) 또는 이 도구의 build.py(켄번즈 자동 조립).")
        for s in cfg["segments"]:
            imgs = segment_images(s, cfg)
            have = sum(1 for p in imgs if os.path.exists(resolve(root, p)))
            mark = "x" if have == len(imgs) else " "
            L.append(f"  - [{mark}] {s['id']}: {have}/{len(imgs)}장  ({imgs[0]} … {imgs[-1].split('/')[-1]})")
    L.append("")

    L.append("## (참고) 고증 검증")
    if pend:
        L.append(f"- ⏳ {pend}건 대기 — **Claude가 web_search로 처리**(당신 작업 아님).")
    else:
        L.append("- ✅ 검증 완료(또는 미실행).")
    L.append("\n> 1·2·3 다 끝나면:  `python auto.py <config> --build`")

    open(os.path.join(root, "human_tasks.md"), "w", encoding="utf-8").write("\n".join(L))


def main():
    cfg_path = [a for a in sys.argv[1:] if not a.startswith("--")][0]
    root = config_root(cfg_path)
    cfg = load_config(cfg_path)
    gen_voice_script(cfg, root)
    gen_human_tasks(cfg, root)
    print("handoff: voice_script.md (음성 복붙용) + human_tasks.md (체크리스트) 생성")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python handoff.py config.json")
        sys.exit(1)
    main()

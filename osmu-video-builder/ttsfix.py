#!/usr/bin/env python3
"""
ttsfix.py — TTS가 자주 틀리는 부분을 자동 교정해 '자연스럽게 읽히는 대본'을 만든다.

  1) 숫자/연도/금액/퍼센트 → 한국어 수 읽기 (1637년→천육백삼십칠 년, 2.5%→이 점 오 퍼센트)
  2) 영문 약어/단어 → 한글 표기 (AI→에이아이) — 한글 인접도 처리
  3) 너무 긴 문장 → 마침표/쉼표로 호흡 분할 (어절 경계 보호)
  4) 줄임표·대시 등 기호 정리
  5) 동음이의 한자어는 리포트로만 경고

입력: config.json 의 각 segment["text"]  →  segment["tts_text"](읽기용) 추가
출력: config.tts.json + tts_report.md. 원문 text는 보존(자막·검토용).
"""
import json
import os
import re
import sys

from osmu_common import config_root, load_config

ENG = {
    "TTS": "티티에스", "AI": "에이아이", "SNS": "에스엔에스", "CEO": "씨이오", "PD": "피디",
    "PS5": "플레이스테이션 파이브", "IT": "아이티", "OK": "오케이", "VS": "대", "vs": "대",
    "GDP": "지디피", "ETF": "이티에프", "API": "에이피아이", "FOMO": "포모", "KTX": "케이티엑스",
}
UNIT = {"%": " 퍼센트", "kg": " 킬로그램", "km": " 킬로미터", "cm": " 센티미터", "℃": " 도", "㎡": " 제곱미터"}
HOMOPHONE = ["사과", "정상", "유산", "연패", "방화"]
DG = "영일이삼사오육칠팔구"
_SMALL = ["", "십", "백", "천"]
_BIG = ["", "만", "억", "조"]


def sino(n):
    if n == 0:
        return "영"
    out, grp = "", 0
    while n > 0:
        part = n % 10000
        n //= 10000
        if part:
            s, p = "", str(part).zfill(4)
            for i, ch in enumerate(p):
                d = int(ch)
                if d:
                    s += ("" if (d == 1 and (3 - i) > 0) else DG[d]) + _SMALL[3 - i]
            out = s + _BIG[grp] + out
        grp += 1
    return out


def read_numbers(s):
    s = re.sub(r"(\d{4})\s*년", lambda m: sino(int(m.group(1))) + " 년", s)
    s = re.sub(r"(\d+)\s*(조|억|만)\s*원", lambda m: sino(int(m.group(1))) + m.group(2) + " 원", s)
    s = re.sub(r"(\d+)\.(\d+)",
               lambda m: " ".join(DG[int(d)] for d in m.group(1)) + " 점 " +
                         " ".join(DG[int(d)] for d in m.group(2)), s)
    s = re.sub(r"(?<!\d)(\d{1,4})(?!\d)", lambda m: sino(int(m.group(1))), s)
    return s


def apply_units(s):
    for k, v in UNIT.items():
        s = s.replace(k, v)
    return s


def apply_eng(s):
    for k in sorted(ENG, key=lambda x: -len(x)):
        s = re.sub(rf"(?<![A-Za-z]){re.escape(k)}(?![A-Za-z])", ENG[k], s)
    return s


def split_long(s, max_len=45):
    out = []
    for sent in re.split(r"(?<=[.!?])\s+", s):
        if len(sent) <= max_len or "," in sent:
            out.append(sent)
            continue
        words = sent.split(" ")
        buf = ""
        pieces = []
        for w in words:
            if len(buf) + len(w) > max_len and buf and len(w) > 1:
                pieces.append(buf.strip())
                buf = w
            else:
                buf = (buf + " " + w).strip()
        if buf:
            pieces.append(buf.strip())
        merged = []
        for p in pieces:
            if merged and len(merged[-1].split()[-1]) <= 2 and len(p.split()[0]) <= 3:
                merged[-1] = merged[-1] + " " + p
            else:
                merged.append(p)
        out.append(", ".join(merged))
    return " ".join(out)


def clean_symbols(s):
    return s.replace("—", " ").replace("…", ".").replace("·", " ").replace("  ", " ").strip()


def fix_text(text):
    notes = []
    if re.search(r"[A-Za-z]", text):
        notes.append("영문→한글")
    if re.search(r"\d", text):
        notes.append("숫자 읽기")
    for h in HOMOPHONE:
        if h in text:
            notes.append(f"동음이의 '{h}' 확인")
    t = apply_eng(text)
    t = read_numbers(t)
    t = apply_units(t)
    t = clean_symbols(t)
    before = t
    t = split_long(t)
    if t != before:
        notes.append("호흡 분할")
    return t, notes


def main():
    cfg_path = [a for a in sys.argv[1:] if not a.startswith("--")][0]
    root = config_root(cfg_path)
    cfg = load_config(cfg_path)
    rep = ["# TTS 교정 리포트\n", "> 원문 text는 보존(자막·검토용). tts_text가 읽기용입니다.\n"]
    for seg in cfg["segments"]:
        orig = seg.get("text", "")
        fixed, notes = fix_text(orig)
        seg["tts_text"] = fixed
        rep += [f"\n## {seg['id']}", f"- 변환: {', '.join(notes) or '없음'}",
                f"- 원문: {orig}", f"- 읽기용: {fixed}"]
    json.dump(cfg, open(os.path.join(root, "config.tts.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    open(os.path.join(root, "tts_report.md"), "w", encoding="utf-8").write("\n".join(rep))
    print(f"ttsfix: {len(cfg['segments'])} segments -> config.tts.json / tts_report.md")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python ttsfix.py config.json")
        sys.exit(1)
    main()

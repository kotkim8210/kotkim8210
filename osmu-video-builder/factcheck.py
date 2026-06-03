#!/usr/bin/env python3
"""
factcheck.py — 대본 자가 고증 검토 (작성 후 스스로 점검).

탐지(자동) + 검증(Claude가 채팅에서) 분담은 그대로. 단 자동화를 위해 두 가지 추가:

  ① factcheck_todo.json  — [수치확인]/[실명위험] 만 모은 '기계가 읽는 작업목록'.
       Claude는 이 파일만 보면 무엇을 web_search 해야 하는지 정확히 안다.
       (예전엔 리포트를 사람이 눈으로 훑어야 해서 자꾸 빠뜨렸다.)
  ② factlog.json 연동    — 이미 검증/수정 끝낸 항목은 todo에서 status=done 으로 표시.
       → 같은 숫자를 매 화차 다시 확인하라고 보채지 않는다(나가는 nagging 제거).

잡아내는 것:
  1) 시대 불일치(anachronism)  2) 수치 주장  3) 단정 표현
  4) 실명 위험  5) 모호 출처어

입력: config.json 또는 .md 대본. 출력: factcheck_report.md / factcheck.json / factcheck_todo.json
사용:  python factcheck.py config.json [--era 17c]
"""
import json
import os
import re
import sys

from osmu_common import config_root

MODERN = ["스마트폰", "휴대폰", "핸드폰", "인터넷", "앱", "어플", "주식앱", "컴퓨터", "비행기",
          "자동차", "전기", "텔레비전", "TV", "라디오", "카메라", "사진", "달러", "비트코인",
          "코인", "ETF", "신용카드", "은행 앱", "유튜브", "SNS", "엘리베이터", "지하철"]
ERA_OK_AFTER = {
    "17c": MODERN,
    "18c": list(MODERN),
    "19c": ["스마트폰", "휴대폰", "핸드폰", "인터넷", "앱", "어플", "컴퓨터", "비행기", "자동차",
            "텔레비전", "TV", "유튜브", "SNS", "비트코인", "코인", "ETF"],
    "20c": ["스마트폰", "인터넷", "앱", "어플", "유튜브", "SNS", "비트코인", "코인", "ETF"],
    "modern": [],
}
ABSOLUTES = ["반드시", "무조건", "모두", "전부", "100%", "백 퍼센트", "전혀", "절대", "최초", "유일",
             "항상", "언제나", "아무도", "누구나"]
VAGUE = ["라고 한다", "전해진다", "알려져 있다", "카더라", "라는 설", "아마도", "것 같다"]
NUM_PAT = re.compile(r"(\d[\d,\.]*\s*(년|원|퍼센트|%|명|배|억|만|조|개|세기)?)")
MODERN_TITLE = ["대통령", "장관", "의원", "회장", "CEO", "대표", "감독", "선수", "배우", "가수", "총리"]

# Claude가 채팅에서 직접 검증해야 하는 카테고리 (SKILL.md 강제 대상)
RESOLVABLE = {"수치확인", "실명위험"}


def get_texts(cfg_path):
    if cfg_path.endswith(".json"):
        cfg = json.load(open(cfg_path, encoding="utf-8"))
        return [(s["id"], s.get("text", ""), s.get("era")) for s in cfg.get("segments", [])]
    txt = open(cfg_path, encoding="utf-8").read()
    return [(f"block{i+1}", p, None) for i, p in enumerate(re.split(r"\n\s*\n", txt)) if p.strip()]


def check(text, era):
    issues = []
    for w in ERA_OK_AFTER.get(era, []):
        if re.search(re.escape(w), text):
            issues.append(("시대불일치", f"'{w}' — {era} 배경에 부적절(현대 요소)"))
    for w in ABSOLUTES:
        if w in text:
            issues.append(("단정표현", f"'{w}' — 과장/반례 위험, 완충 표현 검토"))
    for w in VAGUE:
        if w in text:
            issues.append(("모호출처", f"'{w}' — 근거 보강 권고"))
    nums = [m.group(0).strip() for m in NUM_PAT.finditer(text) if m.group(0).strip()]
    nums = [n for n in nums if re.search(r"\d", n)]
    if nums:
        issues.append(("수치확인", "출처 확인 필요: " + ", ".join(dict.fromkeys(nums))))
    for t in MODERN_TITLE:
        for m in re.finditer(rf"([가-힣]{{2,4}})\s*{t}", text):
            issues.append(("실명위험", f"'{m.group(0)}' — 현대 실존인물? 명예훼손/초상권 점검"))
    return issues


def load_factlog(root):
    p = os.path.join(root, "factlog.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    era = "17c"
    if "--era" in sys.argv:
        era = sys.argv[sys.argv.index("--era") + 1]
    cfg_path = args[0]
    root = config_root(cfg_path)
    factlog = load_factlog(root)

    rep = [f"# 대본 고증 자가검토 리포트  (시대 기준: {era})\n",
           "> 자동 '검출'입니다. [수치확인]·[실명위험]은 Claude가 채팅에서 web_search로 검증·수정합니다.\n",
           "> 검출 0이어도 '검증됨'은 아닙니다.\n"]
    out = {}
    todo = []
    total = 0
    for sid, text, seg_era in get_texts(cfg_path):
        use_era = seg_era or era
        iss = check(text, use_era)
        out[sid] = iss
        total += len(iss)
        tag = f"  ({len(iss)}건)" + (f" [시대:{use_era}]" if seg_era else "")
        rep.append(f"\n## {sid}{tag}")
        if not iss:
            rep.append("- 자동 검출 없음 (그래도 수치·고증 수동 확인 권장)")
        for cat, msg in iss:
            done = False
            if cat in RESOLVABLE:
                key = f"{sid}::{cat}::{msg}"
                logged = factlog.get(key)
                if logged and logged.get("status") in ("verified", "fixed"):
                    done = True
                    todo.append({"sid": sid, "type": cat, "detail": msg,
                                 "status": "done", "source": logged.get("source"),
                                 "note": logged.get("note")})
                else:
                    todo.append({"sid": sid, "type": cat, "detail": msg,
                                 "status": "pending", "source": None, "note": None})
            mark = " ✅검증완료" if done else ""
            rep.append(f"- **[{cat}]** {msg}{mark}")
    rep.insert(3, f"\n**총 검출: {total}건**\n")

    pending = [t for t in todo if t["status"] == "pending"]
    json.dump(out, open(os.path.join(root, "factcheck.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump({"config": os.path.basename(cfg_path), "era": era,
               "pending": len(pending), "items": todo},
              open(os.path.join(root, "factcheck_todo.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    open(os.path.join(root, "factcheck_report.md"), "w", encoding="utf-8").write("\n".join(rep))
    print(f"factcheck: {total} flags / 검증대기 {len(pending)}건 "
          f"-> factcheck_todo.json (Claude 작업목록)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python factcheck.py config.json [--era 17c]")
        sys.exit(1)
    main()

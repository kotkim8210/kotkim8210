#!/bin/bash
# 발행 파이프라인 — 순서 고정 + 실패 시 즉시 중단 + 산출물 검증
set -euo pipefail
TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NOVEL_TOOLS="$TOOLS"
export NOVEL_ROOT="${NOVEL_ROOT:-$(cd "$TOOLS/../.." && pwd)}"
export NOVEL_OUT="${NOVEL_OUT:-/tmp/claude-0/-home-user-kotkim8210/c058c336-4e2b-5e83-9e93-9b4f05f88f8f/scratchpad}"
mkdir -p "$NOVEL_OUT"

cd "$NOVEL_OUT"
echo "── 1/4 계측"; python3 "$TOOLS/measure.py" | tail -3
echo "── 2/4 문서 빌드"; python3 "$TOOLS/build_downloads.py" | tail -4
echo "── 3/4 뷰어 빌드"; python3 "$TOOLS/build_viewer.py" | tail -1
echo "── 4/4 산출물 검증"
LAST=$(ls novel 2>/dev/null || true)
TOTAL=$(python3 -c "
import glob, os
fs=sorted(glob.glob(os.environ['NOVEL_ROOT'] + '/novel/manuscript/*.md'))
print(sum(len('\n'.join(l for l in open(p,encoding='utf-8').read().split('\n') if not l.startswith('# '))) for p in fs))
")
EP=$(ls $NOVEL_ROOT/novel/manuscript/*.md | wc -l)
MS=$(printf "죽은헌터의유언을집행합니다_원고_001-%03d.md" "$EP")
FAIL=0
chk(){ if grep -q "$2" "$1"; then echo "  ✓ $3"; else echo "  ✗ $3 — '$2' 없음"; FAIL=1; fi; }
FMT=$(python3 -c "print(f'{$TOTAL:,}')")
chk "$MS" "총 ${FMT}자" "원고 표지 자수"
chk "$MS" "$(printf '001~%03d화' $EP)" "원고 표지 회차"
chk "죽은헌터의유언을집행합니다_제작문서.md" "${FMT}자" "제작문서 STATUS 자수"
# 활성 플롯이 문서에 실제로 실렸는지: 최신 회차 요약 키워드
LASTTITLE=$(head -1 "$(ls $NOVEL_ROOT/novel/manuscript/*.md | tail -1)" | sed 's/^# [0-9]*\. //')
chk "죽은헌터의유언을집행합니다_제작문서.md" "「${LASTTITLE}」 ✅" "활성 플롯에 최신 회차 요약 반영"
# bible/state.md 의 '최종 반영' 회차가 실제 최신 회차와 같은지 (서사 상태가 본문보다 뒤처지는 것을 막는다 — 23차 검수)
if python3 - <<'PYEOF'
import re, sys, pathlib, os
root = pathlib.Path(os.environ["NOVEL_ROOT"] + "/novel")
last = max(int(f.stem) for f in (root / "manuscript").glob("[0-9][0-9][0-9].md"))
raw = (root / "bible" / "state.md").read_text(encoding="utf-8")
m = re.search(r"<!--\s*최종 반영:\s*(\d+)\s*-->", raw)
if not m:
    print("    state.md에 '<!-- 최종 반영: NNN -->' 주석이 없음"); sys.exit(1)
if int(m.group(1)) != last:
    print(f"    state.md 최종 반영 {int(m.group(1)):03d} / 실제 최신 {last:03d}"); sys.exit(1)
PYEOF
then echo "  ✓ 서사 상태(state.md) 최신 회차 반영"; else echo "  ✗ 서사 상태가 본문보다 뒤처짐"; FAIL=1; fi
# 시스템 창의 享年 값이 캐릭터 바이블과 일치하는지 (26차 검수 — 34/38 오기)
if python3 - <<'PYEOF'
import re, sys, pathlib, os
root = pathlib.Path(os.environ["NOVEL_ROOT"] + "/novel")
chars = (root / "bible" / "characters.md").read_text(encoding="utf-8")
canon = {}
for nm, ag in re.findall(r"([가-힣]{2,4})\s*\(([^)]*享年\s*\d+[^)]*)\)", chars):
    m = re.search(r"享年\s*(\d+)", ag)
    if m: canon.setdefault(nm, m.group(1))
bad = []
for f in sorted((root / "manuscript").glob("[0-9][0-9][0-9].md")):
    for i, line in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
        for nm, ag in re.findall(r"([가-힣]{2,4})\s*\(\s*享年\s*(\d+)\s*\)", line):
            if nm in canon and canon[nm] != ag:
                bad.append(f"{f.stem}:{i} {nm} 享年{ag} (바이블 {canon[nm]})")
if bad:
    print("    " + " | ".join(bad)); sys.exit(1)
PYEOF
then echo "  ✓ 享年 값이 캐릭터 바이블과 일치"; else echo "  ✗ 享年 불일치"; FAIL=1; fi
# 폐기 문구가 활성 바이블(bible/)에 남아 있는지 — state.md의 목록이 출처 (24차 검수)
if python3 - <<'PYEOF'
import re, sys, pathlib, os
root = pathlib.Path(os.environ["NOVEL_ROOT"] + "/novel/bible")
raw = (root / "state.md").read_text(encoding="utf-8")
sec = raw.split("## 폐기 문구")[-1] if "## 폐기 문구" in raw else ""
dead = re.findall(r"^- `([^`]+)`", sec, re.M)
bad = []
# 폐기로 '표시된' 자리는 통과시킨다 — 로그·정정 기록에는 원문이 남아야 한다
MARK = ("폐기", "추정", "시정", "구버전", "수정 전", "교체")
for f in sorted(root.glob("*.md")):
    if f.name in ("state.md", "STATUS.md"): continue   # state=출처, STATUS=자동 생성
    for i, line in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
        if any(m in line for m in MARK): continue
        for d in dead:
            if d in line: bad.append(f"{f.name}:{i} '{d}'")
if bad:
    print("    " + " | ".join(bad)); sys.exit(1)
PYEOF
then echo "  ✓ 폐기 문구 잔재 (bible/)"; else echo "  ✗ 폐기 문구가 활성 바이블에 남아 있음"; FAIL=1; fi
# style-guide §13-1 파편 종결 / §13-2 동일 어미 3연속 (전 회차)
if python3 - <<'PYEOF'
import sys, glob, os, io
sys.path.insert(0, os.environ["NOVEL_TOOLS"])
_o = sys.stdout; sys.stdout = io.StringIO()
import measure
fs = sorted(glob.glob(os.environ["NOVEL_ROOT"] + "/novel/manuscript/[0-9][0-9][0-9].md"))
sys.stdout = _o
bad = []
for f in fs:
    r = measure.measure(f)
    if r[8] or r[9]: bad.append(f"{os.path.basename(f)[:3]}: 파편{r[8]} 반복{r[9]}")
if bad:
    print("    " + " | ".join(bad)); sys.exit(1)
PYEOF
then echo "  ✓ 어미 규칙 (§13-1 파편 · §13-2 계사 3연속)"; else echo "  ✗ 어미 규칙 위반"; FAIL=1; fi
# 유료 분량 범위(4,200~5,500자) — 30화 이후 전 회차. 상한 초과는 배포 금지 (20차 검수)
if python3 - <<'PYEOF'
import sys, pathlib, os
bad = []
for f in sorted(pathlib.Path(os.environ["NOVEL_ROOT"] + "/novel/manuscript").glob("[0-9][0-9][0-9].md")):
    n = int(f.stem)
    if n < 30: continue
    c = len("\n".join(l for l in f.read_text(encoding="utf-8").split("\n") if not l.startswith("# ")))
    if not (4200 <= c <= 5500): bad.append(f"{n:03d}: {c:,}")
if bad:
    print("    " + " | ".join(bad)); sys.exit(1)
PYEOF
then echo "  ✓ 유료 분량 범위 (030~)"; else echo "  ✗ 유료 분량 범위 이탈"; FAIL=1; fi
# 활성 플롯 아웃라인에 적힌 회차별 자수가 실제 원고와 일치하는지 (19차 검수 결함 — 수기 숫자는 반드시 썩는다)
if python3 - <<'PYEOF'
import re, sys, pathlib, os
def chars(n):
    raw = pathlib.Path(os.environ["NOVEL_ROOT"] + f"/novel/manuscript/{n:03d}.md").read_text(encoding="utf-8")
    return len("\n".join(l for l in raw.split("\n") if not l.startswith("# ")))
src = pathlib.Path(os.environ["NOVEL_ROOT"] + "/novel/bible/plot-outline.md").read_text(encoding="utf-8")
bad = []
for n, rec in re.findall(r"\*\*(\d{3}) 「[^」]*」 ✅\*\*\(([\d,]+)자", src):
    a = chars(int(n))
    if int(rec.replace(",", "")) != a:
        bad.append(f"{n}: 기록 {rec} / 실제 {a:,}")
if bad:
    print("    " + " | ".join(bad)); sys.exit(1)
PYEOF
then echo "  ✓ 활성 플롯 회차별 자수"; else echo "  ✗ 활성 플롯 회차별 자수 불일치"; FAIL=1; fi

# ⑪ 편집 리포트 전량이 제작문서 본문에 실제로 들어갔는지 (28차 검수 — 표지 REPORT_RANGE는 glob 자동인데
#    본문 목록은 하드코딩이라 #026이 통째로 빠진 적이 있다. 표지와 본문을 서로 대조한다.)
if python3 - <<'PYEOF'
import pathlib, re, sys, os
SP = pathlib.Path(os.environ["NOVEL_OUT"])
doc = (SP / "죽은헌터의유언을집행합니다_제작문서.md").read_text(encoding="utf-8")
have = {int(x) for x in re.findall(r"^#+ *\d+\. 편집 리포트 #(\d{3})", doc, re.M)}
want = {int(f.stem.split("-")[-1])
        for f in pathlib.Path(os.environ["NOVEL_ROOT"] + "/novel/editorial").glob("edit-report-*.md")}
miss = sorted(want - have)
if miss:
    print("    본문 누락 리포트: " + ", ".join(f"#{n:03d}" for n in miss)); sys.exit(1)
# 표지 REPORT_RANGE는 본문과 동일한 glob(_REPORTS)에서 파생되므로 구조상 어긋날 수 없다.
# 문서 본문에는 과거 리포트가 옛 표지 문구를 인용해 놓은 자리가 있어 정규식으로 재검사하면 오탐이 난다.
PYEOF
then echo "  ✓ 편집 리포트 전량 수록"; else echo "  ✗ 편집 리포트 누락"; FAIL=1; fi

# ⑫ 편집 리포트 헤더의 회차 자수 (28차 검수 — 원고를 고치고 리포트 첫 줄만 구판으로 남았다.
#    `novel/manuscript/NNN.md` (N,NNN자 형태는 리포트 헤더에서만 쓰는 표기라 인용문 오탐이 없다.)
if python3 - <<'PYEOF'
import pathlib, re, sys, os
root = pathlib.Path(os.environ["NOVEL_ROOT"]) / "novel"
def chars(n):
    raw = (root / "manuscript" / f"{n:03d}.md").read_text(encoding="utf-8")
    return len("\n".join(l for l in raw.split("\n") if not l.startswith("# ")))
bad = []
for f in sorted((root / "editorial").glob("edit-report-*.md")):
    for n, rec in re.findall(r"novel/manuscript/(\d{3})\.md` \(([\d,]+)자", f.read_text(encoding="utf-8")):
        a = chars(int(n))
        if int(rec.replace(",", "")) != a:
            bad.append(f"{f.name} {n}화: 기록 {rec} / 실제 {a:,}")
if bad:
    print("    " + " | ".join(bad)); sys.exit(1)
PYEOF
then echo "  ✓ 편집 리포트 헤더 자수"; else echo "  ✗ 편집 리포트 헤더 자수 불일치"; FAIL=1; fi

# ⑬ 사이다 장부 — 회차 누락 + 보상 간격 산술 (31차 검수. 절단 감사가 '궁금함'을 관리한다면 이쪽은 '기분 좋음'을 관리한다.
#    등급 판정은 사람이 하고, 게이트는 산술만 본다. 규칙은 장부 머리의 '규칙 적용 시작' 회차부터 적용.)
if python3 - <<'PYEOF'
import pathlib, re, sys, os
root = pathlib.Path(os.environ["NOVEL_ROOT"]) / "novel"
led = (root / "bible" / "catharsis-ledger.md").read_text(encoding="utf-8")
eps = sorted(int(f.stem) for f in (root / "manuscript").glob("[0-9][0-9][0-9].md"))
m = re.search(r"<!--\s*규칙 적용 시작:\s*(\d{3})\s*-->", led)
if not m:
    print("    장부 머리에 '규칙 적용 시작' 주석이 없다"); sys.exit(1)
START = int(m.group(1))
GRADE = {}
for n, g in re.findall(r"^\|\s*\*{0,2}(\d{3})\*{0,2}\s*\|\s*[⭐\s]*\*{0,2}(응징|대리만족|소승|없음)\*{0,2}\s*\|", led, re.M):
    GRADE[int(n)] = g
missing = [n for n in eps if n not in GRADE]
if missing:
    print("    장부 누락 회차: " + ", ".join(f"{n:03d}" for n in missing)); sys.exit(1)
RANK = {"없음": 0, "소승": 1, "대리만족": 2, "응징": 3}
bad = []
# 시작점에서 카운터를 0으로 리셋하면 이미 쌓인 부채를 게이트가 못 본다.
# 시작점 직전까지의 연속 공백을 초기값으로 물려받는다. 응징만 예외(42화 부채는 소급 청산 불가).
for label, need, limit, carry in (("소승 이상", 1, 3, True), ("대리만족 이상", 2, 6, True), ("응징", 3, 10, False)):
    run = 0
    if carry:
        for n in [x for x in eps if x < START][::-1]:
            if RANK[GRADE[n]] >= need:
                break
            run += 1
    for n in eps:
        if n < START:
            continue
        run = 0 if RANK[GRADE[n]] >= need else run + 1
        if run > limit:
            bad.append(f"{label} {limit}화 한도 초과 ({n:03d}화까지 {run}화 연속 없음)")
            break
if bad:
    print("    " + " | ".join(bad)); sys.exit(1)
PYEOF
then echo "  ✓ 사이다 장부 (회차 수록 · 보상 간격)"; else echo "  ✗ 사이다 장부 위반"; FAIL=1; fi

# ⑭ 화면 호흡 — 장면 구분선(⁂) 과다 (32차 검수. 001~028은 화당 2.1개였는데 056에서 51개까지 표류했다.
#    ⁂를 내부 상태관리 단위로 쓴 것이 원인이라, 독자용 하드컷과 분리해 상한을 건다.)
if python3 - <<'PYEOF'
import pathlib, re, sys, os
root = pathlib.Path(os.environ["NOVEL_ROOT"]) / "novel" / "manuscript"
bad = []
for f in sorted(root.glob("[0-9][0-9][0-9].md")):
    n = int(f.stem)
    c = f.read_text(encoding="utf-8").count("⁂")
    if c > 25:
        bad.append(f"{n:03d}화 {c}개")
if bad:
    print("    ⁂ 25개 초과: " + ", ".join(bad)); sys.exit(1)
PYEOF
then echo "  ✓ 화면 호흡 (장면 구분선 ≤25)"; else echo "  ✗ 장면 구분선 과다"; FAIL=1; fi
if [ "$FAIL" = "1" ]; then echo "❌ 검증 실패 — 배포 금지"; exit 1; fi
echo "✅ 전 항목 일치 — 배포 가능 (${EP}화 / ${FMT}자)"

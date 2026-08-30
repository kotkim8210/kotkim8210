# -*- coding: utf-8 -*-
"""novel/ 원본 → 합본 Markdown 2종 + 조판 PDF 2종"""
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
import os
from pathlib import Path as _P
_ROOT = os.environ.get("NOVEL_ROOT") or str(_P(__file__).resolve().parents[2])
_OUT  = os.environ.get("NOVEL_OUT")  or "/tmp/claude-0/-home-user-kotkim8210/c058c336-4e2b-5e83-9e93-9b4f05f88f8f/scratchpad"
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                Table, TableStyle, HRFlowable, KeepTogether)

ROOT = Path(_ROOT)
NOVEL = ROOT / "novel"
OUTDIR = Path(_OUT)
FONTDIR = Path("/usr/share/fonts/truetype/nanum")
# 회차 수는 원고 디렉터리에서 자동 판정한다 (하드코딩 금지 — 18차/41차 검수 결함의 근본 원인)
LAST_EP = max(int(f.stem) for f in (NOVEL / "manuscript").glob("[0-9][0-9][0-9].md"))

# ── 폰트 ──
pdfmetrics.registerFont(TTFont("NMJ", str(FONTDIR / "NanumMyeongjo.ttf")))
pdfmetrics.registerFont(TTFont("NMJ-B", str(FONTDIR / "NanumMyeongjoBold.ttf")))
pdfmetrics.registerFont(TTFont("NBG", str(FONTDIR / "NanumBarunGothic.ttf")))
pdfmetrics.registerFont(TTFont("NBG-B", str(FONTDIR / "NanumBarunGothicBold.ttf")))
pdfmetrics.registerFont(TTFont("NGC", str(FONTDIR / "NanumGothicCoding.ttf")))
try:
    pdfmetrics.registerFont(TTFont("HANJA", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", subfontIndex=0))
    HANJA_OK = True
except Exception as e:
    print("hanja font unavailable:", e); HANJA_OK = False
registerFontFamily("NMJ", normal="NMJ", bold="NMJ-B", italic="NMJ", boldItalic="NMJ-B")
registerFontFamily("NBG", normal="NBG", bold="NBG-B", italic="NBG", boldItalic="NBG-B")

INK = colors.HexColor("#1C1D21")
SOFT = colors.HexColor("#565863")
SEAL = colors.HexColor("#A63A2B")
GHOST = colors.HexColor("#5B6B7E")
LINE = colors.HexColor("#C9C9C0")
PAPER2 = colors.HexColor("#F0F0EA")

# ── 스타일 ──
S = {}
S["novel"] = ParagraphStyle("novel", fontName="NMJ", fontSize=10.5, leading=19,
                            textColor=INK, alignment=TA_JUSTIFY, wordWrap="CJK",
                            spaceAfter=7, firstLineIndent=0)
S["ghost"] = ParagraphStyle("ghost", parent=S["novel"], textColor=GHOST)
S["relay"] = ParagraphStyle("relay", parent=S["novel"], textColor=SOFT)
S["scene"] = ParagraphStyle("scene", parent=S["novel"], alignment=TA_CENTER,
                            textColor=SOFT, spaceBefore=10, spaceAfter=14)
S["sysbox"] = ParagraphStyle("sysbox", fontName="NBG", fontSize=8.6, leading=15,
                             textColor=INK, wordWrap="CJK", alignment=TA_LEFT)
S["ep-eyebrow"] = ParagraphStyle("epeye", fontName="NBG", fontSize=8, leading=12,
                                 textColor=SEAL, spaceAfter=4)
S["ep-title"] = ParagraphStyle("eptitle", fontName="NMJ-B", fontSize=17, leading=24,
                               textColor=INK, spaceAfter=14)
S["h1"] = ParagraphStyle("h1", fontName="NBG-B", fontSize=15, leading=21, textColor=INK,
                         spaceBefore=6, spaceAfter=10)
S["h2"] = ParagraphStyle("h2", fontName="NBG-B", fontSize=12.5, leading=18, textColor=INK,
                         spaceBefore=14, spaceAfter=7)
S["h3"] = ParagraphStyle("h3", fontName="NBG-B", fontSize=10.5, leading=15, textColor=INK,
                         spaceBefore=11, spaceAfter=5)
S["body"] = ParagraphStyle("body", fontName="NBG", fontSize=9.2, leading=15.5, textColor=INK,
                           wordWrap="CJK", spaceAfter=5, alignment=TA_LEFT)
S["li"] = ParagraphStyle("li", parent=S["body"], leftIndent=10, bulletIndent=2, spaceAfter=3)
S["quote"] = ParagraphStyle("quote", parent=S["body"], leftIndent=10, textColor=SOFT,
                            borderPadding=(2, 6), spaceAfter=6)
S["pre"] = ParagraphStyle("pre", fontName="NGC", fontSize=7.6, leading=11.5, textColor=INK,
                          backColor=PAPER2, borderPadding=(6, 8), spaceAfter=8)
S["cell"] = ParagraphStyle("cell", fontName="NBG", fontSize=7.4, leading=11,
                           textColor=INK, wordWrap="CJK")
S["cellh"] = ParagraphStyle("cellh", parent=S["cell"], fontName="NBG-B")
S["meta"] = ParagraphStyle("meta", fontName="NBG", fontSize=8, leading=12,
                           textColor=SOFT, spaceAfter=4)

HANJA_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]+")

def wrap_hanja(s: str) -> str:
    """나눔 폰트에 없는 한자를 폴백 폰트로 감싼다 (escape 이후에 호출)."""
    if not HANJA_OK:
        return s
    return HANJA_RE.sub(lambda m: f'<font face="HANJA">{m.group(0)}</font>', s)

def inline(s: str, mono_face="NGC") -> str:
    s = escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", rf'<font face="{mono_face}" size="-0.8">\1</font>', s)
    s = re.sub(r"\[\[([^\]]+)\]\]", rf'<font color="#A63A2B">\1</font>', s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", s)
    return wrap_hanja(s)

# 떡밥 집계는 장부의 최신 "등록 N = 활성 N / 회수 N" 줄에서 자동 판독 (하드코딩 금지 — 26차 검수)
_fs = (NOVEL / "bible" / "foreshadowing.md").read_text(encoding="utf-8")
_fm = re.findall(r"등록\s*(\d+)\s*=\s*활성\s*(\d+)\s*/\s*회수\s*(\d+)", _fs)
FS_REG, FS_ACT, FS_DONE = _fm[-1] if _fm else ("?", "?", "?")

_REPORTS = []
for _f in sorted((NOVEL / "editorial").glob("edit-report-*.md")):
    _n = int(_f.stem.split("-")[-1])
    _b = _f.read_text(encoding="utf-8")
    _h = _b.split("\n", 1)[0]
    _m = re.match(r"#\s*편집 리포트 #\d+\s*[—-]\s*(.+)$", _h.strip())
    _REPORTS.append((_n, (_m.group(1).strip() if _m else _f.stem), _b))
if not _REPORTS:
    raise SystemExit("편집 리포트를 하나도 못 찾았다 — 경로 확인")
LAST_REPORT = max(n for n, _, _ in _REPORTS)
# ⚠ 구판 산출물 제거 — 회차마다 파일명이 바뀌어 스크래치패드에 001-008 … 001-055가 쌓였고,
#   검수자가 그중 옛 파일을 열어 "056이 없다"는 오판이 났다(32차 검수). 최신 것만 남긴다.
for _old in _P(_OUT).glob("*_원고_001-*.*"):
    _old.unlink(missing_ok=True)
REPORT_RANGE = f"#001~#{LAST_REPORT:03d}"
MS_MD_NAME = f"죽은헌터의유언을집행합니다_원고_001-{LAST_EP:03d}.md"
MS_PDF_NAME = f"죽은헌터의유언을집행합니다_원고_001-{LAST_EP:03d}.pdf"

# ══════════════ 1) 합본 Markdown ══════════════
def read(p): return p.read_text(encoding="utf-8")

eps = []
for n in range(1, LAST_EP + 1):
    raw = read(NOVEL / "manuscript" / f"{n:03d}.md")
    title = raw.split("\n", 1)[0].lstrip("# ").strip()
    body = raw.split("\n", 1)[1].strip()
    # 자수 계측 canonical: 제목 줄만 제외한 나머지 전체(공백·빈 줄 포함) — scratchpad/measure.py와 동일 정의
    eps.append((n, title, body, len("\n".join(l for l in raw.split("\n") if not l.startswith("# ")))))

total_chars = sum(e[3] for e in eps)
today = "2026-08-09"
_n = eps[-1][0]
ARC_LABEL = ("1부 A1 시작" if _n <= 7 else "1부 A1 완료 · A2 진행" if _n <= 15
    else "1부 A1~A2 완료 · A3 진행" if _n <= 28 else "1부 A1~A3 완료 · A4 진행" if _n <= 43
    else "1부 A1~A4 완료 · A5 진행" if _n <= 55 else "1부 A1~A5 완료 · A6 진행" if _n <= 75
    else "1부 A1~A6 완료 · A7 진행" if _n < 85 else "1부 완결")

# ── STATUS 블록: 빌드 시점에 실측값으로 생성 → 수기 갱신 누락으로 인한 desync 원천 차단
_last5 = "\n".join(f"- {n:03d}화 「{ti.split('. ',1)[-1]}」 — {c:,}자" for n, ti, _b, c in eps[-5:])
_m = re.findall(r"유족 고지 \((\d+)\s*/\s*29\)", "\n".join(e[2] for e in eps))
_notify = _m[-1] if _m else "0"

# 진행 중인 서사 상태는 저장소의 bible/state.md가 단일 출처다 (빌드 스크립트에 문자열로 박지 않는다)
_state_raw = (NOVEL / "bible" / "state.md").read_text(encoding="utf-8")
_state = "\n".join(l for l in _state_raw.split("\n")
                   if not l.startswith("<!--") and not l.startswith("> ")).strip()
_state = _state.replace("{_notify}", _notify)

STATUS_MD = f"""# ⭐ 현재 상태 (STATUS) — 빌드 시점 자동 생성

> **이 블록이 항상 최신이다.** 수기로 고치지 말 것. `build_downloads.py`가 원고를 직접 계측해 매 빌드마다 다시 쓴다.
> 다른 문서(편집 리포트·연재 로그)와 숫자가 어긋나면 **이 블록이 맞다.**

| 항목 | 값 |
|---|---|
| 집필 범위 | **001~{eps[-1][0]:03d}화** |
| 총량 | **{total_chars:,}자** (제목 줄 제외, 공백·빈 줄 포함) |
| 최신 회차 | {eps[-1][0]:03d}화 「{eps[-1][1].split('. ',1)[-1]}」 |
| 생성 시각 기준일 | {today} |

## 최근 5화
{_last5}

{_state}

---

"""

ms_md = [f"# 죽은 헌터의 유언을 집행합니다\n",
         f"> 남성향 현대판타지 · 헌터물 · 미스터리 | 원고 합본 {eps[0][0]:03d}~{eps[-1][0]:03d}화 "
         f"| 총 {total_chars:,}자(공백 포함) | {today} 기준 · 최신 {eps[0][0]:03d}~{eps[-1][0]:03d}화 동기화\n",
         "\n**로그라인** — 게이트에서 죽은 헌터들의 유품을 정리하던 F급 각성자 한겸. "
         "고인의 유언을 끝까지 집행하면, 고인의 힘이 그에게 '상속'된다. "
         "첫 의뢰는 국내 랭킹 1위, 검성 백무혁의 유품 정리 — 그런데 그 유언이 이상하다. "
         "\"나는, 몬스터에게 죽은 게 아니다.\"\n",
         "\n## 목차\n"]
ms_md += [f"- {n:03d}화 「{t.split('. ', 1)[-1]}」" for n, t, _, _c in eps]
for n, t, b, _c in eps:
    ms_md.append(f"\n\n---\n\n# {t}\n\n{b}")
(OUTDIR / MS_MD_NAME).write_text("\n".join(ms_md), encoding="utf-8")

(NOVEL / "bible" / "STATUS.md").write_text(STATUS_MD, encoding="utf-8")

doc_parts = [
    ("⭐ 현재 상태 (STATUS) — 자동 생성", STATUS_MD),
    ("프로젝트 개요", read(NOVEL / "README.md")),
    ("주제·윤리 바이블 (심장)", read(NOVEL / "bible" / "theme-ethics.md")),
    ("반전 설계 바이블 (척추)", read(NOVEL / "bible" / "twist-architecture.md")),
    ("세계관 바이블", read(NOVEL / "bible" / "world.md")),
    ("캐릭터 바이블", read(NOVEL / "bible" / "characters.md")),
    ("플롯 아웃라인 · 연재 로그", read(NOVEL / "bible" / "plot-outline.md")),
    ("떡밥 장부", read(NOVEL / "bible" / "foreshadowing.md")),
    ("문체 가이드", read(NOVEL / "bible" / "style-guide.md")),
    # 편집 리포트: 파일에서 자동 수집(번호 내림차순). ⚠ 손으로 목록을 유지하지 않는다 —
    # 하드코딩 목록과 표지의 REPORT_RANGE가 어긋나 #026이 통째로 누락된 적이 있다(28차 검수).
    *[(f"편집 리포트 #{n:03d} — {t}", body)
      for n, t, body in sorted(_REPORTS, key=lambda x: -x[0])],
    ("런칭: 제목 A/B 비교안", read(NOVEL / "launch" / "title-ab-test.md")),
    ("런칭: 작품 소개문", read(NOVEL / "launch" / "synopsis.md")),
    ("런칭: 표지 브리프", read(NOVEL / "launch" / "cover-brief.md")),
    ("런칭: 표지 디자인 철학", read(NOVEL / "launch" / "cover-philosophy.md")),
    ("런칭: 연재 운영 계획", read(NOVEL / "launch" / "operations.md")),
    ("리서치: 시장 플레이북", read(ROOT / "brain/wiki/topics/webnovel-market-playbook.md")),
    ("리서치: 흥행 공식", read(ROOT / "brain/wiki/topics/webnovel-hit-formula.md")),
    ("리서치: 캐릭터 패턴", read(ROOT / "brain/wiki/topics/webnovel-character-patterns.md")),
    ("리서치: 원본 덤프", read(ROOT / "brain/inbox/2026-08-01-webnovel-research-dump.md")),
]
doc_md = [f"# 「죽은 헌터의 유언을 집행합니다」 제작 문서 합본\n",
          f"> 바이블 · 떡밥 장부 · 편집 리포트 · 리서치 | {today} 기준\n", "\n## 목차\n"]
doc_md += [f"{i+1}. {name}" for i, (name, _) in enumerate(doc_parts)]
for i, (name, txt) in enumerate(doc_parts):
    doc_md.append(f"\n\n---\n\n# {i+1}. {name}\n\n{txt}")
(OUTDIR / "죽은헌터의유언을집행합니다_제작문서.md").write_text("\n".join(doc_md), encoding="utf-8")

# ══════════════ 2) PDF 공통 ══════════════
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("NBG", 7.5)
    canvas.setFillColor(SOFT)
    canvas.drawCentredString(A4[0] / 2, 12 * mm, f"- {canvas.getPageNumber()} -")
    canvas.setFillColor(SEAL)
    canvas.drawString(20 * mm, 285 * mm, "죽은 헌터의 유언을 집행합니다")
    canvas.setFillColor(SOFT)
    canvas.drawRightString(A4[0] - 20 * mm, 285 * mm, doc._vol_label)
    canvas.setStrokeColor(LINE); canvas.setLineWidth(0.4)
    canvas.line(20 * mm, 283 * mm, A4[0] - 20 * mm, 283 * mm)
    canvas.restoreState()

def make_doc(path, vol_label):
    d = SimpleDocTemplate(str(path), pagesize=A4,
                          leftMargin=24 * mm, rightMargin=24 * mm,
                          topMargin=22 * mm, bottomMargin=20 * mm,
                          title="죽은 헌터의 유언을 집행합니다", author="한겸 프로젝트")
    d._vol_label = vol_label
    return d

def cover(story, subtitle, lines):
    story.append(Spacer(1, 55 * mm))
    story.append(Paragraph("죽은 헌터의 유언을",
                 ParagraphStyle("c1", fontName="NMJ-B", fontSize=26, leading=38,
                                alignment=TA_CENTER, textColor=INK)))
    story.append(Paragraph("집행합니다",
                 ParagraphStyle("c2", fontName="NMJ-B", fontSize=26, leading=38,
                                alignment=TA_CENTER, textColor=INK)))
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="30%", thickness=1.2, color=SEAL, hAlign="CENTER"))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(subtitle, ParagraphStyle("c3", fontName="NBG", fontSize=10.5,
                                                    leading=16, alignment=TA_CENTER, textColor=SOFT)))
    story.append(Spacer(1, 60 * mm))
    for ln in lines:
        story.append(Paragraph(ln, ParagraphStyle("c4", fontName="NBG", fontSize=8.5,
                                                  leading=14, alignment=TA_CENTER, textColor=SOFT)))
    story.append(PageBreak())

# ══════════════ 3) 원고 PDF ══════════════
BOX = re.compile(r"^─{10,}\s*$")

def manuscript_flow(body):
    out, lines, i = [], body.split("\n"), 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1; continue
        if BOX.match(ln):
            i += 1; buf = []
            while i < len(lines) and not BOX.match(lines[i].rstrip()):
                buf.append(lines[i].strip()); i += 1
            i += 1
            content = "<br/>".join(wrap_hanja(escape(b)) for b in buf if b)
            tbl = Table([[Paragraph(content, S["sysbox"])]], colWidths=[95 * mm], hAlign="CENTER")
            tbl.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.8, SEAL),
                ("BACKGROUND", (0, 0), (-1, -1), PAPER2),
                ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
            out += [Spacer(1, 3), tbl, Spacer(1, 6)]
            continue
        st = ln.strip()
        if st == "⁂":
            out.append(Paragraph("⁂", S["scene"])); i += 1; continue
        style = S["ghost"] if st.startswith("『") else S["relay"] if st.startswith("─") else S["novel"]
        out.append(Paragraph(wrap_hanja(escape(st)), style)); i += 1
    return out

story = []
cover(story, f"원고 합본 · {eps[0][0]:03d}~{eps[-1][0]:03d}화 ({ARC_LABEL})",
      [f"총 {total_chars:,}자 (공백 포함) · 떡밥 장부 등록 {FS_REG}건 / 회수 {FS_DONE}건",
       f"{today} · 프로젝트 저장소 novel/ · PR #22", "",
       "이 원고는 초고이며, 무단 전재를 금합니다."])
for n, t, b, _c in eps:
    story.append(Paragraph(f"1부 「검성의 유언」 · 제{n}화", S["ep-eyebrow"]))
    story.append(Paragraph(wrap_hanja(escape(t)), S["ep-title"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE))
    story.append(Spacer(1, 6 * mm))
    story += manuscript_flow(b)
    if n != eps[-1][0]:
        story.append(PageBreak())
make_doc(OUTDIR / MS_PDF_NAME, "원고 합본").build(
    story, onFirstPage=lambda c, d: None, onLaterPages=footer)

# ══════════════ 4) 제작 문서 PDF ══════════════
def md_flow(txt):
    out = []
    if txt.startswith("---"):
        end = txt.find("\n---", 3)
        if end != -1:
            fm = txt[3:end].strip().replace("\n", "  ·  ")
            out.append(Paragraph(wrap_hanja(escape(fm)), S["meta"]))
            txt = txt[end + 4:]
    lines, i = txt.split("\n"), 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip(): i += 1; continue
        if ln.startswith("```"):
            i += 1; buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            content = "<br/>".join(wrap_hanja(escape(b).replace(" ", "&nbsp;")) for b in buf)
            out.append(Paragraph(content, S["pre"])); continue
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            lvl = min(len(m.group(1)), 3)
            out.append(Paragraph(inline(m.group(2)), S[f"h{lvl}"])); i += 1; continue
        if ln.strip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                r = lines[i].strip()
                if not re.match(r"^\|[\s\-|:]+\|$", r):
                    rows.append([c.strip() for c in r.strip("|").split("|")])
                i += 1
            if not rows: continue
            ncol = max(len(r) for r in rows)
            data = []
            for ri, r in enumerate(rows):
                r = r + [""] * (ncol - len(r))
                st = S["cellh"] if ri == 0 else S["cell"]
                data.append([Paragraph(inline(c), st) for c in r])
            avail = 162 * mm
            if ncol >= 5:
                w0 = 12 * mm
                rest = (avail - w0) / (ncol - 1)
                widths = [w0] + [rest] * (ncol - 1)
            else:
                widths = [avail / ncol] * ncol
            tbl = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
            tbl.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("BACKGROUND", (0, 0), (-1, 0), PAPER2),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]))
            out += [Spacer(1, 2), tbl, Spacer(1, 6)]
            continue
        if ln.strip().startswith(("- ", "* ")):
            while i < len(lines) and lines[i].strip().startswith(("- ", "* ")):
                out.append(Paragraph(inline(lines[i].strip()[2:]), S["li"], bulletText="·"))
                i += 1
            out.append(Spacer(1, 3)); continue
        if re.match(r"^\d+\.\s", ln.strip()):
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i].strip()):
                num, rest = lines[i].strip().split(".", 1)
                out.append(Paragraph(inline(rest.strip()), S["li"], bulletText=f"{num}."))
                i += 1
            out.append(Spacer(1, 3)); continue
        if ln.strip().startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(inline(lines[i].strip().lstrip("> "))); i += 1
            out.append(Paragraph("<br/>".join(buf), S["quote"])); continue
        if ln.strip() in ("---", "***") or re.match(r"^─{5,}\s*$", ln):
            out.append(HRFlowable(width="100%", thickness=0.4, color=LINE, spaceBefore=4, spaceAfter=6))
            i += 1; continue
        out.append(Paragraph(inline(ln.strip()), S["body"])); i += 1
    return out

story2 = []
cover(story2, f"제작 문서 합본 — 바이블 · 떡밥 장부 · 편집 리포트 합본({REPORT_RANGE}) · 런칭 준비물 · 리서치",
      [f"{today} 기준 · 원고 {eps[0][0]:03d}~{eps[-1][0]:03d}화 동기화 상태",
       "세션이 바뀌어도 이 문서만 읽으면 이어 쓸 수 있도록 설계된 장기기억 세트입니다."])
for i, (name, txt) in enumerate(doc_parts):
    story2.append(Paragraph(f"제{i+1}장", S["ep-eyebrow"]))
    story2.append(Paragraph(wrap_hanja(escape(name)), ParagraphStyle("doct", parent=S["ep-title"], fontName="NBG-B", fontSize=15)))
    story2.append(HRFlowable(width="100%", thickness=0.5, color=LINE))
    story2.append(Spacer(1, 4 * mm))
    story2 += md_flow(txt)
    if i != len(doc_parts) - 1:
        story2.append(PageBreak())
make_doc(OUTDIR / "죽은헌터의유언을집행합니다_제작문서.pdf", "제작 문서").build(
    story2, onFirstPage=lambda c, d: None, onLaterPages=footer)

for f in [MS_MD_NAME, "죽은헌터의유언을집행합니다_제작문서.md",
          MS_PDF_NAME, "죽은헌터의유언을집행합니다_제작문서.pdf"]:
    p = OUTDIR / f
    print(f"{f}: {p.stat().st_size:,} bytes")

# -*- coding: utf-8 -*-
import datetime as _dt
_TODAY = _dt.date.today().isoformat()
"""novel/ 원본 파일 → 단일 HTML 뷰어 생성기"""
import html as H
import re
from pathlib import Path
import os
from pathlib import Path as _P
_ROOT = os.environ.get("NOVEL_ROOT") or str(_P(__file__).resolve().parents[2])
_OUT  = os.environ.get("NOVEL_OUT")  or "/tmp/claude-0/-home-user-kotkim8210/c058c336-4e2b-5e83-9e93-9b4f05f88f8f/scratchpad"

ROOT = Path(_ROOT)
NOVEL = ROOT / "novel"
OUT = Path(f"{_OUT}/novel-viewer.html")

CUT_TYPES = {1: "절단 A · 정보", 2: "절단 B · 위기", 3: "절단 A · 정보", 4: "절단 C · 관계",
             5: "절단 C · 정서", 6: "절단 B · 위기", 7: "절단 A · 정보", 8: "절단 A · 정보",
             9: "절단 C · 관계", 10: "절단 A · 정보", 11: "절단 A · 반전",
             12: "절단 B · 위기", 13: "절단 C · 관계", 14: "절단 C · 정서",
             15: "절단 A · 정보", 16: "절단 A · 정보", 17: "절단 B · 위협",
             18: "절단 C · 관계", 19: "절단 B · 위협", 20: "절단 B · 위기",
             21: "절단 A · 정보", 22: "절단 C · 관계", 23: "절단 A · 반전", 24: "절단 A · 정보",
             25: "절단 B · 위협", 26: "절단 C · 관계", 27: "절단 A · 반전", 28: "절단 C · 예고", 29: "절단 B · 위협", 30: "절단 B · 위협", 31: "절단 A · 정보", 32: "절단 B · 위협", 33: "절단 A · 정보", 34: "절단 A · 반전", 35: "절단 C · 관계", 36: "절단 B · 추격", 37: "절단 A · 등장", 38: "절단 A · 반전", 39: "절단 A · 반전", 40: "절단 B · 위기", 41: "절단 A · 유언", 42: "절단 A · 선택", 43: "절단 B · 강적", 44: "절단 A · 반전", 45: "절단 C · 관계", 46: "절단 B · 위기", 47: "절단 A · 정보",
             48: "절단 B · 강적", 49: "절단 A · 반전", 50: "절단 A · 반전", 51: "절단 C · 선택", 52: "절단 B · 위기"}
_fs = __import__("pathlib").Path(f"{_ROOT}/novel/bible/foreshadowing.md").read_text(encoding="utf-8")
_fm = __import__("re").findall(r"등록\s*(\d+)\s*=\s*활성\s*(\d+)\s*/\s*회수\s*(\d+)", _fs)
FS_REG, FS_ACT, FS_DONE = _fm[-1] if _fm else ("?", "?", "?")
LAST_EP = max(int(f.stem) for f in __import__("pathlib").Path(f"{_ROOT}/novel/manuscript").glob("[0-9][0-9][0-9].md"))

# ---------- 인라인 포맷 ----------
def inline(s: str) -> str:
    s = H.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[\[([^\]]+)\]\]", r'<span class="wikilink">\1</span>', s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    return s

# ---------- 원고(소설) 변환 ----------
def render_manuscript(text: str) -> str:
    lines = text.split("\n")
    out, i, n = [], 0, len(lines)
    title = lines[0].lstrip("# ").strip()
    i = 1
    box_delim = re.compile(r"^─{10,}\s*$")
    while i < n:
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1; continue
        if box_delim.match(ln):  # 시스템 창
            i += 1; box = []
            while i < n and not box_delim.match(lines[i].rstrip()):
                box.append(lines[i].rstrip()); i += 1
            i += 1
            content = "<br>".join(H.escape(b.strip(), quote=False) for b in box if b.strip())
            out.append(f'<div class="sysbox" role="note">{content}</div>')
            continue
        if ln.strip() == "⁂":
            out.append('<div class="scene-break" aria-hidden="true">⁂</div>')
            i += 1; continue
        cls = ""
        st = ln.strip()
        if st.startswith("『"): cls = ' class="ghost"'
        elif st.startswith("─"): cls = ' class="relay"'
        out.append(f"<p{cls}>{inline(st)}</p>")
        i += 1
    return title, "\n".join(out)

# ---------- 일반 문서(md) 변환 ----------
def render_md(text: str) -> str:
    # 프런트매터 분리
    fm = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for l in text[3:end].strip().split("\n"):
                if ":" in l:
                    k, v = l.split(":", 1); fm[k.strip()] = v.strip()
            text = text[end + 4:]
    out = []
    if fm:
        chips = []
        for k in ("tags", "confidence", "status", "updated"):
            if k in fm: chips.append(f'<span class="chip">{H.escape(k)}: {H.escape(fm[k])}</span>')
        if chips: out.append('<div class="chiprow">' + "".join(chips) + "</div>")
    lines = text.split("\n"); i, n = 0, len(lines)
    in_details = False
    while i < n:
        ln = lines[i].rstrip()
        if not ln.strip(): i += 1; continue
        if ln.startswith("```"):  # 코드 펜스
            i += 1; buf = []
            while i < n and not lines[i].startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            out.append("<pre><code>" + H.escape("\n".join(buf)) + "</code></pre>")
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            lvl = min(len(m.group(1)) + 1, 4)
            txt = m.group(2)
            if "스포일러 금고" in txt and not in_details:
                out.append('<details class="vault"><summary>🔒 스포일러 금고 — 독자 미공개 진실 (펼치기)</summary>')
                in_details = True
            out.append(f"<h{lvl}>{inline(txt)}</h{lvl}>")
            i += 1; continue
        if ln.startswith("|"):  # 표
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip()); i += 1
            trs = []
            for ri, r in enumerate(rows):
                if re.match(r"^\|[\s\-|:]+\|$", r): continue
                cells = [c.strip() for c in r.strip("|").split("|")]
                tag = "th" if ri == 0 else "td"
                trs.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells) + "</tr>")
            out.append('<div class="tablewrap"><table>' + "".join(trs) + "</table></div>")
            continue
        if ln.strip().startswith(("- ", "* ")):
            items = []
            while i < n and lines[i].strip().startswith(("- ", "* ")):
                items.append(f"<li>{inline(lines[i].strip()[2:])}</li>"); i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        if ln.strip().startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(inline(lines[i].strip().lstrip("> "))); i += 1
            out.append("<blockquote><p>" + "<br>".join(buf) + "</p></blockquote>")
            continue
        if re.match(r"^─{5,}\s*$", ln) or ln.strip() in ("---", "***"):
            out.append("<hr>"); i += 1; continue
        out.append(f"<p>{inline(ln.strip())}</p>"); i += 1
    if in_details: out.append("</details>")
    return "\n".join(out)

# ---------- 데이터 수집 ----------
episodes = []
for ep in range(1, LAST_EP + 1):
    p = NOVEL / "manuscript" / f"{ep:03d}.md"
    raw = p.read_text(encoding="utf-8")
    # 자수 계측 canonical: 제목 줄("# ...")만 제외한 전체 문자 수(공백·빈 줄 포함) — measure.py / build_downloads.py와 동일 정의
    nchars = len("\n".join(l for l in raw.split("\n") if not l.startswith("# ")))
    title, htmlbody = render_manuscript(raw)
    episodes.append({"n": ep, "title": title, "html": htmlbody, "chars": nchars})

def doc(path, sid, label, group):
    return {"id": sid, "label": label, "group": group,
            "html": render_md((NOVEL / path).read_text(encoding="utf-8")
                              if not str(path).startswith("brain") else (ROOT / path).read_text(encoding="utf-8"))}

docs = [
    doc("bible/theme-ethics.md", "theme", "주제·윤리 = 심장 ⭐", "바이블"),
    doc("bible/twist-architecture.md", "twist", "반전 설계 = 척추 ⭐", "바이블"),
    doc("bible/world.md", "world", "세계관 · 캐논", "바이블"),
    doc("bible/characters.md", "chars", "캐릭터", "바이블"),
    doc("bible/plot-outline.md", "plot", "플롯 · 연재 로그", "바이블"),
    doc("bible/foreshadowing.md", "fore", "떡밥 장부 ⭐", "바이블"),
    doc("bible/style-guide.md", "style", "문체 가이드", "바이블"),
    doc("launch/title-ab-test.md", "l1", "제목 A/B 비교안", "런칭"),
    doc("launch/synopsis.md", "l2", "작품 소개문", "런칭"),
    doc("launch/cover-brief.md", "l3", "표지 브리프", "런칭"),
    doc("launch/cover-philosophy.md", "l5", "표지 디자인 철학 · 의장(儀裝)", "런칭"),
    doc("launch/operations.md", "l4", "연재 운영 계획", "런칭"),
    doc("editorial/edit-report-017.md", "edit17", "편집 리포트 #017 · 10차 검수: 결제 절단 4대 수정", "편집"),
    doc("editorial/edit-report-018.md", "edit18", "편집 리포트 #018 · 11차 검수 전건 반영 + 037·038", "편집"),
    doc("editorial/edit-report-019.md", "edit19", "편집 리포트 #019 · 12차 검수: 전투 참석자 동선", "편집"),
    doc("editorial/edit-report-020.md", "edit20", "편집 리포트 #020 · 13차 검수 + 039 집필", "편집"),
    doc("editorial/edit-report-025.md", "edit25", "편집 리포트 #025 · 052 집필(F01 시스템 규칙화) ⭐최신 기준", "편집"),
    doc("editorial/edit-report-024.md", "edit24", "편집 리포트 #024 · 051 집필(A5 후반 개시)", "편집"),
    doc("editorial/edit-report-023.md", "edit23", "편집 리포트 #023 · 045~050 집필(A5 전반부)", "편집"),
    doc("editorial/edit-report-022.md", "edit22", "편집 리포트 #022 · 16차 검수 반영·최종 동기화", "편집"),
    doc("editorial/edit-report-021.md", "edit21", "편집 리포트 #021 · A4 사건부 종결(040~043)", "편집"),
    doc("editorial/edit-report-016.md", "edit16", "편집 리포트 #016 · 훈훈함 계측·배치 ⭐", "편집"),
    doc("editorial/edit-report-015.md", "edit15", "편집 리포트 #015 · 톤 완급·피식 설계 ⭐", "편집"),
    doc("editorial/edit-report-014.md", "edit14", "편집 리포트 #014 · 루즈함·철학 과잉 점검 ⭐", "편집"),
    doc("editorial/edit-report-013.md", "edit13", "편집 리포트 #013 · 상업 검수·전수 절단 감사 ⭐", "편집"),
    doc("editorial/edit-report-012.md", "edit12", "편집 리포트 #012 · 가독성 지침·자동 자가검수 ⭐", "편집"),
    doc("editorial/edit-report-011.md", "edit11", "편집 리포트 #011 · 7차 리뷰: 캐논·연속성 교정 ⭐", "편집"),
    doc("editorial/edit-report-010.md", "edit10", "편집 리포트 #010 · 6차 리뷰: 정돈 방지·봉인 절차 ⭐", "편집"),
    doc("editorial/edit-report-009.md", "edit9", "편집 리포트 #009 · 5차 리뷰: 29화 수정·A4 속행 ⭐", "편집"),
    doc("editorial/edit-report-008.md", "edit8", "편집 리포트 #008 · 4차 리뷰: 강령 개정·가치 증량 ⭐", "편집"),
    doc("editorial/edit-report-007.md", "edit7", "편집 리포트 #007 · 증량 완결 검수 ⭐", "편집"),
    doc("editorial/edit-report-006.md", "edit6", "편집 리포트 #006 · 주제·반전 레이어 ⭐", "편집"),
    doc("editorial/edit-report-005.md", "edit5", "편집 리포트 #005 · A3 완결 검수", "편집"),
    doc("editorial/edit-report-004.md", "edit4", "편집 리포트 #004 · 통합 리듬 점검", "편집"),
    doc("editorial/edit-report-003.md", "edit3", "편집 리포트 #003 · 3차 편집", "편집"),
    doc("editorial/edit-report-002.md", "edit2", "편집 리포트 #002 · 2차 구조 편집", "편집"),
    doc("editorial/edit-report-001.md", "edit", "편집 리포트 #001 · 1차 퇴고", "편집"),
    doc("brain/wiki/topics/webnovel-market-playbook.md", "r1", "시장 플레이북", "리서치"),
    doc("brain/wiki/topics/webnovel-hit-formula.md", "r2", "흥행 공식", "리서치"),
    doc("brain/wiki/topics/webnovel-character-patterns.md", "r3", "캐릭터 패턴", "리서치"),
    doc("brain/inbox/2026-08-01-webnovel-research-dump.md", "r4", "리서치 원본 덤프", "리서치"),
]

total_chars = sum(e["chars"] for e in episodes)

# ---------- 내비게이션 ----------
nav = ['<div class="navgroup">프로젝트</div>',
       '<button class="navlink active" data-view="home">개요 · 대시보드</button>',
       '<div class="navgroup">원고 — 1부</div>']
for e in episodes:
    nav.append(f'<button class="navlink ep" data-view="ep{e["n"]}">'
               f'<span class="epnum">{e["n"]:03d}</span> {H.escape(e["title"].split(". ",1)[-1])}</button>')
groups = {}
for d in docs: groups.setdefault(d["group"], []).append(d)
for g, items in groups.items():
    nav.append(f'<div class="navgroup">{H.escape(g)}</div>')
    for d in items:
        nav.append(f'<button class="navlink" data-view="{d["id"]}">{H.escape(d["label"])}</button>')
NAV = "\n".join(nav)

# ---------- 뷰 ----------
views = []
home = f"""
<section class="view active" id="view-home">
  <div class="workmark"><span class="seal" aria-hidden="true">執行</span>
    <div><p class="eyebrow">웹소설 수익화 프로젝트 · 남성향 현대판타지 헌터물</p>
    <h1>죽은 헌터의 유언을<br>집행합니다</h1></div></div>
  <p class="logline">게이트에서 죽은 헌터들의 유품을 정리하던 F급 각성자 한겸.
  고인의 유언을 끝까지 집행하면, 고인의 힘이 그에게 '상속'된다.
  첫 의뢰는 국내 랭킹 1위, 검성 백무혁의 유품 정리 — 그런데 그 유언이 이상하다.</p>
  <blockquote class="hook"><p>"나는, 몬스터에게 죽은 게 아니다."</p></blockquote>
  <div class="statrow">
    <div class="stat"><span class="num">{len(episodes)}</span><span class="lbl">집필 회차</span></div>
    <div class="stat"><span class="num">{total_chars:,}</span><span class="lbl">총 글자수</span></div>
    <div class="stat"><span class="num">{FS_REG}</span><span class="lbl">떡밥 등록 · 회수 {FS_DONE}</span></div>
    <div class="stat"><span class="num">A5</span><span class="lbl">서린의 진실 아크 진행</span></div>
  </div>
  <img class="cover" src="data:image/jpeg;base64,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IIIakBaP2ZKvt5Hsu0/5IKpqLJKoIKIIaoIaYIaJIIIpobJJY67YZLIIppYIJrYKoIJoJ55pI6IbprPOMMJq03rd/wDv8PFY3lfd93WaeSKaKO62OWeuq3LbV/rNgvah5XlaPPE33Zpz9e+a+uWq+a+iyymy+hFetdurJ++jd+/Vtf8ArkfitfnhtqvrnsnnvimomntmotpirsuuvmjqkousvlrpgltgsorhshlgggggghghsgkopnjuksvqgDtkljoqhogogkgggjhtqtpijgYZQTWXTbZaeVhWZXdQfngnhmlohnjrrululqjvrvhvnrphrOOtwvoljrihviinvrvrkvsvktmvlimlvqsoigujABystnsvvtsvlrusvvqqssqkurgohlgkptoqmltvrlrlsggmkmvkssskstgojggkhhqqgiqokmvvpkupJugkrkghgpkkhkgohljuuhnvrgtjhhnhtlruCrgBEmvjrhjppqhjpjmjvuntqqrsuurvvvurqvBrlZoOEjnvnmjjvtprstvtjskqlsluhkspgrokAiiRSkoHghuukgksmgolsgkioiihjgriookhmiiELARepEAooihhlpgokoqhigqjvsjmruqrnjmupgCCCNdlCOBotrtkvnmprnrqmmorspsujvrqkiltkGCNAFhGGDmtltvjrsrsuqmsqhkigksggioghqioKAPCPFHLJogggppskggumtqjuopikrgvmijjitpCIDMLFHJBhhhmhunggrjihhtvsvtpunrgpjvpvuHKDHuNNBMvsuvrvunvhrupjktktruotmkiugqhEBJHttEMLGItprjruplqmjhtjiigphpsimkoiniDGJNnoACPJLipjqogogstlggvhlhntvnvvhvlhnNGtDmvNtlghptnskntvjvhrjtunuuvotnntukqrKCknnFmolPpusrivukumsilussugpikkosqsghpmqphP8pukmtggsmkkipghgpuiojpphninimiuulphmibTDsmhOohjiljhhiqjhiuusvnnvtrlqujCHAmhDVzVvmnAtPvuvrvjnvqttustisgsoEGBGFHJusjtcoklgsEkLBJlhhrtpnIogBiAngIOgOMAMPBInnljojmFMFOCkmHoIHkAAhgDELLKLDHDvDPJPFILBNCFBFKCPNHJHJJDPFL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" alt="표지 시안 — 부러진 검의 단면에서 새어 나오는 빛">
  <h3>2차 구조 편집 반영 (외부 리뷰 대응)</h3>
  <ul>
    <li><strong>핵심 순환 조기 증명</strong> — 5화에 박정후 유언 완전 집행·첫 성불 신설. '사연→집행→해소→상속'이 5화 안에 완결.</li>
    <li><strong>3화 전투 재작성</strong> — 승리가 아니라 봉인 경보로 3분을 벌고 부상을 입는 생존전으로. 적의 유능함 보존.</li>
    <li><strong>6화 재설계</strong> — 규정전은 '이틀 유예'만, 긴급 봉인으로 유품이 못 박혀 방화의 표적이 되는 인과 구축. 살수는 제3세력로 분리.</li>
    <li><strong>7화 떡밥 다이어트</strong> — 대기열·40분 단서를 8화로 이월, 서린의 질책으로 주인공 결함(독단) 서사 가동.</li>
  </ul>
  <h3>전략 요약 (리서치 근거)</h3>
  <ul>
    <li><strong>장르 선택</strong> — 판타지 선호 45.7%로 최대 시장, '헌터'가 최다 검색 직업 키워드. 나혼렙 이후 웹툰화 파이프라인이 가장 검증된 구간.</li>
    <li><strong>차별화</strong> — 능력 흡수물의 사이다에 <strong>한풀이·성불(눈물 코드)</strong>를 결합. 법률 문체 시스템창 · 죽은 자 존대 · 전투 전 묵례 = 웹툰화 대비 시그니처.</li>
    <li><strong>수익 경로</strong> — 문피아 자유연재 → 유료화(편당 100원) → 카카오페이지 런칭 → 웹툰화. IP 확장 시 원작 매출 230배 사례(재벌집 막내아들).</li>
  </ul>
  <h3>다음 단계</h3>
  <ul>
    <li>✅ A2 완결 · 통합 점검(#004) 통과 · 런칭 준비물 4종 완비(좌측 '런칭' 탭)</li>
    <li>✅ 주제·반전 설계층 완비 — 중심 질문 "죽은 사람의 뜻은 산 사람의 삶보다 무거운가", 확정 반전 T1~T5</li>
    <li>✅ 원고 29화 · 표지 시안 v2 · 런칭 문서 5종 — 남은 조건: 21~28화 증량, 계정/필명(사용자 결정)</li>
  </ul>
  <p class="meta">저장소 <code>novel/</code> · 브랜치 <code>claude/novel-writer-monetization-gvh2bt</code> ·
  <a href="https://github.com/kotkim8210/kotkim8210/pull/22" target="_blank" rel="noopener">PR #22 (드래프트)</a></p>
</section>"""
views.append(home)

for idx, e in enumerate(episodes):
    prevb = (f'<button class="pager" data-view="ep{e["n"]-1}">← {e["n"]-1:03d}화</button>'
             if idx > 0 else '<button class="pager" data-view="home">← 개요</button>')
    nextb = (f'<button class="pager" data-view="ep{e["n"]+1}">{e["n"]+1:03d}화 →</button>'
             if idx < len(episodes) - 1 else '<button class="pager" data-view="edit2">편집 리포트 →</button>')
    views.append(f"""
<section class="view" id="view-ep{e['n']}">
  <header class="ephead">
    <p class="eyebrow">1부 「검성의 유언」 · 제{e['n']}화</p>
    <h2>{H.escape(e['title'])}</h2>
    <div class="chiprow"><span class="chip">{e['chars']:,}자</span><span class="chip">{CUT_TYPES.get(e['n'], '절단 ? · 미등재')}</span></div>
  </header>
  <div class="prose">{e['html']}</div>
  <nav class="pagernav">{prevb}{nextb}</nav>
</section>""")

for d in docs:
    views.append(f"""
<section class="view" id="view-{d['id']}">
  <header class="ephead"><p class="eyebrow">{H.escape(d['group'])}</p><h2>{H.escape(d['label'])}</h2></header>
  <div class="docbody">{d['html']}</div>
</section>""")
VIEWS = "\n".join(views)

# ---------- 템플릿 ----------
TEMPLATE = """<title>죽은 헌터의 유언을 집행합니다 — 프로젝트 뷰어</title>
<style>
:root{
  --paper:#F8F8F5; --paper2:#F0F0EA; --ink:#1C1D21; --ink-soft:#565863;
  --line:#E1E1D8; --seal:#A63A2B; --seal-soft:#A63A2B22; --ghost:#5B6B7E;
  --code:#EDEDE6;
}
@media (prefers-color-scheme: dark){
  :root{ --paper:#141519; --paper2:#1B1C22; --ink:#E7E6E1; --ink-soft:#9FA1AB;
    --line:#2A2B32; --seal:#D06B55; --seal-soft:#D06B5526; --ghost:#8FA1B5; --code:#22232B; }
}
:root[data-theme="dark"]{ --paper:#141519; --paper2:#1B1C22; --ink:#E7E6E1; --ink-soft:#9FA1AB;
  --line:#2A2B32; --seal:#D06B55; --seal-soft:#D06B5526; --ghost:#8FA1B5; --code:#22232B; }
:root[data-theme="light"]{ --paper:#F8F8F5; --paper2:#F0F0EA; --ink:#1C1D21; --ink-soft:#565863;
  --line:#E1E1D8; --seal:#A63A2B; --seal-soft:#A63A2B22; --ghost:#5B6B7E; --code:#EDEDE6; }
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  background:var(--paper); color:var(--ink);
  font-family:"Pretendard Variable",Pretendard,"Noto Sans KR","Apple SD Gothic Neo","Malgun Gothic",sans-serif;
  line-height:1.75; font-size:16px;
}
.layout{display:grid; grid-template-columns:248px 1fr; min-height:100vh}
/* ── 사이드바 ── */
.sidebar{
  border-right:1px solid var(--line); background:var(--paper2);
  padding:20px 14px 40px; position:sticky; top:0; height:100vh; overflow-y:auto;
}
.brand{font-weight:700; font-size:.95rem; letter-spacing:.02em; padding:4px 10px 14px;
  border-bottom:1px solid var(--line); margin-bottom:10px}
.brand small{display:block; color:var(--ink-soft); font-weight:500; font-size:.72rem; margin-top:2px}
.navgroup{font-size:.68rem; letter-spacing:.14em; text-transform:uppercase;
  color:var(--ink-soft); margin:16px 10px 6px}
.navlink{
  display:block; width:100%; text-align:left; border:0; background:none; color:var(--ink);
  font:inherit; font-size:.86rem; padding:6px 10px; border-radius:6px; cursor:pointer;
}
.navlink:hover{background:var(--seal-soft)}
.navlink.active{background:var(--seal); color:#FBF6F2; font-weight:600}
.navlink:focus-visible,.pager:focus-visible{outline:2px solid var(--seal); outline-offset:2px}
.epnum{font-variant-numeric:tabular-nums; color:var(--ink-soft); font-size:.74rem; margin-right:6px}
.navlink.active .epnum{color:#FBF6F2AA}
/* ── 본문 ── */
main{padding:48px clamp(20px,6vw,72px) 96px; min-width:0}
.view{display:none; max-width:41rem; margin:0 auto}
.view.active{display:block}
.eyebrow{font-size:.72rem; letter-spacing:.16em; text-transform:uppercase; color:var(--seal);
  margin:0 0 8px; font-weight:600}
h1{font-family:"Noto Serif KR","Nanum Myeongjo",AppleMyungjo,Batang,serif;
  font-size:clamp(1.7rem,4vw,2.4rem); line-height:1.3; margin:.1em 0 .4em; text-wrap:balance}
h2{font-family:"Noto Serif KR","Nanum Myeongjo",AppleMyungjo,Batang,serif;
  font-size:1.45rem; line-height:1.35; margin:.2em 0 .6em; text-wrap:balance}
h3{font-size:1.05rem; margin:2em 0 .6em}
h4{font-size:.95rem; margin:1.6em 0 .5em}
.workmark{display:flex; gap:18px; align-items:flex-start; margin-top:8px}
.seal{
  flex:none; width:58px; height:58px; border:2.5px solid var(--seal); color:var(--seal);
  border-radius:8px; display:flex; align-items:center; justify-content:center;
  font-family:"Noto Serif KR",serif; font-weight:700; font-size:1.15rem; letter-spacing:.1em;
  transform:rotate(-4deg); margin-top:10px; writing-mode:vertical-rl;
}
.logline{color:var(--ink-soft); margin:18px 0 6px}
.hook{border-left:3px solid var(--seal); margin:22px 0; padding:4px 0 4px 18px}
.hook p{font-family:"Noto Serif KR",serif; font-size:1.15rem; margin:0}
.cover{display:block; width:min(300px,64%); margin:26px auto 8px; border-radius:6px;
  border:1px solid var(--line); box-shadow:0 10px 30px rgba(0,0,0,.28)}
.statrow{display:grid; grid-template-columns:repeat(auto-fit,minmax(110px,1fr)); gap:10px; margin:28px 0 8px}
.stat{border:1px solid var(--line); border-radius:8px; padding:12px 14px; background:var(--paper2)}
.stat .num{display:block; font-size:1.4rem; font-weight:700; font-variant-numeric:tabular-nums}
.stat .lbl{font-size:.74rem; color:var(--ink-soft); letter-spacing:.06em}
.meta{color:var(--ink-soft); font-size:.85rem; border-top:1px solid var(--line); padding-top:16px; margin-top:36px}
/* ── 원고 조판 ── */
.ephead{margin-bottom:28px; padding-bottom:18px; border-bottom:1px solid var(--line)}
.prose{font-family:"Noto Serif KR","Nanum Myeongjo",AppleMyungjo,Batang,serif;
  font-size:1.02rem; line-height:2.0}
.prose p{margin:0 0 1.15em; text-align:justify}
.prose p.ghost{color:var(--ghost)}
.prose p.relay{color:var(--ink-soft)}
.scene-break{text-align:center; color:var(--ink-soft); letter-spacing:.5em; margin:2.2em 0; font-size:.9rem}
.sysbox{
  font-family:Pretendard,"Noto Sans KR",sans-serif; font-size:.86rem; line-height:1.9;
  border:1px solid var(--seal); border-radius:4px; padding:14px 18px; margin:1.6em auto;
  max-width:30rem; position:relative; background:var(--paper2); letter-spacing:.02em;
}
.sysbox::after{content:"印"; position:absolute; right:10px; bottom:6px; color:var(--seal);
  opacity:.35; font-family:"Noto Serif KR",serif; font-size:.8rem}
.pagernav{display:flex; justify-content:space-between; gap:12px; margin-top:44px;
  padding-top:20px; border-top:1px solid var(--line)}
.pager{border:1px solid var(--line); background:var(--paper2); color:var(--ink); font:inherit;
  font-size:.88rem; padding:9px 16px; border-radius:8px; cursor:pointer}
.pager:hover{border-color:var(--seal); color:var(--seal)}
/* ── 문서 ── */
.docbody blockquote{border-left:3px solid var(--line); margin:1em 0; padding:2px 0 2px 16px; color:var(--ink-soft)}
.docbody blockquote p{margin:0}
.tablewrap{overflow-x:auto; margin:1.2em 0; border:1px solid var(--line); border-radius:8px}
table{border-collapse:collapse; width:100%; font-size:.84rem; line-height:1.6}
th,td{padding:8px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; min-width:90px}
th{background:var(--paper2); font-size:.76rem; letter-spacing:.06em; white-space:nowrap}
tr:last-child td{border-bottom:0}
pre{background:var(--code); border-radius:8px; padding:14px 16px; overflow-x:auto;
  font-size:.82rem; line-height:1.7}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:.9em;
  background:var(--code); padding:.1em .35em; border-radius:4px}
pre code{background:none; padding:0}
.chiprow{display:flex; flex-wrap:wrap; gap:6px; margin:10px 0}
.chip{font-size:.72rem; border:1px solid var(--line); border-radius:999px; padding:2px 10px;
  color:var(--ink-soft); background:var(--paper2)}
.wikilink{color:var(--seal); border-bottom:1px dashed var(--seal)}
a{color:var(--seal)}
hr{border:0; border-top:1px solid var(--line); margin:2em 0}
details.vault{border:1px solid var(--seal); border-radius:8px; padding:12px 16px; margin:1.4em 0;
  background:var(--seal-soft)}
details.vault summary{cursor:pointer; font-weight:600; color:var(--seal)}
ul{padding-left:1.3em} li{margin:.35em 0}
/* ── 모바일 ── */
.topbar{display:none}
@media (max-width:840px){
  .layout{grid-template-columns:1fr}
  .sidebar{display:none}
  .topbar{display:block; position:sticky; top:0; z-index:5; background:var(--paper2);
    border-bottom:1px solid var(--line); padding:10px 14px}
  .topbar select{width:100%; font:inherit; font-size:.9rem; padding:8px 10px;
    border:1px solid var(--line); border-radius:8px; background:var(--paper); color:var(--ink)}
  main{padding:28px 18px 80px}
}
@media (prefers-reduced-motion:no-preference){
  .view.active{animation:fadein .25s ease}
  @keyframes fadein{from{opacity:0; transform:translateY(4px)}to{opacity:1; transform:none}}
}
</style>

<div class="layout">
  <aside class="sidebar">
    <div class="brand">죽은 헌터의 유언을<br>집행합니다<small>프로젝트 뷰어 · {_TODAY}</small></div>
    <nav aria-label="문서 목록">@@NAV@@</nav>
  </aside>
  <div>
    <div class="topbar"><select id="mobilenav" aria-label="문서 선택">@@OPTIONS@@</select></div>
    <main>@@VIEWS@@</main>
  </div>
</div>

<script>
(function(){
  var links = Array.prototype.slice.call(document.querySelectorAll('.navlink'));
  var sel = document.getElementById('mobilenav');
  function show(id){
    document.querySelectorAll('.view').forEach(function(v){v.classList.remove('active')});
    var el = document.getElementById('view-'+id);
    if(!el) return;
    el.classList.add('active');
    links.forEach(function(l){
      var on = l.getAttribute('data-view')===id;
      l.classList.toggle('active', on);
      if(on) l.setAttribute('aria-current','page'); else l.removeAttribute('aria-current');
    });
    if(sel) sel.value = id;
    window.scrollTo({top:0});
  }
  document.addEventListener('click', function(e){
    var b = e.target.closest('[data-view]');
    if(b){ show(b.getAttribute('data-view')); }
  });
  if(sel) sel.addEventListener('change', function(){ show(sel.value); });
})();
</script>
"""

# 모바일 select 옵션
opts = ['<option value="home">개요 · 대시보드</option>']
for e in episodes:
    opts.append(f'<option value="ep{e["n"]}">{e["n"]:03d}화 — {H.escape(e["title"].split(". ",1)[-1])}</option>')
for d in docs:
    opts.append(f'<option value="{d["id"]}">[{H.escape(d["group"])}] {H.escape(d["label"])}</option>')

page = (TEMPLATE.replace("@@NAV@@", NAV)
                .replace("@@OPTIONS@@", "\n".join(opts))
                .replace("@@VIEWS@@", VIEWS))
OUT.write_text(page, encoding="utf-8")
nviews = page.count('<section class="view')
print(f"OK {OUT} ({len(page):,} bytes, views={nviews})")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
쿠팡 제습기 아이템위너 소싱 시트 생성기 (v2 — 국내최저 소싱처 반영).
- 다나와 '국내 최저가 소싱처'(해외배송·품절·카드전용 제외)를 실조회해 소싱가/판매처명/URL 기입.
- 마진 관련 열 + 소싱처 열을 앞쪽에 배치. 쿠팡 위너가만 입력하면 마진/등급 자동계산.
data.json: {"generated_kst":"...","models":[{... , sourcingSeller, sourcingPrice, sourcingUrl, sourcingNote}], "raw":[...]}
"""
import json, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.worksheet.datavalidation import DataValidation

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
OUT = os.path.join(HERE, "쿠팡_제습기_소싱_마진시트.xlsx")
models = DATA["models"]
gen = DATA.get("generated_kst", "")

FEE = 0.12 + 0.01 + 0.03 + 0.01  # 0.17

# 스타일
NAVY="1F3864"; BLUE="2E5496"; YEL="FFF2CC"; GREEN="E2EFDA"; GOLD="FCE4D6"; SRC="FFE699"
hdr_font=Font(bold=True,color="FFFFFF",size=10,name="맑은 고딕")
cell_font=Font(size=10,name="맑은 고딕")
thin=Side(style="thin",color="BFBFBF")
border=Border(left=thin,right=thin,top=thin,bottom=thin)
center=Alignment(horizontal="center",vertical="center",wrap_text=True)
left=Alignment(horizontal="left",vertical="center",wrap_text=True)
right=Alignment(horizontal="right",vertical="center")

wb=Workbook()
ws=wb.active; ws.title="소싱_마진시트"

# (헤더, 폭, 그룹, 입력여부)  그룹: M=마진 SRC=소싱처 IN=쿠팡입력 DN=다나와 ID=식별 REF=참고
COLS=[
 ("순위",6,"M",False),
 ("등급\n(자동)",8,"M",False),
 ("예상마진(원)\n위너가 입력시",13,"M",False),
 ("마진율(%)",9,"M",False),
 ("손익분기\n위너가(원)",11,"M",False),
 ("8%마진\n목표위너가",11,"M",False),
 ("12%마진\n목표위너가",11,"M",False),
 ("① [입력]\n쿠팡 위너가격",13,"IN",True),
 ("② 국내최저\n소싱가(원)",12,"SRC",False),
 ("🏪 국내최저\n소싱처",14,"SRC",False),
 ("🔗 소싱처 URL\n(다나와 가격비교)",30,"SRC",False),
 ("소싱 비고\n(쿠팡최저=마진X 등)",20,"SRC",False),
 ("③ [입력]\n판매자택배비",11,"IN",True),
 ("브랜드",10,"ID",False),
 ("정확한 모델번호",18,"ID",False),
 ("상품명",28,"ID",False),
 ("용량(L)",7,"ID",False),
 ("주요기능/사용처",18,"ID",False),
 ("다나와\n판매처수",8,"DN",False),
 ("④ [입력]\n신품 판매자수",10,"IN",True),
 ("⑤ [입력]\n위너 배송형태",12,"IN",True),
 ("⑥ [입력]\n쿠팡 상품평수",10,"IN",True),
 ("⑦ [입력]\n최근리뷰(Y/N)",10,"IN",True),
 ("⑧ [입력]\n2위 판매자가",11,"IN",True),
 ("⑨ [입력]\n쿠팡 상품 URL",24,"IN",True),
 ("쿠팡 인기신호(리드,미검증)",28,"REF",False),
 ("위험/비고",22,"REF",False),
]
GROUP_FILL={"M":BLUE,"SRC":"BF8F00","IN":NAVY,"DN":"375623","ID":"595959","REF":"7F6000"}
NC=len(COLS)
# 컬럼 인덱스(1-base)
CI={"순위":1,"등급":2,"마진":3,"마진율":4,"BEP":5,"P8":6,"P12":7,"위너가":8,"소싱가":9,
    "소싱처":10,"소싱URL":11,"소싱비고":12,"택배비":13,"브랜드":14,"모델":15,"상품명":16,
    "용량":17,"기능":18,"다나와판매처":19,"신품판매자":20,"위너배송":21,"상품평":22,
    "최근리뷰":23,"이위가":24,"쿠팡URL":25,"신호":26,"위험":27}
def CL(k): return get_column_letter(CI[k])

# 배너
ws.merge_cells(start_row=1,start_column=1,end_row=1,end_column=NC)
b=ws.cell(1,1)
b.value=("⚠ 초록(다나와 국내최저 소싱처·소싱가·마진목표가)=실조회 데이터.  "
         "노랑(①쿠팡위너가 ④판매자수 ⑤배송형태 ⑥상품평 ⑦최근리뷰 ⑧2위가 ⑨URL)=쿠팡 봇차단으로 미취득 → 로그인 상태서 직접 입력.  "
         "소싱처는 해외배송·품절·카드전용가 제외한 국내 최저가.  '사용법_및_한계' 탭 필독.")
b.font=Font(bold=True,color="9C0006",size=10,name="맑은 고딕")
b.fill=PatternFill("solid",fgColor="FFF2CC"); b.alignment=left
ws.row_dimensions[1].height=42

ws.merge_cells(start_row=2,start_column=1,end_row=2,end_column=NC)
b2=ws.cell(2,1)
b2.value=(f"조사기준(KST): {gen}  |  비용모델: 판매가의 17%(수수료12+결제1+위험3+운영1)+택배비  |  "
          f"손익분기위너가=소싱가/0.83  |  ★위너경쟁=최저가싸움 → 가장 싼 국내 소싱처(🏪열)가 핵심")
b2.font=Font(italic=True,size=9,color="404040",name="맑은 고딕"); b2.alignment=left
ws.row_dimensions[2].height=16

HDR=3
for j,(name,w,grp,isin) in enumerate(COLS,1):
    c=ws.cell(HDR,j,name); c.font=hdr_font; c.fill=PatternFill("solid",fgColor=GROUP_FILL[grp])
    c.alignment=center; c.border=border
    ws.column_dimensions[get_column_letter(j)].width=w
ws.row_dimensions[HDR].height=34
ws.freeze_panes="H4"  # A~G(마진) 고정

r0=HDR+1
for idx,m in enumerate(models):
    r=r0+idx
    # 소싱가: 국내최저 소싱가 있으면 그것, 없으면 다나와 검색최저가
    src_price=m.get("sourcingPrice") or 0
    buy = src_price if src_price else (m.get("danawaLowestPrice") or 0)
    W=f"{CL('위너가')}{r}"; I=f"{CL('소싱가')}{r}"; SH=f"{CL('택배비')}{r}"
    D=f"{CL('마진율')}{r}"; R=f"{CL('신품판매자')}{r}"; SS=f"{CL('위너배송')}{r}"; T=f"{CL('상품평')}{r}"
    # 등급 자동
    ws.cell(r,CI["등급"],
        f'=IF(OR({W}="",{I}=""),"위너가입력필요",'
        f'IF(OR({R}="",{SS}="",{T}=""),"쿠팡검증필요",'
        f'IF(OR({SS}="로켓그로스",{R}<2,{T}<30,{D}<5),"제외",'
        f'IF(AND({R}>=2,{SS}="일반",{T}>=100,{D}>=12),"S",'
        f'IF(AND({R}>=2,{SS}="일반",{T}>=50,{D}>=8),"A",'
        f'IF(AND({T}>=30,{R}>=2,{D}>=5),"B","C"))))))')
    ws.cell(r,CI["마진"], f'=IF({W}="","",ROUND({W}-{I}-{W}*{FEE}-{SH},0))')
    ws.cell(r,CI["마진율"], f'=IF(OR({W}="",{W}=0),"",ROUND({CL("마진")}{r}/{W}*100,1))')
    # 손익분기/8%/12% 목표 위너가 — 소싱가 기준 정적값(즉시 표시)
    if buy:
        ws.cell(r,CI["BEP"],round(buy/(1-FEE)))
        ws.cell(r,CI["P8"],round(buy/(1-FEE-0.08)))
        ws.cell(r,CI["P12"],round(buy/(1-FEE-0.12)))
    ws.cell(r,CI["위너가"],None)
    ws.cell(r,CI["소싱가"], buy if buy else None)
    ws.cell(r,CI["소싱처"], m.get("sourcingSeller","") or "(미확인)")
    ws.cell(r,CI["소싱URL"], m.get("sourcingUrl","") or m.get("danawaSearchUrl",""))
    ws.cell(r,CI["소싱비고"], m.get("sourcingNote",""))
    ws.cell(r,CI["택배비"],0)
    ws.cell(r,CI["브랜드"],m.get("brand",""))
    ws.cell(r,CI["모델"],m.get("modelNumber",""))
    ws.cell(r,CI["상품명"],m.get("productName",""))
    ws.cell(r,CI["용량"],m.get("capacityL",""))
    ws.cell(r,CI["기능"],m.get("keyFeatures",""))
    ws.cell(r,CI["다나와판매처"],m.get("sellerCount",""))
    for k in ["신품판매자","위너배송","상품평","최근리뷰","이위가","쿠팡URL"]:
        ws.cell(r,CI[k],None)
    ws.cell(r,CI["신호"],m.get("coupangPopularitySignal",""))
    ws.cell(r,CI["위험"],m.get("riskNotes","") or m.get("notes",""))
    # 스타일
    for j in range(1,NC+1):
        c=ws.cell(r,j); c.border=border; c.font=cell_font
        grp=COLS[j-1][2]; isin=COLS[j-1][3]
        if isin: c.fill=PatternFill("solid",fgColor=YEL)
        elif grp=="M": c.fill=PatternFill("solid",fgColor=GREEN)
        elif grp=="SRC": c.fill=PatternFill("solid",fgColor=SRC)
        elif grp=="DN": c.fill=PatternFill("solid",fgColor="F2F7EE")
        else: c.fill=PatternFill("solid",fgColor="FFFFFF")
        if j in (CI["마진"],CI["BEP"],CI["P8"],CI["P12"],CI["위너가"],CI["소싱가"],CI["이위가"]):
            c.alignment=right; c.number_format='#,##0'
        elif j==CI["마진율"]:
            c.alignment=right; c.number_format='0.0'
        elif j in (CI["상품명"],CI["기능"],CI["소싱처"],CI["소싱URL"],CI["소싱비고"],CI["쿠팡URL"],CI["신호"],CI["위험"]):
            c.alignment=left
        else: c.alignment=center
    ws.row_dimensions[r].height=30

last=r0+len(models)-1
# 위너가 주석
ws.cell(r0,CI["위너가"]).comment=Comment("쿠팡(로그인)에서 이 모델 아이템위너 판매가를 입력. 입력 즉시 마진/등급 자동계산.","소싱봇")
ws.cell(r0,CI["소싱처"]).comment=Comment("해외배송·품절·카드전용가 제외한 다나와 국내 최저가 판매처. 위너경쟁은 최저가 싸움이므로 여기가 핵심.","소싱봇")

# 조건부 서식
mc=f"{CL('마진')}{r0}:{CL('마진')}{last}"
ws.conditional_formatting.add(mc,CellIsRule(operator="greaterThanOrEqual",formula=["10"],fill=PatternFill("solid",fgColor="C6EFCE"),font=Font(color="006100",bold=True,name="맑은 고딕")))
ws.conditional_formatting.add(mc,CellIsRule(operator="lessThan",formula=["10"],fill=PatternFill("solid",fgColor="FFC7CE"),font=Font(color="9C0006",name="맑은 고딕")))
dc=f"{CL('마진율')}{r0}:{CL('마진율')}{last}"
ws.conditional_formatting.add(dc,CellIsRule(operator="greaterThanOrEqual",formula=["12"],fill=PatternFill("solid",fgColor="63BE7B")))
ws.conditional_formatting.add(dc,CellIsRule(operator="between",formula=["8","11.999"],fill=PatternFill("solid",fgColor="C6EFCE")))
ws.conditional_formatting.add(dc,CellIsRule(operator="between",formula=["5","7.999"],fill=PatternFill("solid",fgColor="FFEB9C")))
ws.conditional_formatting.add(dc,CellIsRule(operator="lessThan",formula=["5"],fill=PatternFill("solid",fgColor="FFC7CE")))
bc=f"{CL('등급')}{r0}:{CL('등급')}{last}"
ws.conditional_formatting.add(bc,FormulaRule(formula=[f'OR({CL("등급")}{r0}="S",{CL("등급")}{r0}="A")'],fill=PatternFill("solid",fgColor="63BE7B"),font=Font(bold=True,color="FFFFFF",name="맑은 고딕")))
ws.conditional_formatting.add(bc,FormulaRule(formula=[f'{CL("등급")}{r0}="B"'],fill=PatternFill("solid",fgColor="FFEB9C")))
ws.conditional_formatting.add(bc,FormulaRule(formula=[f'{CL("등급")}{r0}="제외"'],fill=PatternFill("solid",fgColor="FFC7CE"),font=Font(color="9C0006",name="맑은 고딕")))
# 소싱비고에 '쿠팡최저' 포함시 소싱처 빨강 강조
sc=f"{CL('소싱처')}{r0}:{CL('소싱처')}{last}"
ws.conditional_formatting.add(sc,FormulaRule(formula=[f'ISNUMBER(SEARCH("쿠팡",{CL("소싱비고")}{r0}))'],fill=PatternFill("solid",fgColor="FFC7CE"),font=Font(color="9C0006",bold=True,name="맑은 고딕")))

# 드롭다운
dv=DataValidation(type="list",formula1='"일반,로켓그로스"',allow_blank=True); ws.add_data_validation(dv); dv.add(f"{CL('위너배송')}{r0}:{CL('위너배송')}{last}")
dv2=DataValidation(type="list",formula1='"Y,N"',allow_blank=True); ws.add_data_validation(dv2); dv2.add(f"{CL('최근리뷰')}{r0}:{CL('최근리뷰')}{last}")

# ---- Sheet2: 사용법 ----
ws2=wb.create_sheet("사용법_및_한계")
ws2.column_dimensions["A"].width=3; ws2.column_dimensions["B"].width=112
guide=[
 ("H1","⚠ 이 시트로 무엇이 되고, 무엇이 안 되는가 (반드시 읽기)"),("P",""),
 ("H2","1. 자동으로 채워진 것 (실제 조회 데이터)"),
 ("P","• 🏪 국내최저 소싱처 / 소싱가 / 소싱처 URL — 다나와 가격비교 실조회. 해외배송·해외직구·품절·카드전용가는 제외한 국내 최저가."),
 ("P","• 손익분기/8%/12% 목표 위너가 — 소싱가 기준 자동계산(어떤 뷰어에서도 즉시 표시)."),
 ("P","• '소싱 비고'에 '쿠팡최저'가 뜨면(빨강) 다나와 최저가가 쿠팡 자신이라 매입-재판매 마진이 사실상 없음 → 우선 제외."),
 ("P",""),
 ("H2","2. 비워둔 것 (쿠팡 봇차단으로 자동취득 불가 — 노란칸 ①④⑤⑥⑦⑧⑨)"),
 ("P","• 쿠팡 위너가격 / 신품 판매자수 / 위너 배송형태 / 상품평수 / 최근리뷰 / 2위가 / 상품 URL."),
 ("P","• 이유: 이 환경에서 쿠팡은 403 + 실브라우저 연결리셋(Akamai 봇차단, 데이터센터 IP). 로그인 자격증명 없음."),
 ("P","• 지침(추정금지·판매자수 확인불가 제외)상 이 값들은 지어내지 않았다."),
 ("P",""),
 ("H2","3. 사용법 — 위너경쟁은 최저가 싸움"),
 ("P","① 쿠팡(로그인)에서 모델번호로 검색 → 동일모델(스펙·KC 동일) 상세페이지."),
 ("P","② '다른 판매자 보기'로 신품 판매자수·위너 배송형태·위너가·2위가 확인 → 노란칸 입력."),
 ("P","③ 입력 즉시 등급/예상마진/마진율 자동. 예상마진 10원↑=초록, 손실=빨강."),
 ("P","④ 빠른 컷: 쿠팡 위너가가 'E열 손익분기 위너가'보다 낮으면 그 행은 스킵(마진 안 남음)."),
 ("P","⑤ 소싱은 🏪 국내최저 소싱처에서. '소싱비고=쿠팡최저'거나 카드전용가면 매입처로 부적합."),
 ("P",""),
 ("H2","4. 소싱 제외 규칙(반영됨)"),
 ("P","• 해외배송/해외직구 판매처 = 제외(판매자점수 하락 위험)."),
 ("P","• 품절 판매처 = 제외.  • 특정카드 전용가 = 정상 매입가로 불인정(비고 표시)."),
 ("P","• 렌탈·중고·리퍼·병행수입 = 제외."),
 ("P",""),
 ("H2","5. 마진/등급 계산"),
 ("P","예상마진 = 쿠팡위너가 − 소싱가 − 쿠팡위너가×17% − 판매자택배비.   손익분기위너가 = 소싱가/0.83, 8%=/0.75, 12%=/0.71."),
 ("P","제외: 위너=로켓그로스 or 판매자<2 or 상품평<30 or 마진율<5.  S:판매자≥2·일반·평≥100·마진율≥12  A:평≥50·마진율≥8  B:평≥30·마진율≥5."),
 ("P",""),
 ("H2","6. 쿠팡 데이터 취득 방법"),
 ("P","(a) 사장님 PC/폰(가정용 IP)+쿠팡 로그인 직접확인(무료·정확)  (b) 아이템스카우트/판다랭크/셀러라이프(유료)  (c) 주거용 프록시 크롤러(별도환경)."),
]
rr=1
for kind,text in guide:
    c=ws2.cell(rr,2,text)
    if kind=="H1": c.font=Font(bold=True,size=13,color="9C0006",name="맑은 고딕")
    elif kind=="H2": c.font=Font(bold=True,size=11,color="1F3864",name="맑은 고딕")
    else: c.font=Font(size=10,name="맑은 고딕")
    c.alignment=left; rr+=1

# ---- Sheet3: 원본 다나와 ----
ws3=wb.create_sheet("원본_다나와데이터")
rc=["세그먼트","브랜드","상품명","모델번호","용량(L)","다나와최저가","국내최저소싱가","국내최저소싱처","판매처수","소싱처URL","비고"]
for j,h in enumerate(rc,1):
    c=ws3.cell(1,j,h); c.font=hdr_font; c.fill=PatternFill("solid",fgColor=NAVY); c.alignment=center; c.border=border
srcmap={m.get("modelNumber"):m for m in models}
for i,m in enumerate(DATA.get("raw",models),start=2):
    s=srcmap.get(m.get("modelNumber"),{})
    vals=[m.get("segment",""),m.get("brand",""),m.get("productName",""),m.get("modelNumber",""),
          m.get("capacityL",""),m.get("danawaLowestPrice",""),s.get("sourcingPrice",""),
          s.get("sourcingSeller",""),m.get("sellerCount",""),s.get("sourcingUrl","") or m.get("danawaSearchUrl",""),m.get("notes","")]
    for j,v in enumerate(vals,1):
        c=ws3.cell(i,j,v); c.font=cell_font; c.border=border
        c.alignment=left if j in (3,8,10) else center
        if j in (6,7): c.number_format='#,##0'
for j,w in enumerate([16,10,26,18,7,12,12,16,8,30,18],1): ws3.column_dimensions[get_column_letter(j)].width=w
ws3.freeze_panes="A2"

wb.save(OUT)
print("SAVED:",OUT," models:",len(models))

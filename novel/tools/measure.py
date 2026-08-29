import re, glob, os
import os
from pathlib import Path as _P
_ROOT = os.environ.get("NOVEL_ROOT") or str(_P(__file__).resolve().parents[2])
_OUT  = os.environ.get("NOVEL_OUT")  or "/tmp/claude-0/-home-user-kotkim8210/c058c336-4e2b-5e83-9e93-9b4f05f88f8f/scratchpad"
def measure(p):
    t=open(p,encoding='utf-8').read()
    body='\n'.join(l for l in t.split('\n') if not l.startswith('# '))
    chars=len(body)
    paras=[x.strip() for x in body.split('\n') if x.strip() and x.strip()!='⁂']
    dlg=[x for x in paras if x[0] in '"『─>']
    narr=[x for x in paras if x not in dlg]
    longest=max((len(re.sub(r'\s','',x)) for x in narr), default=0)
    over120=sum(1 for x in narr if len(re.sub(r'\s','',x))>120)
    aph=len(re.findall(r'(는 것이다|법이다|뿐이었다|는 뜻이었다|것은 아니었다)\.', '\n'.join(narr)))
    laugh=len(re.findall(r'웃|피식|농담', '\n'.join(paras)))
    warm=len(re.findall(r'보온병|김치|담요|보리차|계란|반찬|밥', '\n'.join(paras)))
    meta=len(re.findall(r'(?:[0-9]+|[일이삼사오육칠팔구십백]+)\s*화(?:\s*전|에서|입니다|였|야|다)', body))
    # §13-1 파편 종결(관형절·명사구만 남기고 끊기) / §13-2 동일 어미 3연속
    frag=sum(1 for x in narr if re.search(r'(의|던|하는|같은|무렵|때|채|만큼|한 번도|조차)\.$', x) and len(x)<60)
    ends=[(re.search(r'([가-힣]{2,3}다)\.$', x).group(1) if re.search(r'([가-힣]{2,3}다)\.$', x) else None) for x in narr]
    # §13-2 개정: 계사·존재사(있었다/없었다/이었다/였다) 3연속만 게이트, 내용 동사는 경고
    FILLER=('있었다','없었다','이었다','였다')
    rep=0; repw=0; run=1
    for a,b in zip(ends+[None], (ends+[None])[1:]):
        if a and a==b: run+=1
        else:
            if run>=3:
                if a and a.endswith(FILLER): rep+=1
                else: repw+=1
            run=1
    # §13-5 체언 나열 3연속 (참고용 — 예외가 많아 게이트로 쓰지 않는다, §13-6)
    VE=re.compile(r'(다|요|까|죠|지|네|군|나|오|소|겠|음|함|임|어|아|래|자)$')
    def nf(x):
        x=x.strip().rstrip('.!?').rstrip('…').strip()
        return bool(x) and len(x)<=30 and not VE.search(x) and bool(re.search(r'[가-힣A-Za-z0-9]$', x))
    noun=0
    for x in narr:
        run=0
        for seg in re.split(r'(?<=[.!?])\s+', x):
            if nf(seg): run+=1
            else:
                if run>=3: noun+=1
                run=0
        if run>=3: noun+=1
    # §13-7 단문 연속 — 25자 이하 완결문 3연속 (경고 전용, 게이트 아님)
    SC=re.compile(r'(다|요|까|죠|네|군|오|소)[.!?]$')
    def sc(x): return len(re.sub(r'\s','',x))<=25 and bool(SC.search(x.strip()))
    brief=0; run=0
    for x in narr:
        segs=[y for y in re.split(r'(?<=[.!?])\s+', x) if y.strip()]
        if len(segs)>=3 and all(sc(y) for y in segs[:3]): brief+=1
        if len(segs)==1 and sc(x): run+=1
        else:
            if run>=3: brief+=1
            run=0
    if run>=3: brief+=1
    return chars, meta, round(100*len(dlg)/max(len(paras),1)), longest, over120, aph, laugh, warm, frag, rep, noun, brief, repw
print(f"{'회':>4} {'자수':>6} {'메타':>4} {'대화%':>5} {'최장':>5} {'120+':>5} {'경구':>4} {'웃음':>4} {'훈훈':>4} {'파편':>4} {'반복':>4} {'반복*':>5} {'체언':>4} {'단문':>4}")
files=sorted(glob.glob(f'{_ROOT}/novel/manuscript/*.md'))
for p in files[-9:]:
    c,mt,r,lg,ov,ap,la,wa,fr,rp,nn,bf,rw = measure(p)
    flag='⚠'+str(mt) if mt else '0'
    print(f"{os.path.basename(p)[:3]:>4} {c:>6} {flag:>4} {r:>5} {lg:>5} {ov:>5} {ap:>4} {la:>4} {wa:>4} {fr:>4} {rp:>4} {rw:>5} {nn:>4} {bf:>4}")
tot=sum(measure(p)[0] for p in files)
print(f"\n총 {len(files)}화 / {tot:,}자")

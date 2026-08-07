"""린치식 조정이 실제로 효과가 있는가 — 3가지 가설 검증.

H1. 분산(종목 수)  : 린치는 수백 종목을 들었다. 15종목 집중의 비용이 문제였는가?
H2. 낮은 회전율    : 린치는 오래 들었다. 연 1회 리밸런스가 월 1회보다 나은가?
H3. '뜨거운 주식 회피': 린치의 1순위 금기. 모멘텀 상위를 배제하면 개선되는가?

재무 데이터가 없으므로 PEG 등 린치의 핵심 지표는 검증 불가. 여기서 검증하는 것은
'린치식 포트폴리오 운용 방식'이 앞선 실패를 고치는지다.
"""
import warnings, os, time
warnings.filterwarnings('ignore')
import pandas as pd, numpy as np
import engine
from engine import load, build_features, metrics, COMM_BPS, TAX_BPS, SLIP_BPS

D = os.path.dirname(os.path.abspath(__file__))
START, END = '2015-01-01', '2025-12-31'
TOPN_LARGE = 200

def elig_rank(close, f, date, topn=None, top_pct=0.60, min_price=1000):
    alive = close.loc[date].notna()
    cont = f['continuity'].loc[date] >= 270
    prc = close.loc[date] >= min_price
    base = (alive & cont & prc).fillna(False)
    adtv = f['adtv60'].loc[date].where(base)
    keep = adtv.nlargest(topn).index if topn else adtv[adtv >= adtv.quantile(1 - top_pct)].index
    out = pd.Series(False, index=close.columns); out.loc[keep] = True
    return out & base

def run(close, open_, f, score_fn, n_hold, topn, freq='ME'):
    """freq: 'ME' 월 리밸런스, 'YE' 연 1회 리밸런스"""
    dates = close.loc[START:END].index
    rb = [d for d in pd.Series(dates, index=dates).resample(freq).last().dropna().values
          if d in set(dates)]
    cash, hold = 1.0, {}
    eq, idx, turns = [], [], []

    for i, rd in enumerate(rb[:-1]):
        for s in list(hold):                                    # 소멸 종목 청산
            if pd.isna(close.loc[rd, s]):
                last = close[s].loc[:rd].dropna()
                cash += hold[s] * (last.iloc[-1] if len(last) else 0.0) * (1 - (COMM_BPS+TAX_BPS+SLIP_BPS)/1e4)
                del hold[s]
        val = cash + sum(sh * close.loc[rd, s] for s, sh in hold.items())
        if not np.isfinite(val) or val <= 0:
            eq.append(eq[-1] if eq else 1.0); idx.append(rd); continue

        e = elig_rank(close, f, rd, topn)
        sc = score_fn(f, rd, e).dropna()
        picks = sc.nlargest(n_hold).index.tolist()
        if not picks:
            eq.append(val); idx.append(rd); continue
        w = {s: 1.0/len(picks) for s in picks}

        ni = dates.get_loc(rd) + 1
        if ni >= len(dates): break
        ed = dates[ni]
        def px(s):
            p = open_.loc[ed, s]
            if pd.isna(p): p = close.loc[rd, s]
            return p if (pd.notna(p) and p > 0) else np.nan

        for s in list(hold):                                    # 매도
            if s not in w:
                p = px(s)
                if pd.isna(p):
                    last = close[s].loc[:rd].dropna(); p = last.iloc[-1] if len(last) else 0.0
                cash += hold[s] * p * (1 - (COMM_BPS+TAX_BPS+SLIP_BPS)/1e4); del hold[s]
        val = cash + sum(sh * px(s) for s, sh in hold.items() if pd.notna(px(s)))
        if not np.isfinite(val) or val <= 0:
            eq.append(eq[-1] if eq else 1.0); idx.append(rd); continue

        tt = 0.0
        for s, wt in w.items():
            p = px(s)
            if pd.isna(p): continue
            diff = val*wt - hold.get(s, 0)*p
            tt += abs(diff)
            if diff > 0:
                cash -= diff * (1 + (COMM_BPS+SLIP_BPS)/1e4); hold[s] = hold.get(s,0) + diff/p
            elif diff < 0:
                cash += -diff * (1 - (COMM_BPS+TAX_BPS+SLIP_BPS)/1e4); hold[s] = hold.get(s,0) + diff/p
        turns.append(tt/val)

        nd = rb[i+1]
        v = cash
        for s, sh in hold.items():
            p2 = close.loc[nd, s]
            if pd.isna(p2):
                last = close[s].loc[:nd].dropna(); p2 = last.iloc[-1] if len(last) else 0.0
            v += sh*p2
        if not np.isfinite(v): v = eq[-1] if eq else 1.0
        eq.append(max(v, 1e-12)); idx.append(nd)

    s = pd.Series(eq, index=pd.DatetimeIndex(idx))
    s = s[~s.index.duplicated(keep='last')].sort_index()
    per_year = 12 if freq == 'ME' else 1
    return s, (np.mean(turns)*per_year if turns else 0)

# ── 전략
def s_lowvol(f, d, e):
    return (-f['vol60'].loc[d]).where(e)

def s_lowvol_nothot(f, d, e):
    """린치 1순위 금기: '뜨거운 업종의 뜨거운 주식'을 산다.
    → 12개월 모멘텀 상위 30%를 배제한 뒤 저변동성 선택"""
    mom = f['ret_12_1'].loc[d].where(e)
    cut = mom.quantile(0.70)
    cool = e & (mom <= cut)
    return (-f['vol60'].loc[d]).where(cool)

def cagr(s):
    y = (s.index[-1]-s.index[0]).days/365.25
    return (s.iloc[-1]/s.iloc[0])**(1/y)-1

def main():
    t0 = time.time()
    close, open_, tri, turnover, uni, bench, notna = load()
    f = build_features(tri, close, turnover, notna)
    kospi = bench['KOSPI'].dropna().resample('ME').last().loc[START:END]
    k_cagr = cagr(kospi)
    print(f'[준비] {time.time()-t0:.0f}s   KOSPI 기준선 CAGR {k_cagr*100:.2f}%\n', flush=True)

    rows = []
    print('='*104)
    print('H1+H2  분산(종목 수) × 회전율(리밸런스 주기)  — 저변동성 선택 기준 고정')
    print('='*104)
    print(f'{"유니버스":<12}{"종목수":>6}{"주기":>6}{"CAGR":>9}{"MDD":>9}{"Sharpe":>8}{"vs KOSPI":>10}{"회전율":>8}')
    for topn, ulbl in [(TOPN_LARGE, '대형주200'), (None, '전체60%')]:
        for freq, flbl in [('ME', '월'), ('YE', '연1회')]:
            for n in [15, 30, 50, 100]:
                eq, tv = run(close, open_, f, s_lowvol, n, topn, freq)
                if len(eq) < 8: continue
                m = metrics(eq, kospi); c = cagr(eq)
                rows.append(dict(universe=ulbl, n=n, freq=flbl, cagr=c, mdd=m['MDD'],
                                 sharpe=m['Sharpe'], vs=c-k_cagr, turn=tv))
                print(f'{ulbl:<12}{n:>6}{flbl:>6}{c*100:>8.2f}%{m["MDD"]*100:>8.1f}%'
                      f'{m["Sharpe"]:>8.2f}{(c-k_cagr)*100:>+9.2f}p{tv:>8.2f}', flush=True)

    print(f'\n{"="*104}')
    print("H3  '뜨거운 주식 회피' 필터 (린치 1순위 금기) — 모멘텀 상위 30% 배제 후 저변동성")
    print('='*104)
    print(f'{"유니버스":<12}{"종목수":>6}{"주기":>6}{"기본":>10}{"핫배제":>10}{"차이":>10}')
    for topn, ulbl in [(TOPN_LARGE, '대형주200'), (None, '전체60%')]:
        for freq, flbl in [('ME', '월'), ('YE', '연1회')]:
            for n in [30, 50]:
                a, _ = run(close, open_, f, s_lowvol, n, topn, freq)
                b, _ = run(close, open_, f, s_lowvol_nothot, n, topn, freq)
                if len(a) < 8 or len(b) < 8: continue
                ca, cb = cagr(a), cagr(b)
                print(f'{ulbl:<12}{n:>6}{flbl:>6}{ca*100:>9.2f}%{cb*100:>9.2f}%{(cb-ca)*100:>+9.2f}p', flush=True)

    pd.DataFrame(rows).to_csv(f'{D}/lynch_grid.csv', index=False)
    print(f'\n[완료] {time.time()-t0:.0f}s')

if __name__ == '__main__':
    main()

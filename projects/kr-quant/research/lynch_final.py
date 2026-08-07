"""연 1회 리밸런스 전략을 '월간 시가평가'로 다시 측정 + 랜덤 대조군.

앞선 실행의 MDD는 연간 스냅샷 기준이라 기중 낙폭을 놓쳤다(측정 오류).
여기서는 리밸런스는 연 1회 하되 평가는 매월 해서 MDD·Sharpe를 비교 가능하게 만든다.
"""
import warnings, os, time
warnings.filterwarnings('ignore')
import pandas as pd, numpy as np
from engine import load, build_features, metrics, COMM_BPS, TAX_BPS, SLIP_BPS

D = os.path.dirname(os.path.abspath(__file__))
START, END = '2015-01-01', '2025-12-31'

def elig_rank(close, f, date, topn=None, top_pct=0.60, min_price=1000):
    alive = close.loc[date].notna()
    cont = f['continuity'].loc[date] >= 270
    prc = close.loc[date] >= min_price
    base = (alive & cont & prc).fillna(False)
    adtv = f['adtv60'].loc[date].where(base)
    keep = adtv.nlargest(topn).index if topn else adtv[adtv >= adtv.quantile(1 - top_pct)].index
    out = pd.Series(False, index=close.columns); out.loc[keep] = True
    return out & base

def run(close, open_, f, score_fn, n_hold, topn, rebal_freq='YE'):
    """리밸런스는 rebal_freq 주기, 평가는 매월 (MDD 비교 가능하게)"""
    dates = close.loc[START:END].index
    months = [d for d in pd.Series(dates, index=dates).resample('ME').last().dropna().values
              if d in set(dates)]
    rebals = set(d for d in pd.Series(dates, index=dates).resample(rebal_freq).last().dropna().values
                 if d in set(dates))
    cash, hold = 1.0, {}
    eq, idx, turns = [], [], []

    def mtm(d):
        v = cash
        for s, sh in hold.items():
            p = close.loc[d, s]
            if pd.isna(p):
                last = close[s].loc[:d].dropna(); p = last.iloc[-1] if len(last) else 0.0
            v += sh * p
        return v

    for m in months:
        # 소멸 종목 청산
        for s in list(hold):
            if pd.isna(close.loc[m, s]):
                last = close[s].loc[:m].dropna()
                cash += hold[s] * (last.iloc[-1] if len(last) else 0.0) * (1-(COMM_BPS+TAX_BPS+SLIP_BPS)/1e4)
                del hold[s]

        if m in rebals:
            val = mtm(m)
            if np.isfinite(val) and val > 0:
                e = elig_rank(close, f, m, topn)
                sc = score_fn(f, m, e).dropna()
                picks = sc.nlargest(n_hold).index.tolist()
                if picks:
                    w = {s: 1.0/len(picks) for s in picks}
                    ni = dates.get_loc(m) + 1
                    if ni < len(dates):
                        ed = dates[ni]
                        def px(s):
                            p = open_.loc[ed, s]
                            if pd.isna(p): p = close.loc[m, s]
                            return p if (pd.notna(p) and p > 0) else np.nan
                        for s in list(hold):
                            if s not in w:
                                p = px(s)
                                if pd.isna(p):
                                    last = close[s].loc[:m].dropna(); p = last.iloc[-1] if len(last) else 0.0
                                cash += hold[s]*p*(1-(COMM_BPS+TAX_BPS+SLIP_BPS)/1e4); del hold[s]
                        val = cash + sum(sh*px(s) for s, sh in hold.items() if pd.notna(px(s)))
                        if np.isfinite(val) and val > 0:
                            tt = 0.0
                            for s, wt in w.items():
                                p = px(s)
                                if pd.isna(p): continue
                                diff = val*wt - hold.get(s, 0)*p
                                tt += abs(diff)
                                if diff > 0:
                                    cash -= diff*(1+(COMM_BPS+SLIP_BPS)/1e4); hold[s] = hold.get(s,0)+diff/p
                                elif diff < 0:
                                    cash += -diff*(1-(COMM_BPS+TAX_BPS+SLIP_BPS)/1e4); hold[s] = hold.get(s,0)+diff/p
                            turns.append(tt/val)
        v = mtm(m)
        if not np.isfinite(v): v = eq[-1] if eq else 1.0
        eq.append(max(v, 1e-12)); idx.append(m)

    s = pd.Series(eq, index=pd.DatetimeIndex(idx))
    s = s[~s.index.duplicated(keep='last')].sort_index()
    yrs = (s.index[-1]-s.index[0]).days/365.25
    return s, (sum(turns)/yrs if turns else 0)

def s_lowvol(f, d, e): return (-f['vol60'].loc[d]).where(e)
def cagr(s):
    y = (s.index[-1]-s.index[0]).days/365.25
    return (s.iloc[-1]/s.iloc[0])**(1/y)-1

def main():
    t0 = time.time()
    close, open_, tri, turnover, uni, bench, notna = load()
    f = build_features(tri, close, turnover, notna)
    kospi = bench['KOSPI'].dropna().resample('ME').last().loc[START:END]
    kc = cagr(kospi); km = metrics(kospi)
    print(f'[준비] {time.time()-t0:.0f}s\n', flush=True)

    print('='*96)
    print('월간 시가평가 기준 재측정 (리밸런스 주기만 다름) — MDD·Sharpe 비교 가능')
    print('='*96)
    print(f'{"전략":<28}{"CAGR":>9}{"MDD":>9}{"Sharpe":>8}{"vs KOSPI":>10}{"회전율":>8}')
    print(f'{"KOSPI 지수":<28}{kc*100:>8.2f}%{km["MDD"]*100:>8.1f}%{km["Sharpe"]:>8.2f}{"":>10}{"-":>8}')
    best = None
    for topn, ul in [(200, '대형주200'), (None, '전체60%')]:
        for freq, fl in [('ME', '월'), ('YE', '연1회')]:
            for n in [15, 30, 50]:
                eq, tv = run(close, open_, f, s_lowvol, n, topn, freq)
                m = metrics(eq, kospi); c = cagr(eq)
                lbl = f'저변동성 {ul} {n}종목 {fl}'
                print(f'{lbl:<28}{c*100:>8.2f}%{m["MDD"]*100:>8.1f}%{m["Sharpe"]:>8.2f}'
                      f'{(c-kc)*100:>+9.2f}p{tv:>8.2f}', flush=True)
                if best is None or c > best[1]: best = (lbl, c, n, topn, freq)

    print(f'\n최고 성과: {best[0]}  CAGR {best[1]*100:.2f}%')
    print('\n' + '='*96)
    print(f'랜덤 대조군 150회 — 동일 조건(대형주200 / {best[2]}종목 / 연1회)에서 무작위 선택')
    print('='*96, flush=True)
    rng = np.random.default_rng(11); rc = []
    for i in range(150):
        sd = int(rng.integers(0, 10**9))
        def s_rand(ff, d, e, _s=sd):
            idx = e[e].index
            if len(idx) == 0: return pd.Series(dtype=float)
            return pd.Series(np.random.default_rng(_s+int(pd.Timestamp(d).toordinal())).random(len(idx)), index=idx)
        eq, _ = run(close, open_, f, s_rand, 50, 200, 'YE')
        rc.append(cagr(eq))
        if (i+1) % 50 == 0: print(f'  {i+1}/150 평균 {np.mean(rc)*100:.2f}% ({time.time()-t0:.0f}s)', flush=True)
    rc = np.array(rc)
    eq_best, _ = run(close, open_, f, s_lowvol, 50, 200, 'YE')
    cb = cagr(eq_best); pct = (rc < cb).mean()*100
    print(f'\n  랜덤(50종목·연1회) CAGR: 5%ile {np.percentile(rc,5)*100:.2f}% | 중앙값 {np.median(rc)*100:.2f}% '
          f'| 95%ile {np.percentile(rc,95)*100:.2f}% | 평균 {rc.mean()*100:.2f}%')
    print(f'  저변동성 50종목 연1회: {cb*100:.2f}%  →  랜덤 대비 {pct:.1f}%ile  '
          f'{"✅ 유의" if pct>=95 else ("△ 미약" if pct>=80 else "❌ 무의미")}')
    print(f'  KOSPI 지수:            {kc*100:.2f}%  →  랜덤 대비 {(rc<kc).mean()*100:.1f}%ile')
    np.save(f'{D}/lynch_random.npy', rc)
    print(f'\n[완료] {time.time()-t0:.0f}s')

if __name__ == '__main__':
    main()

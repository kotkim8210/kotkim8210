"""최종 검증: 자동투자 전략이 시장 평균을 이기는가.

수정 사항
 - EW 기준선: 비대칭 절단 제거 → 상하위 1% 윈저라이즈 (오른쪽 꼬리를 자르던 편향 제거)
 - 유동성 필터: 절대금액 대신 '당일 거래대금 상위 X%' 랭크 (수정주가 스케일 왜곡 완화)
 - 대형주 유니버스(거래대금 상위 200) 별도 검증 — 소형주 편중이 원인인지 분리
 - 랜덤 대조군으로 '우연 대비 실력' 판정
"""
import warnings, os, time
warnings.filterwarnings('ignore')
import pandas as pd, numpy as np
from engine import (load, build_features, backtest, metrics, rsi_weekly,
                    COMM_BPS, TAX_BPS, SLIP_BPS)
import engine

D = os.path.dirname(os.path.abspath(__file__))
START, END = '2015-01-01', '2025-12-31'

# ── 랭크 기반 유동성 필터로 교체
LIQ_TOP_PCT = 0.60      # 거래대금 상위 60%
TOPN_LARGE = 200

def elig_rank(close, turnover, f, uni, date, top_pct=LIQ_TOP_PCT, topn=None, min_price=1000):
    alive = close.loc[date].notna()
    cont = f['continuity'].loc[date] >= 270
    prc = close.loc[date] >= min_price
    base = (alive & cont & prc).fillna(False)
    adtv = f['adtv60'].loc[date].where(base)
    if topn is not None:
        keep = adtv.nlargest(topn).index
    else:
        thr = adtv.quantile(1 - top_pct)
        keep = adtv[adtv >= thr].index
    out = pd.Series(False, index=close.columns)
    out.loc[keep] = True
    return out & base

def bt(close, open_, turnover, f, uni, score_fn, n_hold, topn=None):
    engine.eligibility = lambda c, t, ff, u, d, ma, min_price=1000: elig_rank(c, t, ff, u, d, topn=topn)
    return backtest(close, open_, turnover, f, uni, score_fn, n_hold, START, END)

def ew_bench(close, turnover, f, uni, topn=None):
    dates = close.loc[START:END].index
    rebal = [d for d in pd.Series(dates, index=dates).resample('ME').last().dropna().values
             if d in set(dates)]
    rows = []
    for i in range(len(rebal) - 1):
        d0, d1 = rebal[i], rebal[i + 1]
        e = elig_rank(close, turnover, f, uni, d0, topn=topn)
        syms = e[e].index
        if len(syms) == 0: rows.append((d1, 0.0)); continue
        r = (close.loc[d1, syms] / close.loc[d0, syms] - 1)
        # 상장폐지로 가격 소멸 → 마지막 가용가로 평가 (생존편향 방지)
        miss = r[r.isna()].index
        for s in miss:
            seg = close[s].loc[d0:d1].dropna()
            r[s] = seg.iloc[-1] / close.loc[d0, s] - 1 if len(seg) else -0.5
        r = r.dropna()
        if len(r) == 0: rows.append((d1, 0.0)); continue
        lo, hi = r.quantile(0.01), r.quantile(0.99)     # 대칭 윈저라이즈
        rows.append((d1, r.clip(lo, hi).mean()))
    s = pd.Series(dict(rows)).sort_index()
    return (1 + s).cumprod()

def cagr(eq):
    y = (eq.index[-1] - eq.index[0]).days / 365.25
    return (eq.iloc[-1] / eq.iloc[0]) ** (1 / y) - 1

def main():
    t0 = time.time()
    close, open_, tri, turnover, uni, bench, notna = load()
    f = build_features(tri, close, turnover, notna)
    print(f'[준비] {time.time()-t0:.0f}s', flush=True)

    for lbl, topn in [('전체(거래대금 상위60%)', None), ('대형주(상위200)', TOPN_LARGE)]:
        for d in ['2010-06-30', '2015-06-30', '2020-06-30', '2025-06-30']:
            dt = close.index[close.index <= pd.Timestamp(d)][-1]
            e = elig_rank(close, turnover, f, uni, dt, topn=topn)
            print(f'   [{lbl}] {dt.date()} 유니버스 {int(e.sum()):,}')
        break

    kospi = bench['KOSPI'].dropna().resample('ME').last().loc[START:END]

    for label, topn in [('■ 전체 유니버스 (거래대금 상위 60%)', None),
                        ('■ 대형주 유니버스 (거래대금 상위 200)', TOPN_LARGE)]:
        print(f'\n{"="*100}\n{label}\n{"="*100}', flush=True)
        ewb = ew_bench(close, turnover, f, uni, topn=topn)
        res, eqs = {}, {'EW_평균종목': ewb, 'KOSPI지수': kospi}
        for name, (fn, n) in engine.STRATS.items():
            if name == 'EW_MARKET': continue
            eq, turn = bt(close, open_, turnover, f, uni, fn, n, topn)
            if len(eq) < 24: continue
            eqs[name] = eq
            m = metrics(eq, ewb); m['연회전율'] = turn
            res[name] = m
        for nm, s in [('EW_평균종목', ewb), ('KOSPI지수', kospi)]:
            res[nm] = metrics(s, ewb); res[nm]['연회전율'] = np.nan

        df = pd.DataFrame(res).T
        show = df[['CAGR','MDD','Sharpe','초과CAGR','IR','월승률','최종배수','연회전율']].copy()
        for c in ['CAGR','MDD','초과CAGR','월승률']:
            show[c] = show[c].apply(lambda v: f'{v*100:7.2f}%' if pd.notna(v) else '      -')
        for c in ['Sharpe','IR','최종배수','연회전율']:
            show[c] = show[c].apply(lambda v: f'{v:6.2f}' if pd.notna(v) else '     -')
        print(show.sort_values('CAGR', ascending=False).to_string())
        df.to_csv(f'{D}/final_{"large" if topn else "all"}.csv')
        pd.DataFrame(eqs).to_parquet(f'{D}/final_eq_{"large" if topn else "all"}.parquet')

    # ── 랜덤 대조군 (대형주 유니버스)
    print(f'\n{"="*100}\n랜덤 포트폴리오 대조군 200회 (대형주 유니버스, 15종목) — 우연 대비 실력 판정\n{"="*100}', flush=True)
    rng = np.random.default_rng(7)
    rc = []
    for i in range(200):
        sd = int(rng.integers(0, 10**9))
        def s_rand(ff, date, elig, _s=sd):
            e = elig[elig].index
            if len(e) == 0: return pd.Series(dtype=float)
            return pd.Series(np.random.default_rng(_s + int(pd.Timestamp(date).toordinal())).random(len(e)), index=e)
        eq, _ = bt(close, open_, turnover, f, uni, s_rand, 15, TOPN_LARGE)
        if len(eq) > 24: rc.append(cagr(eq))
        if (i+1) % 50 == 0: print(f'  {i+1}/200 평균 {np.mean(rc)*100:.2f}% ({time.time()-t0:.0f}s)', flush=True)
    rc = np.array(rc); np.save(f'{D}/random_cagrs.npy', rc)
    print(f'\n  랜덤 CAGR 분포: 5%ile {np.percentile(rc,5)*100:.2f}% | 중앙값 {np.median(rc)*100:.2f}% '
          f'| 95%ile {np.percentile(rc,95)*100:.2f}% | 평균 {rc.mean()*100:.2f}%')
    print(f'\n  전략별 랜덤 대비 백분위 (95%ile 초과해야 알파 주장 가능):')
    for name, (fn, n) in engine.STRATS.items():
        if name == 'EW_MARKET': continue
        eq, _ = bt(close, open_, turnover, f, uni, fn, n, TOPN_LARGE)
        if len(eq) < 24: continue
        c = cagr(eq); p = (rc < c).mean() * 100
        mark = '✅ 유의' if p >= 95 else ('△ 미약' if p >= 80 else '❌ 무의미')
        print(f'    {name:<14} CAGR {c*100:6.2f}%  →  랜덤 대비 상위 {100-p:5.1f}%  {mark}')

    print(f'\n[완료] {time.time()-t0:.0f}s')

if __name__ == '__main__':
    main()

"""버크셔 해서웨이 vs S&P500 — '버핏을 따라하면 시장을 이기는가'의 실증 검증.

주의: ^GSPC는 배당 제외 가격지수다. 버크셔는 무배당이므로 그대로 비교하면
      S&P에 불리하다. 따라서 S&P 총수익 근사치(+연 2.0%p 배당)를 함께 제시한다.
"""
import warnings, os
warnings.filterwarnings('ignore')
import pandas as pd, numpy as np
import FinanceDataReader as fdr

D = os.path.dirname(os.path.abspath(__file__))
SPX_DIV = 0.020   # S&P500 장기 평균 배당수익률 근사 [확인필요]

def cagr(s):
    y = (s.index[-1] - s.index[0]).days / 365.25
    return (s.iloc[-1] / s.iloc[0]) ** (1 / y) - 1

def mdd(s): return (s / s.cummax() - 1).min()

def stats(s, rf=0.03):
    r = s.pct_change().dropna()
    c = cagr(s); v = r.std() * np.sqrt(252)
    return dict(CAGR=c, MDD=mdd(s), Vol=v, Sharpe=(c - rf) / v)

def main():
    brk = fdr.DataReader('BRK-A', '1980-01-01', '2025-12-31')['Close']
    spx = fdr.DataReader('^GSPC', '1980-01-01', '2025-12-31')['Close']
    df = pd.concat([brk.rename('BRK'), spx.rename('SPX')], axis=1).dropna()

    print('=' * 96)
    print('버크셔 해서웨이 vs S&P500  (1980-2025, 46년)')
    print('=' * 96)
    b, s = stats(df.BRK), stats(df.SPX)
    spx_tr_cagr = s['CAGR'] + SPX_DIV
    print(f'{"":22} {"CAGR":>9} {"MDD":>9} {"변동성":>9} {"Sharpe":>8} {"최종배수":>10}')
    print(f'{"버크셔(BRK-A)":22} {b["CAGR"]*100:8.2f}% {b["MDD"]*100:8.1f}% {b["Vol"]*100:8.1f}% '
          f'{b["Sharpe"]:8.2f} {df.BRK.iloc[-1]/df.BRK.iloc[0]:9.0f}배')
    print(f'{"S&P500(가격지수)":22} {s["CAGR"]*100:8.2f}% {s["MDD"]*100:8.1f}% {s["Vol"]*100:8.1f}% '
          f'{s["Sharpe"]:8.2f} {df.SPX.iloc[-1]/df.SPX.iloc[0]:9.0f}배')
    print(f'{"S&P500(배당포함 근사)":22} {spx_tr_cagr*100:8.2f}% {"":>9} {"":>9} {"":>8}')
    print(f'\n  → 전체 기간 초과수익(배당 조정 후): {(b["CAGR"]-spx_tr_cagr)*100:+.2f}%p/년')

    # ── 10년 단위
    print('\n' + '=' * 96)
    print('10년 단위 — "버핏의 우위는 지금도 유효한가"')
    print('=' * 96)
    print(f'{"기간":14} {"버크셔":>10} {"S&P(가격)":>11} {"S&P(배당포함)":>13} {"초과":>10}')
    rows = []
    for y0 in range(1980, 2025, 5):
        y1 = min(y0 + 5, 2026)
        seg = df.loc[f'{y0}-01-01':f'{y1-1}-12-31']
        if len(seg) < 200: continue
        cb, cs = cagr(seg.BRK), cagr(seg.SPX)
        ex = cb - (cs + SPX_DIV)
        rows.append((f'{y0}-{y1-1}', cb, cs, cs + SPX_DIV, ex))
        print(f'{y0}-{y1-1:<9} {cb*100:9.2f}% {cs*100:10.2f}% {(cs+SPX_DIV)*100:12.2f}% {ex*100:+9.2f}%p')

    # ── 롤링 10년 초과수익
    print('\n' + '=' * 96)
    print('롤링 10년 초과수익 (배당 조정 후) — 우위의 지속성')
    print('=' * 96)
    m = df.resample('ME').last()
    roll = []
    for i in range(120, len(m)):
        seg = m.iloc[i-120:i+1]
        roll.append((seg.index[-1], cagr(seg.BRK) - cagr(seg.SPX) - SPX_DIV))
    rs = pd.Series(dict(roll))
    print(f'  롤링 10년 구간 수: {len(rs)}')
    print(f'  초과수익 > 0 인 비율: {(rs>0).mean()*100:.1f}%')
    print(f'  평균 {rs.mean()*100:+.2f}%p | 중앙값 {rs.median()*100:+.2f}%p '
          f'| 최대 {rs.max()*100:+.2f}%p | 최소 {rs.min()*100:+.2f}%p')
    print(f'\n  최근 10년(2016-2025) 기준 초과수익: {rs.iloc[-1]*100:+.2f}%p')
    for yr in [2000, 2005, 2010, 2015, 2020, 2025]:
        v = rs[rs.index.year == yr]
        if len(v): print(f'    {yr}년 시점 직전10년 초과: {v.iloc[-1]*100:+7.2f}%p')

    # ── 베타
    print('\n' + '=' * 96)
    print('시장 베타 — 버핏 팩터 분해의 핵심(저베타 노출)')
    print('=' * 96)
    for lbl, seg in [('1980-1999', df.loc[:'1999-12-31']), ('2000-2025', df.loc['2000-01-01':])]:
        r = seg.pct_change().dropna()
        beta = r.BRK.cov(r.SPX) / r.SPX.var()
        corr = r.BRK.corr(r.SPX)
        print(f'  {lbl}:  베타 {beta:.2f}   상관 {corr:.2f}   '
              f'버크셔 변동성 {r.BRK.std()*np.sqrt(252)*100:.1f}% vs S&P {r.SPX.std()*np.sqrt(252)*100:.1f}%')

    rs.to_csv(f'{D}/brk_rolling10y.csv')
    pd.DataFrame(rows, columns=['기간','버크셔','SPX가격','SPX총수익','초과']).to_csv(f'{D}/brk_periods.csv', index=False)

if __name__ == '__main__':
    main()

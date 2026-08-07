"""생존편향 없는 한국주식 백테스트 엔진.

원칙
 - 유니버스는 매 리밸런스 시점에 '실제로 거래 가능했던' 종목만 (상장폐지 종목 포함)
 - 신호는 t시점까지의 데이터만 사용, 체결은 t+1 시가
 - 상장폐지 시 마지막 가용 가격으로 청산
 - 비용: 수수료 + 세금 + 슬리피지 전부 반영
"""
import warnings, os
warnings.filterwarnings('ignore')
import pandas as pd, numpy as np

D = os.path.dirname(os.path.abspath(__file__))

COMM_BPS = 1.5      # 매수/매도 수수료 0.015%
TAX_BPS = 20.0      # 매도 시 세금 0.20% (보수적)
SLIP_BPS = 10.0     # 편도 슬리피지 0.10%

# ────────────────────────────────────────────────── 데이터
MIN_VALID_PRICE = 100      # 100원 미만은 데이터 오류로 간주
MAX_GAP_DAYS = 10          # 직전 관측이 10거래일 넘게 떨어지면 불연속(거래정지 등)

def clean(close, open_):
    """DQ 검사: 이상가격 · 거래정지 공백 · 가격제한폭 초과를 제거한다.

    이 처리를 빼면 거래정지 후 재개 시점의 가짜 폭등(예: 10년 공백을 하루 수익률로 계산)을
    모멘텀 전략이 그대로 매수해 백테스트가 완전히 망가진다.
    """
    bad = (close < MIN_VALID_PRICE) | close.isna()
    close = close.mask(bad)
    open_ = open_.mask(bad)

    idx = close.index
    notna = close.notna()
    posmat = notna.mul(np.arange(len(idx)), axis=0).where(notna)
    prev = posmat.ffill().shift(1)
    gap = posmat - prev                                   # 직전 유효관측까지의 거래일 간격

    r = close.pct_change()
    # 가격제한폭: 2015-06-15 이전 ±15%, 이후 ±30% (여유 두고 오류만 제거)
    lim = pd.Series(np.where(idx < pd.Timestamp('2015-06-15'), 0.18, 0.33), index=idx)
    ok = (gap <= MAX_GAP_DAYS) & (r.abs().le(lim, axis=0))
    r_clean = r.where(ok)

    # 총수익지수 재구성 — 기술적 지표는 전부 이 위에서 계산한다
    tri = (1 + r_clean.fillna(0)).cumprod().where(notna)
    n_masked = int((r.notna() & ~ok).sum().sum())
    return close, open_, tri, r_clean, notna, n_masked

def load():
    px = pd.read_parquet(f'{D}/prices.parquet')
    uni = pd.read_parquet(f'{D}/universe.parquet')
    bench = pd.read_parquet(f'{D}/bench.parquet')
    close = px.pivot(index='Date', columns='Symbol', values='Close').sort_index()
    open_ = px.pivot(index='Date', columns='Symbol', values='Open').sort_index()
    vol = px.pivot(index='Date', columns='Symbol', values='Volume').sort_index()
    close, open_, tri, r_clean, notna, n_masked = clean(close, open_)
    turnover = close * vol
    print(f'[DQ] 이상 수익률 {n_masked:,}건 마스킹 (거래정지 공백·가격제한폭 초과·이상가격)')
    return close, open_, tri, turnover, uni, bench, notna

# ────────────────────────────────────────────────── 지표
def rsi_weekly(close_w, n=14):
    d = close_w.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = (-d.clip(upper=0)).rolling(n).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))

def build_features(tri, close, turnover, notna):
    """지표는 전부 정제된 총수익지수(tri) 위에서 계산한다."""
    f = {}
    f['ret_12_1'] = tri.shift(21) / tri.shift(252) - 1             # 12개월 모멘텀(최근 1개월 제외)
    f['ret_6m'] = tri / tri.shift(126) - 1
    f['ma252'] = tri.rolling(252).mean()
    f['ma300'] = tri.rolling(300).mean()
    f['ma252_slope'] = f['ma252'] / f['ma252'].shift(21) - 1        # 월봉 MA12 기울기
    f['above_ma252'] = tri > f['ma252']
    f['above_ma300'] = tri > f['ma300']
    f['high520'] = tri.rolling(520).max()                          # 104주 박스 상단
    f['breakout'] = tri >= f['high520'] * 0.995
    f['vol60'] = tri.pct_change().rolling(60).std() * np.sqrt(252)
    f['adtv60'] = turnover.rolling(60).mean()
    f['vol_mult'] = turnover.rolling(20).mean() / turnover.rolling(120).mean()
    f['disparity'] = tri / f['ma252'] * 100
    # 최근 300거래일 중 실제 거래된 일수 — 거래정지·불연속 종목 배제용
    f['continuity'] = notna.rolling(300).sum()
    cw = tri.resample('W-FRI').last()
    f['rsi_w'] = rsi_weekly(cw).reindex(tri.index, method='ffill')
    return f

# ────────────────────────────────────────────────── 유니버스
def eligibility(close, turnover, f, uni, date, min_adtv, min_price=1000):
    alive = close.loc[date].notna()
    cont = f['continuity'].loc[date] >= 270      # 최근 300거래일 중 270일 이상 거래 (연속성)
    liq = f['adtv60'].loc[date] >= min_adtv
    prc = close.loc[date] >= min_price
    return (alive & cont & liq & prc).fillna(False)

# ────────────────────────────────────────────────── 전략 (t시점 점수, 높을수록 선호)
def s_momentum(f, date, elig):
    return f['ret_12_1'].loc[date].where(elig)

def s_lowvol(f, date, elig):
    return (-f['vol60'].loc[date]).where(elig)

def s_trend_mom(f, date, elig):
    ok = elig & f['above_ma252'].loc[date] & (f['ma252_slope'].loc[date] > 0)
    return f['ret_12_1'].loc[date].where(ok)

def s_krq_t(f, date, elig):
    """설계 문서의 T축 규칙: 월봉추세 + 주봉추세 + 박스돌파 + 거래량확인 + RSI 과열배제 + 이격제한"""
    ok = (elig
          & f['above_ma252'].loc[date] & (f['ma252_slope'].loc[date] > 0)   # T1 월봉 추세
          & f['above_ma300'].loc[date]                                      # T2 주봉 추세
          & (f['vol_mult'].loc[date] >= 1.2)                                # T4 거래량 확인
          & (f['rsi_w'].loc[date].between(45, 78))                          # T5 과열 배제
          & (f['disparity'].loc[date] <= 140))                              # T6 이격 제한
    score = f['ret_12_1'].loc[date] + f['breakout'].loc[date].astype(float) * 0.2
    return score.where(ok)

def s_krq_t_strict(f, date, elig):
    """T축 + 박스권 돌파 필수"""
    ok = (elig
          & f['above_ma252'].loc[date] & (f['ma252_slope'].loc[date] > 0)
          & f['above_ma300'].loc[date]
          & f['breakout'].loc[date]
          & (f['vol_mult'].loc[date] >= 1.2)
          & (f['rsi_w'].loc[date].between(45, 78))
          & (f['disparity'].loc[date] <= 140))
    return f['ret_12_1'].loc[date].where(ok)

def s_reversal(f, date, elig):
    return (-f['ret_6m'].loc[date]).where(elig)

def s_equal(f, date, elig):
    return pd.Series(1.0, index=elig.index).where(elig)

STRATS = {
    'EW_MARKET':   (s_equal, None),      # 시장 평균(동일가중) — 진짜 비교 기준
    'MOM_12_1':    (s_momentum, 15),
    'LOWVOL':      (s_lowvol, 15),
    'TREND_MOM':   (s_trend_mom, 15),
    'KRQ_T':       (s_krq_t, 15),
    'KRQ_T_STRICT':(s_krq_t_strict, 15),
    'REVERSAL':    (s_reversal, 15),
}

# ────────────────────────────────────────────────── 백테스트
def backtest(close, open_, turnover, f, uni, score_fn, n_hold, start, end,
             min_adtv=300_000_000, verbose=False):
    dates = close.loc[start:end].index
    rebal = pd.Series(dates, index=dates).resample('ME').last().dropna().values
    rebal = [d for d in rebal if d in set(dates)]

    cash, holdings = 1.0, {}          # symbol -> shares
    equity, hist_dates, turnovers = [], [], []
    prev_w = {}

    for i, rd in enumerate(rebal[:-1]):
        # ── 가격이 소멸한 보유종목(상장폐지·거래정지) 청산: 마지막 가용가 사용
        for s in list(holdings):
            p = close.loc[rd, s]
            if pd.isna(p):
                last = close[s].loc[:rd].dropna()
                px_out = last.iloc[-1] if len(last) else 0.0
                cash += holdings[s] * px_out * (1 - (COMM_BPS + TAX_BPS + SLIP_BPS) / 1e4)
                del holdings[s]
        val = cash + sum(sh * close.loc[rd, s] for s, sh in holdings.items())
        if not np.isfinite(val) or val <= 0:      # 방어: NaN·음수 전파 차단
            equity.append(max(val, 0) if np.isfinite(val) else (equity[-1] if equity else 1.0))
            hist_dates.append(rd); turnovers.append(0); continue

        # ── 신호 (rd 시점 데이터만)
        elig = eligibility(close, turnover, f, uni, rd, min_adtv)
        sc = score_fn(f, rd, elig).dropna()
        if n_hold is None:
            picks = sc.index.tolist()
        else:
            picks = sc.nlargest(n_hold).index.tolist()
        if not picks:
            equity.append(val); hist_dates.append(rd); turnovers.append(0); continue

        w = {s: 1.0 / len(picks) for s in picks}

        # ── 체결: 다음 거래일 시가
        nxt_idx = dates.get_loc(rd) + 1
        if nxt_idx >= len(dates): break
        ed = dates[nxt_idx]

        def px_at(s):
            p = open_.loc[ed, s]
            if pd.isna(p): p = close.loc[rd, s]
            return p if (pd.notna(p) and p > 0) else np.nan

        # 매도
        for s in list(holdings):
            if s not in w:
                p = px_at(s)
                if pd.isna(p):
                    last = close[s].loc[:rd].dropna()
                    p = last.iloc[-1] if len(last) else 0.0
                cash += holdings[s] * p * (1 - (COMM_BPS + TAX_BPS + SLIP_BPS) / 1e4)
                del holdings[s]
        val = cash + sum(sh * px_at(s) for s, sh in holdings.items()
                         if pd.notna(px_at(s)))
        if not np.isfinite(val) or val <= 0:
            equity.append(equity[-1] if equity else 1.0); hist_dates.append(rd)
            turnovers.append(0); continue
        # 리밸런스
        tot_turn = 0.0
        for s, wt in w.items():
            p = px_at(s)
            if pd.isna(p): continue
            target_val = val * wt
            cur_val = holdings.get(s, 0) * p
            diff = target_val - cur_val
            tot_turn += abs(diff)
            if diff > 0:
                cost = diff * (COMM_BPS + SLIP_BPS) / 1e4
                cash -= diff + cost
                holdings[s] = holdings.get(s, 0) + diff / p
            elif diff < 0:
                proceeds = -diff
                cost = proceeds * (COMM_BPS + TAX_BPS + SLIP_BPS) / 1e4
                cash += proceeds - cost
                holdings[s] = holdings.get(s, 0) - proceeds / p
        turnovers.append(tot_turn / val if val > 0 else 0)

        # ── 다음 리밸런스까지 보유
        nd = rebal[i + 1]
        v = cash
        for s, sh in holdings.items():
            p2 = close.loc[nd, s]
            if pd.isna(p2):                      # 기간 중 소멸 → 마지막 가용가로 평가
                last = close[s].loc[:nd].dropna()
                p2 = last.iloc[-1] if len(last) else 0.0
            v += sh * p2
        if not np.isfinite(v): v = equity[-1] if equity else 1.0
        equity.append(max(v, 1e-12)); hist_dates.append(nd)

    eq = pd.Series(equity, index=pd.DatetimeIndex(hist_dates))
    eq = eq[~eq.index.duplicated(keep='last')].sort_index()
    return eq, np.mean(turnovers) * 12

def ew_market(close, turnover, f, uni, start, end, min_adtv=300_000_000):
    """'평균적인 종목'의 수익률 — 비용 없는 순수 기준선.
    종목 선택 능력이 없는 투자자가 얻는 결과. 전략은 이걸 이겨야 의미가 있다."""
    dates = close.loc[start:end].index
    rebal = [d for d in pd.Series(dates, index=dates).resample('ME').last().dropna().values
             if d in set(dates)]
    rets = []
    for i in range(len(rebal) - 1):
        d0, d1 = rebal[i], rebal[i + 1]
        elig = eligibility(close, turnover, f, uni, d0, min_adtv)
        syms = elig[elig].index
        if len(syms) == 0: rets.append((d1, 0.0)); continue
        p0, p1 = close.loc[d0, syms], close.loc[d1, syms]
        r = (p1 / p0 - 1)
        r = r[r.abs() < 3.0]                      # 극단 이상치 방어
        rets.append((d1, r.mean() if len(r) else 0.0))
    s = pd.Series(dict(rets)).sort_index()
    return (1 + s).cumprod()

# ────────────────────────────────────────────────── 성과지표
def metrics(eq, bench_eq=None, rf=0.03):
    r = eq.pct_change().dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
    dd = eq / eq.cummax() - 1
    mdd = dd.min()
    ann_vol = r.std() * np.sqrt(12)
    sharpe = (cagr - rf) / ann_vol if ann_vol > 0 else np.nan
    downside = r[r < 0].std() * np.sqrt(12)
    sortino = (cagr - rf) / downside if downside > 0 else np.nan
    m = {'CAGR': cagr, 'MDD': mdd, 'Vol': ann_vol, 'Sharpe': sharpe,
         'Sortino': sortino, 'Calmar': cagr / abs(mdd) if mdd else np.nan,
         '월승률': (r > 0).mean(), '최종배수': eq.iloc[-1] / eq.iloc[0], 'years': yrs}
    if bench_eq is not None:
        b = bench_eq[~bench_eq.index.duplicated(keep='last')].sort_index()
        b = b.reindex(eq.index.union(b.index)).ffill().reindex(eq.index)
        br = b.pct_change()
        ex = (r - br.reindex(r.index)).dropna()
        m['초과CAGR'] = cagr - ((b.iloc[-1] / b.iloc[0]) ** (1 / yrs) - 1)
        m['IR'] = ex.mean() / ex.std() * np.sqrt(12) if ex.std() > 0 else np.nan
        m['벤치대비승률'] = (ex > 0).mean()
    return m

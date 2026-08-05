"""생존편향 없는 한국주식 일봉 수집.
현재 상장 + 과거 상장폐지 종목을 모두 포함한다."""
import warnings, time, os, sys, json
warnings.filterwarnings('ignore')
import pandas as pd, numpy as np
import FinanceDataReader as fdr
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT = os.path.dirname(os.path.abspath(__file__))
START, END = '2008-01-01', '2025-12-31'

def build_universe():
    cur = fdr.StockListing('KRX')
    cur = cur[cur.Market.isin(['KOSPI', 'KOSDAQ'])].copy()
    cur['Symbol'] = cur['Code']
    cur['DelistingDate'] = pd.NaT
    cur['ListingDate'] = pd.NaT
    cur = cur[['Symbol', 'Name', 'Market', 'ListingDate', 'DelistingDate']]
    cur['status'] = 'listed'

    dl = fdr.StockListing('KRX-DELISTING')
    dl['DelistingDate'] = pd.to_datetime(dl['DelistingDate'], errors='coerce')
    dl['ListingDate'] = pd.to_datetime(dl['ListingDate'], errors='coerce')
    dl = dl[(dl.SecuGroup == '주권') &
            (dl.Market.isin(['KOSPI', 'KOSDAQ'])) &
            (dl.DelistingDate >= '2008-01-01')].copy()
    dl = dl[['Symbol', 'Name', 'Market', 'ListingDate', 'DelistingDate', 'Reason']]
    dl['status'] = 'delisted'

    uni = pd.concat([cur, dl], ignore_index=True)
    # 보통주만: 우선주(코드 끝자리 != 0) 및 스팩 제외
    uni = uni[uni.Symbol.str.match(r'^\d{5}0$')]
    uni = uni[~uni.Name.str.contains('스팩|기업인수목적', na=False)]
    uni = uni.drop_duplicates('Symbol', keep='first').reset_index(drop=True)
    return uni

def fetch(sym):
    for attempt in range(3):
        try:
            df = fdr.DataReader(sym, START, END)
            if df is None or len(df) == 0:
                return sym, None
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            df = df[df.Close > 0]
            df['Symbol'] = sym
            return sym, df.reset_index()
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return sym, None

if __name__ == '__main__':
    t0 = time.time()
    uni = build_universe()
    uni.to_parquet(f'{OUT}/universe.parquet')
    syms = uni.Symbol.tolist()
    print(f'[universe] {len(syms)} 종목 (상장 {(uni.status=="listed").sum()} / 폐지 {(uni.status=="delisted").sum()})', flush=True)

    frames, fails, done = [], [], 0
    with ThreadPoolExecutor(16) as ex:
        futs = {ex.submit(fetch, s): s for s in syms}
        for f in as_completed(futs):
            sym, df = f.result()
            done += 1
            if df is None:
                fails.append(sym)
            else:
                frames.append(df)
            if done % 250 == 0:
                print(f'[{done}/{len(syms)}] ok={len(frames)} fail={len(fails)} {time.time()-t0:.0f}s', flush=True)

    px = pd.concat(frames, ignore_index=True)
    px.columns = [c if c != 'index' else 'Date' for c in px.columns]
    px['Date'] = pd.to_datetime(px['Date'])
    px = px.sort_values(['Symbol', 'Date'])
    px.to_parquet(f'{OUT}/prices.parquet', index=False)

    # 벤치마크 지수
    bm = {}
    for code, name in [('KS11', 'KOSPI'), ('KQ11', 'KOSDAQ'), ('KS200', 'KOSPI200')]:
        try:
            b = fdr.DataReader(code, START, END)[['Close']].rename(columns={'Close': name})
            bm[name] = b[name]
        except Exception as e:
            print(f'  bench {name} fail: {e}', flush=True)
    pd.DataFrame(bm).to_parquet(f'{OUT}/bench.parquet')

    print(f'[done] rows={len(px):,} symbols={px.Symbol.nunique()} fails={len(fails)} '
          f'기간 {px.Date.min().date()}~{px.Date.max().date()} {time.time()-t0:.0f}s', flush=True)
    json.dump(fails, open(f'{OUT}/fails.json', 'w'))

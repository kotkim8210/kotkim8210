# 💰 pricing — 공급단가 + 시세 추적

옥수수 장사의 손익은 **두 숫자**로 결정된다.

| 추적 대상 | 무엇 | 소스 | 이 폴더의 파일 |
|---|---|---|---|
| **시세** (시장가) | 손님이 실제로 내는 값 = 경쟁사 판매가 | 당근 (시세추적기로 수집) | `market_prices.json` |
| **공급단가** (매입가) | 내가 사오는 도매가 | PBF Company 파트너 어드민 | `supply_prices.json` |

> **마진 = 시세 − 공급가 − 수수료.**
> 등록 판매가(list)는 '받고 싶은 값'일 뿐 실제 전환은 시세 근처에서 일어난다.
> 그래서 list 기준이 아니라 **시세 기준 마진**을 봐야 한다 → 두 추적을 *함께* 돌린다.

## 파일

| 파일 | 용도 |
|---|---|
| `supply_prices.json` | 공급가(매입가) 스냅샷 원장. PBF 캡처를 받을 때마다 한 블록씩 append. **비공개** |
| `market_prices.json` | 시세(경쟁사 판매가) 참고 원장. 라이브 소스는 시세추적기 구글시트 |
| `build_report.py` | 위 둘 + `../listings/products.json`(판매가)을 조인해 마진표 생성 (stdlib만, 무설치) |
| `MARGIN_REPORT.md` | 자동 생성 결과물. **직접 편집 금지** — JSON 고치고 재생성 |

## 갱신 루틴

**① 공급가 업데이트** (PBF 어드민 새 캡처를 받았을 때)
1. `supply_prices.json`의 `snapshots`에 새 블록 추가 (`seq`+1, `date` 갱신, 12개 옵션)
2. `python3 pricing/build_report.py`

**② 시세 업데이트** (시세추적기 데이터가 모였을 때)
1. 추적기 대시보드의 옵션별 최저/평균 단위당단가를 보고 `market_prices.json`의
   `references`에 갱신 (실측값은 `"sample": false`)
2. `python3 pricing/build_report.py`

**③ 수수료 가정 변경** (실제 당근 수수료 확인 시)
- `build_report.py` 상단 `PG_FEE_RATE` / `PLATFORM_FEE_RATE` / `PACKAGING_COST`만 고치고 재실행

## 현재 상태 (2026-06-13)

- 공급가: **중품 −18~29% 폭락** (시즌 종료). 특품 거의 보합, 애플 보합.
  → 협상 없이도 시세 기준 마진이 ~0%대 → ~30%대로 회복. **협상 보류**가 맞다.
- 시세: `corn-mid`(중품)만 임시 예시값 보유. **특품·애플 실측 시세는 수집 대기** —
  시세추적기로 채워야 마진표 시세 열이 완성된다.

## ⚠️ 비공개 주의

`supply_prices.json` / `MARGIN_REPORT.md`의 **공급가는 도매 매입가(비공개)**.
`listings/products.json`·북마클릿 등 **고객에게 나가는 산출물에는 절대 넣지 말 것.**
(현재 products.json·북마클릿에는 판매가만 들어 있고 cost는 없음 — 그대로 유지.)

## 관련

- 시세추적기 설치/사용: [`../시세추적기_설치가이드_v3.md`](../시세추적기_설치가이드_v3.md)
- 시세추적기 코드: [`../당근_시세추적기_v3.gs`](../당근_시세추적기_v3.gs)
- 보류된 협상 초안: [`../legacy/negotiation_drafts.md`](../legacy/negotiation_drafts.md)

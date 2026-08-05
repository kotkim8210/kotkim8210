# 7. 출력 형식 사양 (Report Spec)

## 7.0 두 가지 산출물

모든 분석은 **사람이 읽는 마크다운**과 **기계가 읽는 JSON**을 동시에 생성한다(§7 요구).
둘은 같은 계산 결과에서 렌더링되므로 내용이 어긋날 수 없다.

```python
def render_report(score, signal, store) -> tuple[str, dict]:
    payload = build_payload(score, signal, store)   # 단일 진실 소스
    return render_markdown(payload), payload        # 같은 데이터에서 두 형태
```

**A~F 섹션 구조는 고정 계약이다.** 활성 시나리오가 있을 때만 D와 E 사이에 **S 섹션**이 삽입된다
(§10~11 확장). 시나리오가 없으면 S 섹션은 아예 나타나지 않는다.

---

## 7.1 마크다운 리포트 템플릿

````markdown
# {종목명} ({티커}) — 중장기 분석 리포트
> 기준일 {as_of} · 등급 **{grade}** · 종합 **{total}/100** · 신뢰도 **{confidence}/100**
> 데이터 커버리지 {data_coverage:.0%} {⚠️ 경고 배지들}

## A. 종목 개요
- **업종** {sector} (KSIC {ksic}) · **시가총액** {mktcap}억원 · **상장** {listing_date}
- **최근 5~10년 주요 변화**
  | 연도 | 매출 | 영업이익 | 주요 사건 |
  |---|---|---|---|
- **현재 위치**: 52주 {pos_52w}% 구간 · PER {per} (5년 백분위 {per_pct}) · PBR {pbr} ({pbr_pct})

## B. 공시/재무 분석
### B-1. 재무 추이 (최근 5~10년)
| 항목 | FY-4 | FY-3 | FY-2 | FY-1 | 최근4Q |
|---|---|---|---|---|---|
| 매출 / 영업이익 / 순이익 / OCF / FCF / 부채비율 / ROE / 영업이익률 |

- **이익의 질**: `accrual_ratio` {v} ({judgment})
- **F축 {F}/100** — 기여: F1 {..} F2 {..} F3 {..} F4 {..} F5 {..} F6 {..} F7 {..}

### B-2. 최근 공시 핵심 이벤트
| 접수일 | 유형 | 내용 | 해석 | 영향 |
|---|---|---|---|---|

- **D축 {D}/100**

### B-3. 긍정 / 부정 요인 (분리 제시)
| ✅ 긍정 | ❌ 부정 |
|---|---|

## C. 수급/기술적 분석
### C-1. 수급
| 주체 | 20일 | 60일 | 120일 | 추세 |
|---|---|---|---|---|
| 외국인 / 기관 / 연기금 / 개인 |
- **수급-가격 다이버전스**: {yes/no} — {설명}
- **S축 {S}/100**

### C-2. 주봉/월봉 추세
- 월봉: 12M 이평 {above/below}, 기울기 {+/-}, 이격도 {v}
- 주봉: 20W/60W {골든/데드크로스}, 60W 이평 {돌파/이탈}
- 박스권: 104주 상단 {v}원 — 현재 {돌파/미돌파}
- RSI(주봉 14) {v} → {구간 판정}
- **T축 {T}/100**

### C-3. 가격 구간 판정
| 구간 | 가격대 | 근거 |
|---|---|---|
| 🟢 매수 적정 | {low}~{high} | |
| 🟡 주의 | {..} | |
| 🔴 매도 경고 | {..} | |

## D. 커뮤니티/정성 분석
- **다수 의견**: {낙관/중립/비관} (감성 백분위 {v})
- **근거 있는 의견인가**: `evidence_ratio` {v} — {해석}
- **검색 관심도** `hype_z` {v} {과열 배지}
- **반복되는 논리 3가지**: 1) .. 2) .. 3) ..
- **데이터로 검증한 결과**: {타당/부분타당/근거없음} — {구체적 반박 또는 확인}
- **역발상 가능성**: {평가}
- **Q축 {Q}/100 · C축 {C}/100**

## S. 시나리오 트랙   ※활성 시나리오가 있을 때만 표시
- **연결 시나리오**: {title} ({catalyst_type}, 발표 {announced_at})
- **생애주기 단계**: {lifecycle_stage} → 4단계 모델 상 **{①~④}단계**
- **포지션 상태**: `{WATCH|CONFIRM_PENDING|SCALE_IN|SCALE_UP|LAPSED}`
- **연결 강도** {link_strength} — 근거: {link_basis}
  - 매칭 사업부문 매출비중 {v}% × 밸류체인 {계수} × 정책구체성 {계수}
- **E축 {E}/100**
  | E1 정책적합 | E2 실적반영 | E3 선반영위험 | E4 단타과열 | E5 지속성 |
  |---|---|---|---|---|
- **확인 4항목**: 실적 {✅/❌} · 수급 {✅/❌} · 차트 {✅/❌} · 공시 {✅/❌} → {n}/4
- **판정**: {매수 가능 단계 / 아직 기대 단계 — 매수 금지}

## E. 투자 결론
> ## {매수 / 관망 / 매도}
> 신뢰도 **{confidence}/100** · 종합 **{total}/100** · 등급 **{grade}**

**이유**
1. …
2. …
3. … (3~5개, 각각 근거 데이터 각주 포함)

**전제 조건** (이것이 깨지면 결론이 바뀐다)
- …

**리스크**
| 리스크 | 발생 시 영향 | 관측 지표 |
|---|---|---|

**분할매수 규칙**
| 차수 | 비중 | 조건 |
|---|---|---|
| 1차 | 40% | |
| 2차 | 30% | |
| 3차 | 30% | |

**분할매도 / 이탈 규칙**
| 트리거 | 조치 |
|---|---|

**게이트 판정**
- 하드 게이트: {통과 / 위반 항목}
- 4중 동시충족: F {✅/❌} D {✅/❌} S·T {✅/❌} C {✅/❌}
- 과열 거부권: {n}/5 {🚫발동 / 정상}

## F. 자동화 룰셋
```
# 이 종목에 적용되는 발동 조건 (재현 가능 형태)
IF  매출YoY > {x}% AND 영업이익률개선 AND 외국인20일순매수 > 0
AND 월봉 종가 > MA12 AND RSI_W14 <= 78
AND 과열거부권 < 3
THEN 매수후보 (사이징 {y}%)

IF  RSI_M >= 75 AND 감성백분위 >= 80 AND 기관20일순매수 < 0
THEN 분할매도 1/3
```
- 발동한 룰: {rule_ids}
- 차단한 룰: {blocked_by}
- 매칭 패턴: {pattern_ids} (상태: 가설/검증됨)

---
⚠️ 이 리포트는 리서치 보조 자료이며 투자 자문이 아닙니다. 모든 신호는 확률적 추정이고,
과거 패턴의 반복은 보장되지 않습니다. 최종 판단과 결과의 책임은 투자자 본인에게 있습니다.
데이터 기준 {as_of} · 설정 버전 {config_hash} · 룰 버전 {rules_version}
````

---

## 7.2 금칙어 필터 (`report/guard.py`)

§8의 "무조건 오른다는 표현을 금지한다"를 렌더링 단계에서 강제한다.

```python
FORBIDDEN = [
    r"무조건", r"확실히\s*(오른|상승)", r"보장", r"100%\s*(수익|상승)",
    r"반드시\s*(오른|간다)", r"손실\s*없", r"안전한\s*투자",
    r"지금\s*아니면", r"마지막\s*기회",
]

def guard(markdown: str) -> str:
    """금칙어 발견 시 렌더링을 실패시킨다. 치환하지 않는다."""
    for pat in FORBIDDEN:
        if re.search(pat, markdown):
            raise ForbiddenExpressionError(pat)
    return markdown
```

**치환이 아니라 예외를 던진다.** 조용히 고치면 왜 그런 문장이 생성됐는지 알 수 없다.
템플릿이나 근거 생성 로직의 문제를 드러내는 것이 목적이다.

또한 **모든 결론에 다음 3요소가 있는지 검사**하고, 없으면 렌더링에 실패한다:
① 신뢰도 점수 ② 전제 조건 ③ 리스크 목록.

---

## 7.3 JSON 출력 (요약)

전체 스키마는 `schemas/report.schema.json`. 최상위 구조:

```json
{
  "meta": {
    "schema_version": "1.0", "as_of": "2026-08-05",
    "config_hash": "…", "rules_version": "…", "generated_at": "…"
  },
  "stock": { "code": "005930", "name": "…", "sector": "…", "ksic": "…",
             "market_cap": 0, "listing_date": "…" },
  "scores": {
    "total": 0, "grade": "A", "confidence": 0, "data_coverage": 0.0,
    "axes": {
      "F": { "value": 0, "coverage": 0.0, "components": { "F1": 0, "…": 0 } },
      "D": {}, "S": {}, "T": {}, "E": {}, "Q": {}, "C": {}
    }
  },
  "gates": {
    "hard": { "passed": true, "violations": [] },
    "soft": { "penalties": [], "size_multiplier": 1.0 },
    "quad_gate": { "F": true, "D": true, "ST": true, "C": true, "passed": true },
    "overheat_veto": { "count": 0, "triggered": [], "blocked": false }
  },
  "scenario": {
    "active": false, "scenario_id": null, "state": null,
    "link_strength": null, "link_basis": null,
    "lifecycle_stage": null, "confirmations": { "earnings": false, "flow": false,
                              "chart": false, "disclosure": false, "count": 0 }
  },
  "signal": {
    "action": "BUY_CANDIDATE", "size_pct": 6.0, "tranche": 1,
    "triggered_rules": ["BUY_CORE"], "blocked_by": [], "warnings": [],
    "entry_plan": [ { "tranche": 1, "pct": 40, "condition": "…" } ],
    "exit_plan":  [ { "trigger": "…", "action": "TRIM_1_3" } ]
  },
  "rationale": [ { "point": "…", "evidence": { "metric": "…", "value": 0,
                                               "source": "dart:20260315000123" } } ],
  "risks": [ { "risk": "…", "impact": "…", "monitor": "…" } ],
  "assumptions": [ "…" ],
  "patterns": [ { "id": "KP-01", "name": "…", "status": "가설", "matched": true } ],
  "audit": { "input_hash": "…", "feature_snapshot_ref": "…", "trial_id": null }
}
```

### 설계 포인트

| 필드 | 왜 필요한가 |
|---|---|
| `rationale[].evidence.source` | 모든 근거에 **출처 ID**(공시 접수번호 등)를 단다. 검증 가능성 확보 |
| `scores.axes.*.components` | 축 점수의 내부 분해. "왜 이 점수인가"를 사후 재현(INV-4) |
| `gates.*` | 통과/차단 이유를 명시. 좋은 종목이 왜 안 나왔는지도 설명 가능 |
| `confidence` ≠ `total` | "얼마나 좋은가"와 "얼마나 믿을 만한가"를 분리 |
| `audit.input_hash` | 같은 입력 → 같은 출력 재현성 보장 |
| `patterns[].status` | 가설 패턴을 검증된 것처럼 보이게 하지 않는다 |

---

## 7.4 스크리닝 결과 JSON (`screen`)

```json
{
  "meta": { "as_of": "…", "universe_size": 2700, "config_hash": "…" },
  "funnel": {
    "universe": 2700, "after_hard_gates": 1180, "after_quad_gate": 47,
    "after_veto": 41, "final_candidates": 30
  },
  "candidates": [
    { "rank": 1, "code": "…", "name": "…", "total": 0, "grade": "S",
      "confidence": 0, "track": "value|scenario",
      "axes": { "F": 0, "D": 0, "S": 0, "T": 0, "E": 0, "Q": 0, "C": 0 },
      "one_line": "…", "patterns": ["KP-01"], "warnings": [] }
  ],
  "excluded_summary": { "G1_관리종목": 45, "G6_유동성": 820, "…": 0 }
}
```

**`funnel`이 이 시스템의 건강 진단서다.** 2,700 → 30으로 좁혀지는 각 단계의 잔존 수를 매일 기록하면,
어느 날 게이트가 고장 났을 때(예: 갑자기 후보가 300개) 즉시 알아챌 수 있다.
`excluded_summary`는 "왜 대부분이 탈락했는가"를 보여줘 게이트 임계값 조정의 근거가 된다.

# 5. Claude Code 프로젝트 구조

## 5.1 전체 트리

```
kr-quant/
├── README.md
├── pyproject.toml                  # 의존성·빌드·lint 설정 (uv 또는 poetry)
├── Makefile                        # setup / bootstrap / test / screen / backtest
├── .env.example                    # DART_API_KEY, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
├── .gitignore                      # data/, .env, reports/ 제외
│
├── config/
│   ├── settings.yaml               # 전역 설정: 경로·쿼터·스케줄·텍스트 소스 on/off
│   ├── scoring.yaml                # ★7축 가중치·하위지표 배점·정규화 방식
│   ├── rules.yaml                  # ★게이트·매수/매도/경고 룰 (DSL)
│   ├── universe.yaml               # 유니버스 필터·업종 분류·제외 목록
│   ├── costs.yaml                  # 수수료·세율(effective_from 시계열)·슬리피지
│   ├── patterns.yaml               # 패턴 라이브러리 (KP-01~, ANTI-01~)
│   └── overheat_lexicon.yaml       # 과열 관용구 사전
│
├── src/krquant/
│   ├── __init__.py
│   ├── cli.py                      # typer 기반 CLI 진입점
│   │
│   ├── core/
│   │   ├── config.py               # YAML 로드 + pydantic 검증 + 설정 해시
│   │   ├── types.py                # Score, Signal, Gate, ScenarioState 등 도메인 타입
│   │   ├── calendar.py             # 한국 거래일·휴장일·결산 캘린더
│   │   ├── errors.py               # SchemaDriftError, RateLimitError, DataGapError
│   │   ├── logging.py              # 구조화 로깅 (JSON)
│   │   └── audit.py                # 감사추적: 입력해시·룰버전·기여도 기록 (INV-4)
│   │
│   ├── io/
│   │   ├── http.py                 # 재시도·백오프·타임아웃 통합 클라이언트
│   │   ├── ratelimit.py            # 토큰버킷 + 일일 쿼터 관리
│   │   ├── cache.py                # L1 메모리 LRU + L2 디스크(TTL·콘텐츠해시)
│   │   └── store.py                # ★PITStore — 전 시스템의 단일 데이터 관문
│   │
│   ├── collectors/
│   │   ├── base.py                 # Collector 프로토콜 (fetch → bronze 저장)
│   │   ├── dart/
│   │   │   ├── endpoints.py        # 엔드포인트 상수 (변경 시 여기만 수정)
│   │   │   ├── corp_code.py        # 고유번호 매핑
│   │   │   ├── disclosure.py       # list.json 공시 목록
│   │   │   ├── financial.py        # 재무제표 (+ rcept_dt 결합)
│   │   │   ├── ownership.py        # majorstock / elestock
│   │   │   ├── major_report.py     # 주요사항보고서군
│   │   │   └── document.py         # 사업보고서 본문 XML
│   │   ├── krx/
│   │   │   ├── price.py            # 일봉 OHLCV
│   │   │   ├── flow.py             # 투자자별 순매수
│   │   │   ├── listing.py          # 종목 마스터 + 상장폐지 이력
│   │   │   └── adapter.py          # 🔶 비공식 경로 격리 계층
│   │   ├── kind.py                 # 관리종목·시장경보·불성실공시 (HTML)
│   │   ├── text/
│   │   │   ├── naver_search.py     # 뉴스·블로그·카페 언급량
│   │   │   ├── naver_datalab.py    # ⭐검색 관심도 (hype_z)
│   │   │   └── rss.py              # 언론사·정책브리핑 RSS
│   │   └── policy/
│   │       ├── korea_kr.py         # 정책브리핑 보도자료
│   │       ├── law_go_kr.py        # 국가법령정보 (제개정·시행일)
│   │       ├── assembly.py         # 열린국회 의안
│   │       └── fiscal.py           # 열린재정 예산·집행
│   │
│   ├── normalize/
│   │   ├── master.py               # 종목 마스터 (상장/폐지/시장구분 이력)
│   │   ├── accounts.py             # 계정과목 표준화 매핑 테이블
│   │   ├── financials.py           # 연결 우선, 분기 환산, 단위 통일(원)
│   │   ├── prices.py               # 수정주가, 주봉·월봉 리샘플
│   │   ├── segments.py             # 부문별 매출 파싱 (LLM 보조 + 검토 큐)
│   │   └── quality.py              # DQ-01~09 검사
│   │
│   ├── features/                   # ★전부 as_of 시그니처. 순수함수.
│   │   ├── fundamental.py          # F1~F7, accrual_ratio, F_direction
│   │   ├── disclosure.py           # D1~D6, contract_impact
│   │   ├── flow.py                 # S1~S6, 수급-가격 다이버전스
│   │   ├── technical.py            # T1~T6 (주봉·월봉 전용)
│   │   ├── text.py                 # 감성, evidence_ratio, hype_z
│   │   └── event.py                # 이벤트 컨텍스트(액면분할 등) 피처
│   │
│   ├── scenario/                   # ⭐시나리오 트랙
│   │   ├── catalog.py              # 촉매 이벤트 등록·생애주기 관리
│   │   ├── mapping.py              # 정책 → 종목 매핑 (link_strength)
│   │   ├── scores.py               # E1~E5 계산
│   │   ├── state.py                # 상태머신 (WATCH→…→EXIT)
│   │   └── confirm.py              # 확인 4항목 판정
│   │
│   ├── scoring/
│   │   ├── normalize.py            # 업종 백분위 / 절대구간 / 자기이력 Z
│   │   ├── axes.py                 # F·D·S·T·E·Q·C 축 점수
│   │   ├── aggregate.py            # 가중합 + 등급 + confidence
│   │   └── attribution.py          # 축별 기여도 분해
│   │
│   ├── rules/
│   │   ├── dsl.py                  # YAML 룰 파서·평가기
│   │   ├── gates.py                # 하드·소프트 게이트, 4중 동시충족
│   │   ├── veto.py                 # ⭐과열 거부권 (V1~V5)
│   │   ├── buy.py                  # BUY_CORE / CONTRARIAN / SCENARIO
│   │   ├── sell.py                 # SELL_* 룰
│   │   └── sizing.py               # 사이징·분할매수 스케줄·제약
│   │
│   ├── patterns/
│   │   ├── library.py              # patterns.yaml 로드·검증
│   │   ├── matcher.py              # 현재 종목 ↔ 패턴 매칭
│   │   └── miner.py                # 성공사례 → 조건 추출 (결정트리 깊이≤3)
│   │
│   ├── backtest/
│   │   ├── engine.py               # 이벤트 드리븐 루프
│   │   ├── broker.py               # 체결 (상한가·거래정지·유동성 제약)
│   │   ├── portfolio.py            # 포지션·현금·평가 회계
│   │   ├── costs.py                # 수수료·세금(시계열)·슬리피지
│   │   ├── metrics.py              # CAGR·MDD·Sharpe·IR·Calmar 등
│   │   ├── bias_check.py           # B-01~08 편향 검사
│   │   ├── validate.py             # 워크포워드·purged k-fold·DSR·랜덤대조군
│   │   └── trials.py               # 시도 레지스트리 (다중검정 보정용)
│   │
│   ├── eventstudy/
│   │   ├── car.py                  # 시장모형 AR/CAR 계산
│   │   ├── windows.py              # 1주·1개월·3개월·6개월 구간
│   │   └── classify.py             # A(즉시급등소멸)/B(지연상승)/C(하락) 분류
│   │
│   └── report/
│       ├── markdown.py             # A~F 섹션 렌더링
│       ├── json_out.py             # 스키마 준수 JSON
│       ├── charts.py               # 주봉·월봉·수급·CAR 차트 (PNG)
│       └── guard.py                # ⭐금칙어 필터 ("무조건 오른다" 등 차단)
│
├── tests/
│   ├── contract/                   # 외부 API 스키마 계약 테스트 (주기 실행)
│   ├── unit/                       # 피처·점수·룰 단위 테스트
│   ├── golden/                     # 고정 입력 → 고정 출력 회귀 테스트
│   └── pit/                        # ★선견편향 방지 전용 테스트 (가장 중요)
│
├── notebooks/                      # 탐색·시각화 (운영 경로 아님)
├── reports/                        # 산출물 (gitignore)
├── data/                           # bronze/silver/gold/cache (gitignore)
│
└── .claude/
    ├── commands/
    │   ├── screen.md
    │   ├── deepdive.md
    │   ├── backtest.md
    │   ├── watchlist.md
    │   └── scenario.md
    └── settings.json
```

---

## 5.2 핵심 인터페이스 시그니처

구현 시 이 시그니처를 먼저 고정하고 내부를 채운다. 타입이 설계를 강제한다.

```python
# core/types.py ─────────────────────────────────────────────────────────
Axis = Literal["F", "D", "S", "T", "E", "Q", "C"]
ScenarioState = Literal["WATCH", "CONFIRM_PENDING", "SCALE_IN",
                        "SCALE_UP", "LAPSED", "EXIT"]
Action = Literal["BUY_CANDIDATE", "HOLD", "TRIM", "EXIT", "NO_NEW_BUY", "SKIP"]

@dataclass(frozen=True)
class AxisScore:
    axis: Axis
    value: float | None          # 0~100, 판정 불가 시 None
    coverage: float              # 관측된 하위지표 비율 0~1
    components: dict[str, float] # 하위지표별 점수 (감사추적)

@dataclass(frozen=True)
class StockScore:
    code: str
    as_of: date
    axes: dict[Axis, AxisScore]
    total: float
    grade: Literal["S", "A", "B", "C", "D"]
    confidence: float            # 0~100 — total과 별개
    data_coverage: float

@dataclass(frozen=True)
class Signal:
    code: str
    as_of: date
    action: Action
    size_pct: float | None
    tranche: int | None          # 분할매수 차수 1·2·3
    triggered_rules: list[str]
    blocked_by: list[str]        # 게이트·거부권 발동 내역
    warnings: list[str]
    rationale: list[str]         # 사람이 읽는 근거 3~5개
    audit: AuditRecord

# io/store.py ───────────────────────────────────────────────────────────
class PITStore:
    def __init__(self, as_of: date, root: Path): ...
    def universe(self, market: str | None = None) -> list[str]: ...
    def prices(self, code: str, lookback: int, freq: Literal["D","W","M"]) -> pd.DataFrame: ...
    def financials(self, code: str, periods: int = 20) -> pd.DataFrame: ...
    def flows(self, code: str, lookback: int) -> pd.DataFrame: ...
    def disclosures(self, code: str, lookback: int) -> pd.DataFrame: ...
    def scenarios(self, code: str | None = None) -> pd.DataFrame: ...
    def text_stats(self, code: str, lookback: int) -> pd.DataFrame: ...
    def sector_peers(self, code: str) -> list[str]: ...

# features/ ─────────────────────────────────────────────────────────────
def fundamental_features(code: str, store: PITStore) -> dict[str, float | None]: ...
def flow_features(code: str, store: PITStore) -> dict[str, float | None]: ...
def technical_features(code: str, store: PITStore) -> dict[str, float | None]: ...
# … 전부 (code, store) → dict 형태로 통일. store가 as_of를 이미 알고 있다.

# scoring/ ──────────────────────────────────────────────────────────────
def score_stock(code: str, store: PITStore, cfg: ScoringConfig) -> StockScore: ...

# scenario/ ─────────────────────────────────────────────────────────────
def compute_link_strength(scenario_id: str, code: str, store: PITStore) -> tuple[float, str]:
    """returns (link_strength 0~1, link_basis 근거텍스트)"""
def transition(pos: ScenarioPosition, score: StockScore,
               store: PITStore) -> tuple[ScenarioState, str]:
    """returns (다음 상태, 전이 사유)"""

# rules/ ────────────────────────────────────────────────────────────────
def evaluate(score: StockScore, feats: dict, portfolio: Portfolio,
             cfg: RulesConfig) -> Signal: ...
def overheat_veto(feats: dict, score: StockScore) -> tuple[int, list[str]]:
    """returns (충족 개수, 발동 조건 목록)"""

# backtest/ ─────────────────────────────────────────────────────────────
def run_backtest(start: date, end: date, cfg: Config) -> BacktestResult: ...
def check_biases(result: BacktestResult) -> list[BiasCheck]:
    """B-01~08. 하나라도 실패하면 성과 출력 금지"""

# eventstudy/ ───────────────────────────────────────────────────────────
def compute_car(events: pd.DataFrame, store: PITStore,
                windows: list[tuple[int,int]]) -> pd.DataFrame: ...

# report/ ───────────────────────────────────────────────────────────────
def render_report(score: StockScore, signal: Signal,
                  store: PITStore) -> tuple[str, dict]:
    """returns (markdown, json_dict) — 항상 둘 다 생성 (§7 요구)"""
```

---

## 5.3 CLI

```bash
krq bootstrap  --years 10                    # 초기 전량 적재
krq collect    --since 2026-08-01            # 증분 수집
krq screen     --date 2026-08-05 --top 30 --track all|value|scenario
krq deepdive   005930 --date 2026-08-05 --out reports/
krq watchlist  --sync                        # 보유·관심 종목 매도/경고 점검
krq scenario   list|show <id>|link <id> <code>
krq backtest   --from 2015-01-01 --to 2025-12-31 --walk-forward --seed 42
krq eventstudy --event-type "단일판매공급계약" --windows 5,21,63,126
krq mine       --label-horizon 12m           # 패턴 후보 추출
krq validate   --check biases|dq|contracts
```

---

## 5.4 Claude Code 슬래시 명령

이 저장소의 `.claude/commands/` 규약을 따른다 (CLAUDE.md §2).

| 명령 | 역할 |
|---|---|
| `/screen` | 오늘의 후보 스캔 → 상위 N개 요약 + 각 종목 한 줄 근거 |
| `/deepdive <종목>` | A~F 전체 리포트 생성 (MD + JSON) |
| `/scenario` | 활성 시나리오 보드 — 상태별 종목 현황, 신규 촉매 알림 |
| `/backtest` | 백테스트 실행 → 편향 체크리스트부터 보고 |
| `/watchlist` | 보유 종목 매도 신호·경고 점검 |

`/deepdive` 명령 정의 예시:

```markdown
---
description: 단일 종목 A~F 심층 리포트 생성 (공시·재무·수급·기술·정성·시나리오)
---
1. `krq deepdive $ARGUMENTS --out reports/` 실행
2. 생성된 JSON을 읽어 A~F 섹션이 모두 채워졌는지 검증
3. `data_coverage < 0.7` 이면 리포트 상단에 신뢰도 경고를 명시
4. 결론 섹션의 금칙어("무조건", "확실히 오른다") 위반 여부 확인
5. 사용자에게 E(투자 결론)·F(자동화 룰셋) 섹션을 먼저 요약해 제시
```

---

## 5.5 테스트 전략

| 계층 | 내용 | 중요도 |
|---|---|---|
| `tests/pit/` | **선견편향 방지** — 과거 시점 조회에 미래 데이터가 섞이지 않는지 | ★★★ |
| `tests/contract/` | 외부 API 스키마 계약 (1건 fetch → 필수 필드 존재) | ★★★ |
| `tests/golden/` | 고정 입력 → 고정 점수. 룰 수정 시 회귀 감지 | ★★ |
| `tests/unit/` | 피처 산식·게이트 논리·상태 전이 | ★★ |

### PIT 테스트가 최우선인 이유
이 시스템에서 가장 위험한 버그는 **에러를 내지 않고 조용히 좋은 결과를 만드는 버그**다.
선견편향은 예외를 발생시키지 않고 성과만 좋아지므로, 테스트로 잡지 못하면 영원히 발견되지 않는다.

```python
def test_no_lookahead_in_financials():
    """2024-03-01 시점 조회에 2023 사업보고서가 포함되면 안 된다
    (일반적으로 3월 하순 접수되므로)."""
    store = PITStore(as_of=date(2024, 3, 1), root=TEST_DATA)
    fin = store.financials("005930")
    assert (fin.rcept_dt <= date(2024, 3, 1)).all()
    assert not ((fin.fiscal_year == 2023) & (fin.report_type == "사업보고서")).any()

def test_universe_includes_delisted():
    """과거 시점 유니버스에 이후 상장폐지된 종목이 포함되어야 한다."""
    store = PITStore(as_of=date(2018, 6, 1), root=TEST_DATA)
    codes = store.universe()
    assert any(c in codes for c in KNOWN_DELISTED_AFTER_2018)
```

---

## 5.6 구현 로드맵

각 단계는 **끝나면 실제로 돌아가는 것**을 남긴다. 마지막에 한꺼번에 조립하지 않는다.

| Phase | 산출물 | 완료 기준 |
|---|---|---|
| **0. 골격** | config·types·PITStore 인터페이스·CLI 스텁·테스트 골격 | `krq --help` 동작, PIT 테스트가 실패하는 상태로 존재 |
| **1. 데이터** | 종목마스터(상폐 포함)·일봉·수급·DART 재무(PIT 저장) | `krq bootstrap` 완료, DQ-01~08 통과 |
| **2. 피처·점수** | F·D·S·T 4축 + 정규화 + 게이트 | `krq screen`이 후보 리스트 출력 |
| **3. 룰·리포트** | 매수·매도·경고 룰, A~F 리포트(MD+JSON) | `krq deepdive 005930` 완주 |
| **4. 백테스트** | 엔진·비용·편향검사·워크포워드 | B-01~08 전부 통과한 성과 리포트 |
| **5. 텍스트·역발상** | 뉴스·데이터랩·감성 → Q·C축 + 과열 거부권 | 7축 중 6축 가동 |
| **6. 시나리오** | 정책·법령 수집, 매핑, E축, 상태머신 | `krq scenario` 보드 동작 |
| **7. 이벤트스터디·마이닝** | CAR 엔진, 패턴 마이너 | 공시 유형별 CAR 곡선 산출 |

**Phase 2까지만 해도 쓸모가 있다.** 4축 스크리너 + 게이트만으로도 대부분의 종목을 걸러낸다.
텍스트·시나리오는 정확도를 높이지만, 없어도 시스템은 동작한다 — 의존성을 그렇게 설계했다.

### 단계별 위험 요소

| Phase | 예상 난관 | 대응 |
|---|---|---|
| 1 | DART 재무 계정과목 표준화 (기업마다 명칭 상이) | 매핑 테이블 + 미매핑 항목 리포트 |
| 1 | 상장폐지 종목 과거 데이터 확보 | 여러 소스 교차. 확보 실패 구간은 명시적으로 제외 기간 처리 |
| 2 | 업종 분류 기준 시점 변경 | 시점별 분류 이력 보존 |
| 4 | 백테스트 속도 (2,700종목 × 10년) | 피처 캐싱 + DuckDB 벡터 연산 |
| 6 | **부문별 매출 파싱** (가장 어려움) | LLM 보조 + 사람 검토 큐 + 실패 시 0.5 페널티 폴백 |
| 6 | 정책 표현 ↔ 사업 표현 어휘 불일치 | 임베딩 유사도 + 키워드 사전 병행, 결과는 WATCH로만 |

---

## 5.7 의존성 (최소 구성)

```toml
[project.dependencies]
pandas, numpy, pyarrow, duckdb        # 데이터
httpx, tenacity                        # HTTP + 재시도
pydantic, pyyaml                       # 설정 검증
typer, rich                            # CLI
pykrx, finance-datareader              # 한국 시장 데이터
scikit-learn                           # 패턴 마이닝(결정트리)
matplotlib                             # 차트
pytest, pytest-cov, ruff, mypy         # 개발
```

무거운 ML 프레임워크는 넣지 않는다. 이 시스템의 병목은 모델 표현력이 아니라
**데이터 품질과 편향 제거**이며, 복잡한 모델은 과최적화 위험만 키운다.

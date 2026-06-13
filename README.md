# kotkim8210

## 📊 당근 시세 추적기 v3

당근마켓 상품의 단위당 단가·평점·찜수를 기록하고, 매일 가격 변동과 신규 상품을 메일로 알림받는 무료 시스템.
구글시트 + Apps Script + 브라우저 북마클릿으로 동작합니다.

**v2 → v3 핵심 변경: 입력 자동화**
- 브라우저 북마클릿으로 당근 상품 페이지에서 **클릭 한 번**에 데이터 추출 → 시트 자동 기록
- Web App 엔드포인트 추가 (토큰 인증)
- 자동 단위 추론(kg/박스/개)과 자유 텍스트 옵션 파싱

| 파일 | 용도 |
|---|---|
| `당근_시세추적기_v3.gs` | 구글 Apps Script 코드. 시트의 Apps Script에 통째로 붙여넣기. |
| `시세추적기_설치가이드_v3.md` | 설치/사용 가이드 (한글). 여기부터 읽으세요. |
| `bookmarklet/install.html` | 북마클릿 드래그&드롭 설치 페이지. 브라우저로 열기. |
| `bookmarklet/bookmarklet.js` | 북마클릿 풀 소스 (읽기/수정용). |
| `bookmarklet/bookmarklet.min.js` | 압축본 (`javascript:` 프리픽스 포함). |

### 빠른 시작
1. [`시세추적기_설치가이드_v3.md`](./시세추적기_설치가이드_v3.md) 의 A섹션대로 설치
2. `bookmarklet/install.html` 을 브라우저로 열고 버튼을 북마크 바로 드래그
3. 당근 상품 페이지에서 북마클릿 클릭 → 모달 [전송] → 끝

---

## 🏪 당근스토어 상품등록 자동채움

도매상품(참외 / 초당옥수수 / 콜라비) 7종의 등록 초안 + 폼 자동채움 북마클릿.
당근스토어 상품등록 페이지에서 북마클릿 클릭 → 상품 선택 → 폼 자동 채움 + 클립보드 복사.

| 파일 | 용도 |
|---|---|
| `listings/drafts.md` | 7종 상품의 제목/상세설명/옵션가/해시태그/사진 가이드 (사람이 읽는 초안). |
| `listings/products.json` | 같은 데이터의 구조화 버전. 북마클릿이 임베드해 사용. |
| `bookmarklet/store_filler.js` | 자동채움 북마클릿 풀 소스. |
| `bookmarklet/store_filler.min.js` | 압축본 (`javascript:` 프리픽스 포함). |
| `bookmarklet/store_filler_install.html` | 북마클릿 드래그&드롭 설치 페이지. |

> ✅ **옥수수 시세 매칭 + 마진 회복 (2026-06-13)** — 시즌 종료로 공급가 자연 하락(중품 −18~29%) +
> 등록가를 시세 근처로 일괄 조정(중품 −31%, 특품 −23%, 애플 −27% 평균). 시세 기준 마진 ~0%대 → ~30%대.
> 수수료는 **당근 공식 안내인 통합 3.3%(결제+판매, VAT 포함)** 로 확정.
> 마진 현황 → [`pricing/MARGIN_REPORT.md`](./pricing/MARGIN_REPORT.md) · 협상 보류 초안 → [`legacy/negotiation_drafts.md`](./legacy/negotiation_drafts.md)

### 임베드된 상품
1. 성주 가정용 참외 (혼합과) — 1/2/3/5kg
2. 성주 가정용 참외 (중소과) — 1/1.5/3/5kg
3. 성주 가정용 참외 (로얄과) — 3/5kg
4. 제주 초당옥수수 (중품 9~14cm) — 5/10/15/20개
5. 제주 초당옥수수 (특품 14cm+) — 5/10/15/20개
6. 애플 초당옥수수 (특품) — 5/10/15/20개
7. 제주 콜라비 (정품) — 3/5/10kg

> 🍉 **수박**은 도매가 데이터 미수신으로 누락. 가격 알려주시면 같은 양식으로 추가됩니다.

### 빠른 시작
1. `bookmarklet/store_filler_install.html` 을 브라우저로 열고 주황 버튼을 북마크 바로 드래그
2. 당근스토어 상품등록 페이지 열기
3. 북마클릿 클릭 → 상품/옵션 선택 → [⚡ 자동채움] 또는 [복사]

---

## 💰 공급단가 + 시세 마진 추적 (`pricing/`)

손익은 **두 숫자**로 결정됩니다 — **시세**(손님이 내는 시장가)와 **공급단가**(내 매입가).
`마진 = 시세 − 공급가 − 수수료`. 등록 판매가가 아니라 시세 기준으로 봐야 현실적이라,
두 추적을 함께 돌리고 마진표를 자동 생성합니다.

| 파일 | 용도 |
|---|---|
| `pricing/supply_prices.json` | 공급가(매입가) 스냅샷 원장 — PBF 어드민 캡처마다 추가. **비공개** |
| `pricing/market_prices.json` | 시세(경쟁사 판매가) 참고 원장 — 라이브 소스는 시세추적기 구글시트 |
| `pricing/build_report.py` | 공급가·시세·판매가 조인 → 마진표 생성 (무설치, stdlib만) |
| `pricing/MARGIN_REPORT.md` | 자동 생성 마진 리포트 (직접 편집 금지) |
| `pricing/README.md` | 추적 모델·갱신 루틴 설명 |

```bash
python3 pricing/build_report.py    # JSON 갱신 후 재실행하면 MARGIN_REPORT.md 갱신
```

> ⚠️ 공급가는 **도매 매입가(비공개)**. `products.json`·북마클릿 등 고객 노출 산출물에는 절대 넣지 마세요.

---

## Claude Code 플러그인 (저장소 공통)

This repo is pre-configured to use the [`everything-claude-code`](https://github.com/affaan-m/everything-claude-code) plugin — a toolkit of subagents, skills, and automation hooks (code review, TDD, security scanning, formatting, multi-language patterns).

### Automatic setup

The project-level `.claude/settings.json` registers the marketplace and enables the plugin, so you don't need to run `/plugin` commands manually.

```bash
git clone <this-repo>
cd kotkim8210
claude
```

When Claude Code starts, approve the project-trust prompt. The marketplace `everything-claude-code` (source: `affaan-m/everything-claude-code`) is registered and the plugin `everything-claude-code@everything-claude-code` is enabled automatically.

Verify with:

```
/plugin list
/plugin marketplace list
```

### Manual fallback

If you opted out of project settings, run these inside Claude Code:

```
/plugin marketplace add affaan-m/everything-claude-code
/plugin install everything-claude-code@everything-claude-code
/plugin list
```

### Files

- `.claude/settings.json` — shared plugin/marketplace config (committed).
- `.claude/settings.local.json` — per-developer overrides (gitignored).

### Upstream

<https://github.com/affaan-m/everything-claude-code>

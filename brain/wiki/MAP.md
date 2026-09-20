# 🗺️ 지식 지도 (MAP) — 검색 인덱스

> 모든 검색(`/recall`)은 여기서 시작한다. 이 파일은 **작게** 유지한다(요약·링크만).
> 클로드는 이 인덱스로 위치를 좁힌 뒤 관련 주제 문서 1~3개만 펼쳐 몇 초 만에 답한다.

## 📊 통계
- 주제 문서: **13**
- 누적 통찰(insights): **4**
- 보관(archive): 0
- 마지막 수집(ingest): 2026-09-20 (유튜브 다계정·연좌제 → youtube-multi-account·reused-content·account-security 신설)
- 마지막 드림 시퀀스: 2026-06-14 (드림 #2 — 구식 항목 정리·브랜치 감사)

## 📚 주제 색인 (Topic Index)

### 방법론 · 핵심개념
- [[second-brain]] — 지식을 외부 시스템에 저장·연결하는 방법론. 수동 분류 시간을 없앤다. `#방법론 #핵심개념`
- [[zettelkasten]] — 원자적 노트 + 링크로 아이디어가 창발하는 메모 상자 방법론. 제2의 뇌의 지적 선조. `#방법론 #선행연구 #연결`
- [[claude-knowledge-system]] — 수집기·연결엔진·정제기 3 컴포넌트로 된 전체 아키텍처. `#아키텍처 #메타`
- [[session-independence]] — GitHub·API 키 없이 어떤 세션에서도 작동(자동화는 선택). 비용 최소화 정책. `#설계원칙 #운영 #비용`

### 클로드 코드 운영
- [[claude-code-skills]] — 스킬 설치 스코프(레포/유저/전역)·지속성, 로컬 PC↔클라우드 구분, 설치 안전. `#클로드코드 #스킬 #환경`

### 내 작업·자산 (브랜치 색인)
- [[my-projects]] — 흩어진 브랜치별 실제 프로젝트 지도(인스타·당근·성경저널·쿠팡·홍보처크롤러). `#프로젝트 #색인 #사업`
- [[video-skills]] — 영상·유튜브 스킬 3종(watch·youtube-shorts·osmu) 색인. `#스킬 #영상 #유튜브`

### 유튜브 채널 운영 전략 🆕
- [[youtube-multi-account]] — ⭐연좌제 결합은 **애드센스 연결 시점**에 발생. 실험기엔 무료 계정 분리로 충분, 안티브라우저 불필요. `#유튜브 #다계정 #연좌제 #애드센스`
- [[reused-content]] — CC 라이선스≠재사용 면제. 실질 차별화 **6축 중 4축** 기준 + 원천별 위험 A~D등급. `#유튜브 #YPP #콘텐츠전략`
- [[account-security]] — 분리할수록 분실 위험↑. **앵커 계정 1개 + 순환 복구 금지**가 핵심. `#보안 #계정복구 #리스크관리`

### 워크플로 3단계
- [[data-dumping]] — (1단계/수집기) 분류 없이 무가공 투입 → 정리 시간 제로화. `#수집기 #1단계`
- [[self-evolving-wiki]] — (2단계/연결엔진) 연결고리 매핑 + 지식 지도 생성 → 40만 단어서도 초고속 검색. `#연결엔진 #검색 #2단계`
- [[dream-sequence]] — (3단계/정제기) ⭐유휴 시간 자가 정제: 모순·중복·구식 정리 + 통찰 축적. **가장 중요.** `#정제기 #핵심 #3단계`

## 🕸️ 연결 그래프 (주요 간선)
```
second-brain ──(상위 방법론)── claude-knowledge-system
     │                                  │
     ├─(1단계)─ data-dumping ◄──(Collector 구현)
     ├─(2단계)─ self-evolving-wiki ◄──(Connector 구현)
     └─(3단계)─ dream-sequence ◄──(Refiner 구현)

data-dumping ──(입력 공급)──► self-evolving-wiki ──(정제 대상)──► dream-sequence
                                       ▲                              │
                                       └────(피드백: 정제가 연결을 개선)─┘

zettelkasten ──(지적 선조/이론적 뿌리)──► second-brain, self-evolving-wiki, data-dumping
   └ "분류 말고 연결" · 링크 기반 창발 = 이 시스템 설계 철학의 원류

💡 zettelkasten.창발 ══(드림#1 통찰)══ dream-sequence
   └ 드림 시퀀스 = 체텔카스텐 창발을 자동화·가속한 엔진 (INSIGHTS.md 참고)

claude-code-skills ──(같은 원리)──► session-independence
   └ "로컬 PC ↔ 클라우드는 다른 컴퓨터, 커밋한 것만 영속" (brain/inbox 위치 혼선의 근원)

── [내 작업 자산 클러스터] ──
my-projects ──(콘텐츠 운영 도구)──► video-skills
   └ 인스타/유튜브 콘텐츠 프로젝트 ◄─ youtube-shorts·osmu 스킬이 뒷받침
my-projects ══(흩어짐의 해소)══ session-independence
   └ 17개 브랜치로 흩어진 작업을 brain 색인 하나로 = "하나의 뇌" 목표 실현

── [유튜브 채널 운영 클러스터] 🆕 ──
youtube-multi-account ══(결합 시점 원리)══ reused-content
   └ 수익화 전=계정구조로 방어 / 수익화 후=애드센스로 결합되어 콘텐츠 컴플라이언스로 방어 이동

youtube-multi-account ──(부작용 상쇄)──► account-security
   └ 계정 분리 ↑ → 연좌제 ↓ 이지만 분실 위험 ↑. 실험기 확률상 분실 >> 연좌제

reused-content ──(위험 등급 판정)──► video-skills
   └ youtube-shorts=C등급(높음) · osmu=B등급 → 등급이 계정 슬롯 배치를 결정

reused-content ══(미인식 자산 발견)══ my-projects
   └ 이커머스·자동화 1인칭 실전 경험 = A등급(재사용 위험 구조적 0). 가장 저평가된 채널 소재

account-security ──(같은 원리)──► session-independence
   └ "복구 경로를 미리 확보하지 않으면 자산이 사라진다" = "커밋한 것만 영속"
```

## ⚠️ 미해결 모순 / 확인필요
- [확인필요] [[data-dumping]] — "5분 내 스캔"은 데이터 규모에 따라 달라질 수 있는 예시 수치.
- [확인필요] 설계 긴장 — '자기 언어 재작성'을 AI가 대신하면 사람의 학습 이득이 줄 수 있음(드림#1, INSIGHTS.md). 완화책 검토 필요.
- [✅해결 2026-06-14] 기본 브랜치 main 전환 완료(default=main 확인). 새 세션이 통합 뇌를 로드함.
- [미해결] [[my-projects]] — 잉여 브랜치 5개(festive-wright·graphify-setup·upbeat-goodall·index-work·merge-brain-into-main)는 main에 완전 병합 → 삭제 가능. 프로젝트·설정 브랜치는 보존. 장기적으로 프로젝트별 독립 레포 분리 검토.
- [확인필요] [[youtube-multi-account]] — 개인사업자가 애드센스 별도 수취인으로 인정되는지(세무사 확인 필요). litt.ly 유료 가이드의 실제 지목 도구도 미확정.
- [모순] [[account-security]] — 앵커 계정 단일화는 복구 안전성↑ 이지만 **연결 신호 강화 + 단일 장애점**. 앵커 이중화 방안 검토 필요.
- [ ] [[reused-content]] — "6축 중 4축" 임계값은 운영 휴리스틱이며 유튜브 공식 기준 아님. 실제 심사 결과로 보정 필요.
- [ ] [[video-skills]] — youtube-shorts의 `실질변형 게이트(C1~C3)`가 6축 기준을 몇 축 충족하는지 대조 검증.

*(이 인덱스는 `/ingest`·`/dream` 실행 시마다 자동 갱신된다.)*

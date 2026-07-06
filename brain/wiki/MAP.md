# 🗺️ 지식 지도 (MAP) — 검색 인덱스

> 모든 검색(`/recall`)은 여기서 시작한다. 이 파일은 **작게** 유지한다(요약·링크만).
> 클로드는 이 인덱스로 위치를 좁힌 뒤 관련 주제 문서 1~3개만 펼쳐 몇 초 만에 답한다.

## 📊 통계
- 주제 문서: **11**
- 누적 통찰(insights): **4**
- 보관(archive): 0
- 마지막 수집(ingest): 2026-06-23 (당근-농수산물-판매법 → karrot-fresh-selling 신설)
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
- [[karrot-fresh-selling]] — 당근 농수산물 판매 7원칙(신선식품 보정)+2026 자동화 경계+CS방어. `/listing`·CS팩·Canva브리프·Supabase 스키마 산출. `#당근마켓 #농수산물 #자동화 #사업`

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

my-projects ──(당근 자동화 확장)──► karrot-fresh-selling
   └ 기존 '당근 상품등록 자동화'(북마클릿·마진추적기 3.3%)의 신선식품 버전.
     자동화 경계 = 입력준비(/listing·Canva) + 출력관리(Supabase) + 비즈 자동응답.
     ⚠️ 당근 외부 API 없음 → 직접 게시·채팅봇·시세수집 불가.
```

## ⚠️ 미해결 모순 / 확인필요
- [확인필요] [[data-dumping]] — "5분 내 스캔"은 데이터 규모에 따라 달라질 수 있는 예시 수치.
- [확인필요] 설계 긴장 — '자기 언어 재작성'을 AI가 대신하면 사람의 학습 이득이 줄 수 있음(드림#1, INSIGHTS.md). 완화책 검토 필요.
- [✅해결 2026-06-14] 기본 브랜치 main 전환 완료(default=main 확인). 새 세션이 통합 뇌를 로드함.
- [미해결] [[my-projects]] — 잉여 브랜치 5개(festive-wright·graphify-setup·upbeat-goodall·index-work·merge-brain-into-main)는 main에 완전 병합 → 삭제 가능. 프로젝트·설정 브랜치는 보존. 장기적으로 프로젝트별 독립 레포 분리 검토.

*(이 인덱스는 `/ingest`·`/dream` 실행 시마다 자동 갱신된다.)*

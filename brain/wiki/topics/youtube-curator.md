---
title: YouTube 큐레이터 — CC 떡상 발굴 → 숏츠 자동 편집
slug: youtube-curator
tags: [영상, 유튜브, 자동화, 큐레이션, 저작권, 숏츠]
created: 2026-06-20
updated: 2026-06-20
sources: ["https://min-inter.co.kr/youtube-curator-danbi/analytics/", 세션-2026-06-20]
related: [[video-editing-automation]], [[video-skills]], [[my-projects]]
confidence: high
status: active
---

## 한 줄 요약
danbi 분석 사이트의 *발굴*과 우리 `video-editor`의 *편집*을 합쳐, 카테고리별 CC 떡상 영상을 매일 자동으로 찾아 롱폼→숏츠로 만드는 무인 파이프라인(`youtube-curator/`). 저작권은 **CC 라이선스로 한정**해 채널 정지를 원천 차단.

## 핵심 내용
- 구조: 발굴(CC 필터·떡상점수) → ⚖️권리 게이트(CC 이중확인) → 다운로드 → 하이라이트 선택(LLM/휴리스틱) → 9:16 숏츠 편집(`--fit cover`·자막·무음컷) → 매니페스트 + CC 출처표기.
- **YouTube API 키 불필요**: `yt-dlp`의 `license` 필드로 CC 판별, 검색은 `sp=EgIwAQ==`(Creative Commons) 필터.
- **떡상 점수 = 조회수 / 업로드 후 경과일**(하루 평균 조회수). 신선도·길이 조건으로 트렌드만.
- 봇 벽: 데이터센터 IP(샌드박스·CI)는 YouTube 'bot 확인'에 막힘 → **`player_client=android`** 로 우회(쿠키 없이 상당수 통과), 100%는 `YT_COOKIES` secret.
- 자동화: `.github/workflows/curate.yml` 매일 06시 KST 크론 + 수동 실행, 결과 아티팩트. `categories.yaml`만 고치면 카테고리 확장(축구월드컵·쇼핑숏츠 기본).
- **자동 업로드는 의도적으로 제외** — 권리·오업로드 위험 방지, 사람이 검수 후 게시.
- 실증: CC 월드컵 영상 실제 발굴(552K뷰/11일=떡상 50,217/일), 9:16 크롭 편집 1080×1920 확인.

## 연결고리 (Connections)
- [[video-editing-automation]] — 그 5단계 골격의 1·3·4·5단계를 그대로 쓰고, '발굴(0단계)'을 앞에 붙인 것. 2단계 의미컷도 하이라이트 선택에 재사용.
- [[video-skills]] — 기존 youtube-shorts·osmu 스킬의 'CC·권리 게이트' 원칙을 코드로 구현.
- [[my-projects]] — 인스타·쿠팡 등 콘텐츠 운영 자산에 합류하는 실전 도구.

## 미해결/모순 (Open Questions)
- [✅구현 2026-06-20] 비한국어 CC 원본 → **한국어 자막 분위기 맞춤 자동 번역**(`--translate-ko`, LLM이 장르 파악 후 코믹/감동/스포츠 어휘로 번역). 월드컵 카테고리를 영어 CC+번역으로 전환.
- [✅구현 2026-06-20] `manifest.json`을 읽는 **정적 분석 대시보드**(`dashboard/index.html`) — 통계·카드·CC 배지·떡상점수. 크론 아티팩트에 동봉. 크론 시각 19:50 KST.
- [✅구현 2026-06-20] **채널 분석(랭킹+예측)** — `channels.py`: 구독자 스냅샷 누적 → 랭킹·일성장·7/30일 구독자 예측·최근영상 주간 조회수 예측. 추적 채널=수동(`channels.yaml`)+자동(디스커버리 CC 창작자→`auto_channels.json`). 대시보드 '📊 채널 분석' 탭. 호스팅=로컬/아티팩트(프로필 레포라 Pages 안 함).
- [확인필요] CI에서 봇 벽 안정성 — `YT_COOKIES` 없이 android 클라이언트만으로 충분한지 실측 필요.
- [미해결] 검수 후 반자동 업로드(YouTube OAuth), TOP 1200 대규모 랭킹(대형 시드+쿠키) — 다음 빌드.

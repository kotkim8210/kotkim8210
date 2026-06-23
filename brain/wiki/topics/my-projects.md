---
title: 진행 중인 프로젝트 색인 (브랜치별 산출물 지도)
slug: my-projects
tags: [프로젝트, 색인, 사업, 콘텐츠, 브랜치]
created: 2026-06-13
updated: 2026-06-13
sources: [2026-06-13-branch-inventory.md]
related: [[video-skills]], [[claude-code-skills]], [[session-independence]], [[nongsan-supply-prices]], [[delivery-trade-policy]]
confidence: high
status: active
---

## 한 줄 요약
여러 Claude 세션에서 각기 다른 GitHub 브랜치로 흩어져 진행된 실제 프로젝트들의 색인 — 어느 세션에서든 `/recall`로 "그 작업 어디까지 했지?"를 찾기 위한 지도.

## 핵심 내용 (브랜치 = 프로젝트)

| 프로젝트 | 브랜치 | 핵심 산출물 | 상태 |
|---|---|---|---|
| **인스타/쓰레드 콘텐츠 자동화** | `automate-infographic-reels-dwO7j` | @알쓸지잡10 트렌드 콘텐츠 JSON 60+, 번들 빌드 스크립트(Node) | 진행 |
| **홍보처 이메일 크롤러** | `friendly-goldberg-i3mwo8` | 요양/한방병원 이메일 크롤러(검수 41건), 네이버 밴드·B2B 공급처 엑셀 | 진행 |
| **당근스토어 상품등록 자동화** | `gallant-keller-Vlmnq` | 폼 자동채움 북마클릿(7종), 마진 추적기, 당근 수수료 3.3% | 진행 |
| **성경저널 POD** | `tender-wright-hf5pq1` | 등산저널→성경저널 피벗, 랜딩 7종 HTML, '엄마의 기도 노트' 디자인, GA4 | 진행 |
| **Next.js 쿠팡파트너스 MVP** | `lean-dev-workflow-i6yeq`, `setup-claude-code-plugin-LIuOs` | Next.js 15 랜딩+A/B, 쿠팡파트너스 수익 페이지 | 진행 |

(상세: 2026-06-13-branch-inventory.md)

## 부가: 인프라/설정 브랜치
- `optimize-token-settings-4r97O` — settings.json 토큰 절약 최적화
- `resolve-namespace-conflicts-fmvMO` — everything-claude-code/gstack 네임스페이스 충돌 해소
- `validate-settings-workflow-GOUhT` — CLAUDE.md 워크플로 템플릿 + validate-settings.sh

## 브랜치 정리 상태 (2026-06-14 드림#2 감사)
- 🗑️ **삭제 가능**(잉여, main에 완전 병합 → 지식 손실 0): `festive-wright`, `graphify-setup`(옛 기본), `upbeat-goodall`, `index-work`, `merge-brain-into-main`
- 🔒 **보존**(고유 작업물 보유): 위 프로젝트 5개 + 인프라 3개 + `zealous-galileo`(karpathy 스킬 `d5b6709`). 삭제 전 해당 작업을 main에 병합하거나 독립 레포로 이전 필요.

## 연결고리 (Connections)
- [[video-skills]] — youtube-shorts·osmu 스킬이 콘텐츠 프로젝트(인스타·유튜브) 운영을 뒷받침.
- [[session-independence]] — 이 색인 자체가 "세션이 흩어져도 하나의 뇌에서 전체를 본다"는 원칙의 실현.
- [[claude-code-skills]] — 프로젝트마다 `.claude/` 설정이 달라 스킬 스코프 규칙의 영향을 받음.
- [[nongsan-supply-prices]] — 당근스토어·쿠팡 등 재판매 프로젝트의 실제 매입 단가(농산물 공급가표).
- [[delivery-trade-policy]] — 재판매/드롭배송 운영 전제(공급가에 택배비 포함, 산지직출고, 택배거래 99%).

## 미해결/모순 (Open Questions)
- [ ] 각 프로젝트를 독립 레포로 분리할지, 이 레포 서브폴더로 유지할지 결정.
- [ ] 프로젝트별 최신 진행상황은 해당 브랜치 세션에서 갱신 필요(이 색인은 2026-06-13 스냅샷).

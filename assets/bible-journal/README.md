# 엄마의 기도 노트 — 디자인 v1 (인쇄용)

선택 방향: **프리미엄 미니멀(C) + 올리브 1도 인쇄** — 고급감과 최저 원가 양립.

## 양산 사양
- 표지: 크림 무광 라미네이트 + 인쇄 골드/올리브 (포일 ❌)
- 내지: 크림지 + 올리브 1도 인쇄 (풀컬러 ❌)
- 제본: 와이어-O(스프링) 또는 무선 소프트커버
- 판형: A5 (148×210mm), 분량 100~120p 권장

## 파일
- `01_cover.png` ~ `05_log.png` : 페이지 시안 (A5 300DPI)
- `mom-prayer-journal_interior.pdf` : 인쇄 입고용 A5 PDF
- `generate.js` : 재생성 스크립트 (@napi-rs/canvas + pdfkit; 나눔명조 TTF 필요)

재생성: `npm i @napi-rs/canvas pdfkit` 후 나눔명조(Regular/Bold/ExtraBold) TTF를 같은 폴더에 두고 `node generate.js`.

## v1.1 — 완제품 (110p)
- `mom-prayer-journal_full-110p.pdf` : **입고용 완제품** (A5 300DPI)
  - 표지·속표지·사용법·헌사·자녀 인덱스 / 데일리 ×92 / 기도응답표 ×7 / 성경 통독표(구약·신약) / 연말 회고
- `generate_full.js` : 완제품 재생성 스크립트
- `06~10_*.png` : 신규 페이지 미리보기

## v1.2 — 상세페이지 (스마트스토어)
- `detail_full.png` : 상세페이지 전체 (1080px wide, 세로 롱) — 후킹→공감→해결→기능3→종이의이유→사양→선물→한정CTA
- `detail_hero.png` : 첫 화면(후킹) 단독
- `generate_detail.js` : 재생성 스크립트

## v1.3 — 대표 썸네일 (목록 노출용)
- `thumb_1_main.png` : **대표이미지**(검색 목록) — 깔끔 제품 hero
- `thumb_2_hook.png` : 후킹(올리브 밴드, 그리드에서 시선 강탈)
- `thumb_3_feature.png` : 기능(기록)
- `thumb_4_inside.png` : 구성(110p 한눈에)
- `thumb_5_gift.png` : 선물 앵글
- `generate_thumbs.js` : 재생성 스크립트 (1:1 1000×1000)

### v1.3.1 — 썸네일 시인성 개선
- 후킹(#2) 배경 카키 올리브 → **딥그린(#2E3A32)** 고급화
- 보조 텍스트 전부 Bold/ExtraBold + 진한 색으로 가독성 강화, 선물 라벨 알약형

### v1.3.2 — 썸네일 가독성 전면 개선
- 이미지 내부 인쇄 글자에 의존 X → 핵심 문구를 썸네일 위에 큰 글씨로 직접 노출
  (T2 브랜드명, T3 칸 이름 리스트, T4 페이지별 큰 캡션)
- T2 소형 표지 제거, T5 표지 축소 → 프레임/바닥 넘침 수정

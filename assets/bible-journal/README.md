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

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

## v1.4 — 표지 확대 · 상세 딥그린 통일 · 업로드 조각 · 브랜드/가격
- 표지 부제/구절 확대(재제작) → 상세·썸네일에 반영
- 상세페이지 어두운 밴드 올리브→**딥그린(#2E3A32)** 통일(썸네일과 톤 일치)
- `detail_part_1~6.png` : 스마트스토어 업로드용 조각(섹션 경계 컷 → 글자 안 잘림)
- `brand-and-pricing.md` : 브랜드명 5후보 + 가격·옵션·SEO 상품명

## v1.5 — 브랜드 확정: 씨앗과 기도
- 브랜드 = **씨앗과 기도**, 제품 = 엄마의 기도 노트
- 로고(새싹 심볼 = 씨앗→발아, 이름과 의미 일치):
  - `logo_primary.png` 가로형 / `logo_stacked.png` 세로형
  - `logo_profile_cream.png` · `logo_profile_green.png` 프로필(인스타/쓰레드)
- `generate_logo.js` 재생성 스크립트
- TODO: 표지 하단·썸네일 코너에 워드마크 스탬프(브랜드 통일) — 승인 시 진행

## v1.6 — 브랜드 마크 통일 (씨앗과 기도)
- 표지 하단(발행처) · 상세 마지막 밴드 · 썸네일 5종 하단에 '씨앗과 기도' 마크
- 모든 PNG/PDF/조각 재생성하여 브랜드 통일 적용

## v1.7 — 1단계 POD용 흑백 본문
- `mom-prayer-journal_interior-BW-110p.pdf` : **본문(표지 제외) 110쪽, 흰 배경 + 검정 잉크**
  - 디지털 POD '흑백' 단가 적용용. 종이는 미색(크림)모조 선택 권장.
  - 표지는 별도 컬러 파일(`01_cover.png`)로 업로드.
- `generate_bw.js` 재생성 스크립트
- 주의: 인쇄 파일은 배경을 크림으로 채우지 않음(크림은 종이색). 화면용 PNG와 구분.

## v1.8 — 인쇄용 컬러 표지 (와이어제본)
- `cover_front_print.png` / `cover_back_print.png` : 앞/뒤 표지, A5 + **도련 3mm**(1818×2550px, 300dpi)
- `cover_front_guides.png` : 재단선(빨강)·안전선(파랑) 확인용 (업로드 X)
- 와이어제본이라 책등 없음(앞/뒤 분리). RGB PNG — 디지털 POD는 대부분 그대로 수용(필요시 PDF/CMYK 변환 가능)
- 최종 POD 세트: 흑백 본문 110p + 컬러 앞/뒤 표지 + 와이어 + 미색지

## v1.9 — 전체 검수(2026-07-19) + 표지 타공 안전여백
- **전수 검수 완료**: 썸네일 5종·상세 6조각·내지 미리보기·로고 4종·PDF 3종(페이지 수·A5 규격) 이상 없음. 성경 표기(데살로니가전서 5:17, 엡 6:4, 통독표 66권) 정확.
- **수정: 표지 프레임 타공 침범** — 기존 프레임이 재단선 기준 약 6mm 안쪽에 있어 와이어 타공 존(제본쪽 10mm)과 겹칠 위험 → **12mm로 이동**(`SAFE 105→177`), 앞표지 발행처(씨앗과 기도) 위치 보정. 가이드에 주황 타공 존(10mm) 표시 추가.
- 알려진 미세 불일치(무해): 상세·썸네일 카피 "기도 92편" vs 흑백 입고본 데일리 93장(1장 초과 제공). 수정 불요.
- **재생성 환경**: `/tmp/journal`에 나눔명조 TTF 3종 + `npm i @napi-rs/canvas pdfkit` 후 `NODE_PATH=<node_modules> node generate_*.js`.
  폰트 출처: `raw.githubusercontent.com/google/fonts/main/ofl/nanummyeongjo/NanumMyeongjo-{Regular,Bold,ExtraBold}.ttf` (Regular은 `NanumMyeongjo.ttf`로 복사).

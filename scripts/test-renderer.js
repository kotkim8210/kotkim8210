// Mock test — exercises render-images.js with a fixture JSON (no Claude call).
// Run: node scripts/test-renderer.js
import { renderImages } from "../src/render-images.js";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "output");

const fixtures = [
  {
    topic_id: "_test_ranking",
    category: "취업/연봉",
    card_type: "ranking",
    slides: [
      {
        slide_number: 1, type: "cover", tag: "#취준생필독 💼",
        headline_line1: "2026 대기업", headline_line2: "신입 초봉 TOP",
        subheadline: "블라인드 현직자 제보 기반 / 30초 컷",
      },
      {
        slide_number: 2, type: "ranking",
        section_title: "대기업 신입 초봉 TOP 7 (세전)",
        items: [
          { rank: 1, name: "SK하이닉스", detail: "성과급 1500%", value: "5,800만", badge: "🥇" },
          { rank: 2, name: "삼성전자 DS", detail: "메모리·파운드리", value: "5,500만", badge: "🥈" },
          { rank: 3, name: "네이버", detail: "스톡 별도 지급", value: "5,200만", badge: "🥉" },
          { rank: 4, name: "카카오", detail: "복지 포인트 600만", value: "5,000만" },
          { rank: 5, name: "현대차", detail: "특근수당 별도", value: "4,800만" },
          { rank: 6, name: "LG에너지솔루션", detail: "기숙사 제공", value: "4,700만" },
          { rank: 7, name: "포스코", detail: "지역 근무 가산", value: "4,500만" },
        ],
        footnote: "[2025 블라인드 기준] 성과급 제외 추정치 · 부서별 차이 있음",
      },
      { slide_number: 3, type: "cta" },
    ],
  },
  {
    topic_id: "_test_checklist",
    category: "재테크/돈",
    card_type: "checklist",
    slides: [
      {
        slide_number: 1, type: "cover", tag: "#돈되는정보 💰",
        headline_line1: "20대 모르면", headline_line2: "손해보는 지원금",
        subheadline: "정부24·복지로 통합 / 신청만 하면 받는 돈",
      },
      {
        slide_number: 2, type: "checklist",
        section_title: "20대 필수 정부지원금 6가지",
        items: [
          { icon: "🏠", name: "청년 월세 한시 특별지원", detail: "월 최대 20만원 12개월", badge: "신청 4월~" },
          { icon: "💼", name: "국민취업지원제도", detail: "월 50만 × 6개월 + 취업알선" },
          { icon: "📚", name: "내일배움카드", detail: "1인당 300~500만원 직업훈련비" },
          { icon: "🎓", name: "청년 도약계좌", detail: "5년 5천만원 목돈 마련", badge: "소득요건 ⚠" },
          { icon: "🏦", name: "청년희망적금 만기 연장", detail: "비과세 혜택 연장 가능" },
          { icon: "🚇", name: "K-패스 교통비 환급", detail: "월 21회 이상 이용시 20~53% 환급" },
        ],
        footnote: "2026년 3월 기준 · 연도별 정책 변동 가능 · 자세한 조건은 정부24 확인",
      },
      { slide_number: 3, type: "cta" },
    ],
  },
  {
    topic_id: "_test_comparison",
    category: "취업/연봉",
    card_type: "comparison",
    slides: [
      {
        slide_number: 1, type: "cover", tag: "#취준생필독 💼",
        headline_line1: "네이버 vs 카카오", headline_line2: "신입 복지 비교",
        subheadline: "현직자 제보 기반 · 어디가 더 좋을까?",
      },
      {
        slide_number: 2, type: "comparison",
        section_title: "네이버 vs 카카오 신입 복지 5종 비교",
        headers: ["항목", "네이버", "카카오"],
        rows: [
          ["기본 초봉", "5,200만", "5,000만"],
          ["스톡옵션", "별도 지급", "RSU 4년"],
          ["복지 포인트", "150만/년", "600만/년"],
          ["식대", "전액 지원", "전액 지원"],
          ["재택근무", "주 3일", "주 2일"],
          ["사내 어린이집", "○ (분당)", "○ (판교)"],
        ],
        footnote: "[2025 블라인드/잡플래닛 종합] 부서·직군별 차이 있음 · 변동 가능",
      },
      { slide_number: 3, type: "cta" },
    ],
  },
];

for (const fx of fixtures) {
  console.log(`\n=== rendering ${fx.topic_id} (${fx.card_type}) ===`);
  const out = await renderImages(fx, OUT);
  console.log("done:", out.length, "images");
}

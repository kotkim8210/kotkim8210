import "dotenv/config";
import { writeFile, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { generateContent } from "./generate-content.js";
import { renderImages } from "./render-images.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUTPUT_DIR = join(__dirname, "..", "output");

function usage() {
  console.error('Usage: node src/pipeline.js "<주제>"');
  console.error('Example: node src/pipeline.js "2026 대기업 신입 초봉 티어"');
}

async function main() {
  const topic = process.argv[2];
  if (!topic) {
    usage();
    process.exit(1);
  }

  if (!process.env.ANTHROPIC_API_KEY) {
    console.error("[pipeline] ANTHROPIC_API_KEY 가 .env 파일에 설정되어 있어야 합니다.");
    console.error("           cp .env.example .env 후 키를 입력하세요.");
    process.exit(1);
  }

  await mkdir(OUTPUT_DIR, { recursive: true });

  console.log(`[pipeline] 주제: ${topic}`);
  console.log("[pipeline] 1/2 콘텐츠 생성 중 (Claude API + web_search)...");
  const content = await generateContent(topic);

  if (!content.topic_id || !Array.isArray(content.slides)) {
    throw new Error("생성된 JSON에 topic_id 또는 slides 필드가 없습니다.");
  }

  const jsonPath = join(OUTPUT_DIR, `${content.topic_id}.json`);
  await writeFile(jsonPath, JSON.stringify(content, null, 2), "utf-8");
  console.log(`[pipeline] JSON 저장: ${jsonPath}`);
  console.log(`[pipeline]   topic_id=${content.topic_id} card_type=${content.card_type} slides=${content.slides.length}`);

  console.log("[pipeline] 2/2 이미지 렌더링 중 (Puppeteer)...");
  const images = await renderImages(content, OUTPUT_DIR);

  console.log("\n[pipeline] 완료!");
  console.log(`  JSON:   ${jsonPath}`);
  console.log(`  이미지: ${images.length}장`);
  for (const p of images) console.log(`    - ${p}`);
}

main().catch((err) => {
  console.error("\n[pipeline] 실패:", err.message);
  if (err.stack) console.error(err.stack);
  process.exit(1);
});

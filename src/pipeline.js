import "dotenv/config";
import { writeFile, readFile, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

import { generateContent } from "./generate-content.js";
import { renderImages } from "./render-images.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUTPUT_DIR = join(__dirname, "..", "output");

function parseArgs(argv) {
  const opts = { topic: null, fromJson: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--from-json") opts.fromJson = argv[++i];
    else if (a.startsWith("--")) throw new Error(`Unknown flag: ${a}`);
    else if (!opts.topic) opts.topic = a;
    else throw new Error(`Unexpected positional arg: ${a}`);
  }
  return opts;
}

function usage() {
  console.error(`Usage:
  node src/pipeline.js "<주제>"                          Claude로 생성 → 렌더링
  node src/pipeline.js --from-json <path/to.json>        기존 JSON으로 바로 렌더링 (API 키 불필요)

Examples:
  node src/pipeline.js "2026 대기업 신입 초봉 티어"
  node src/pipeline.js --from-json data/contents/01_big_corp_salary.json`);
}

async function main() {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (err) {
    console.error(`[pipeline] ${err.message}\n`);
    usage();
    process.exit(2);
  }

  if (!opts.topic && !opts.fromJson) {
    usage();
    process.exit(1);
  }

  await mkdir(OUTPUT_DIR, { recursive: true });

  let content;
  let jsonPath;

  if (opts.fromJson) {
    const abs = resolve(opts.fromJson);
    console.log(`[pipeline] --from-json ${abs}`);
    const raw = await readFile(abs, "utf-8");
    content = JSON.parse(raw);
    if (!content.topic_id || !Array.isArray(content.slides)) {
      throw new Error("JSON 파일에 topic_id 또는 slides 필드가 없습니다.");
    }
    jsonPath = join(OUTPUT_DIR, `${content.topic_id}.json`);
    await writeFile(jsonPath, JSON.stringify(content, null, 2), "utf-8");
    console.log(`[pipeline] JSON 복사: ${jsonPath}`);
  } else {
    if (!process.env.ANTHROPIC_API_KEY) {
      console.error("[pipeline] ANTHROPIC_API_KEY 가 .env 파일에 설정되어 있어야 합니다.");
      console.error("           cp .env.example .env 후 키를 입력하세요.");
      console.error("           (또는 --from-json <path> 로 사전 생성 JSON 사용)");
      process.exit(1);
    }

    console.log(`[pipeline] 주제: ${opts.topic}`);
    console.log("[pipeline] 1/2 콘텐츠 생성 중 (Claude API + web_search)...");
    content = await generateContent(opts.topic);

    if (!content.topic_id || !Array.isArray(content.slides)) {
      throw new Error("생성된 JSON에 topic_id 또는 slides 필드가 없습니다.");
    }

    jsonPath = join(OUTPUT_DIR, `${content.topic_id}.json`);
    await writeFile(jsonPath, JSON.stringify(content, null, 2), "utf-8");
    console.log(`[pipeline] JSON 저장: ${jsonPath}`);
  }

  console.log(`[pipeline]   topic_id=${content.topic_id} card_type=${content.card_type} slides=${content.slides.length}`);

  console.log(`[pipeline] ${opts.fromJson ? "1/1" : "2/2"} 이미지 렌더링 중 (Puppeteer)...`);
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

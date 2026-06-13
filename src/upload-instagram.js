import "dotenv/config";
import { readFile, writeFile, readdir, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, basename } from "node:path";

import { uploadImage } from "./image-host.js";
import { InstagramClient, uploadCarousel } from "./instagram.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const OUTPUT_DIR = join(ROOT, "output");
const STATE_PATH = join(OUTPUT_DIR, "upload-state.json");

const IG_CAPTION_LIMIT = 2200;
const IG_HASHTAG_LIMIT = 30;
// State files we should never treat as content JSON
const STATE_FILES = new Set(["upload-state.json", "batch-state.json"]);

function parseArgs(argv) {
  const opts = { topicIds: [], all: false, dryRun: false, limit: Infinity };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--all") opts.all = true;
    else if (a === "--dry-run") opts.dryRun = true;
    else if (a === "--limit") opts.limit = Number(argv[++i]);
    else if (a.startsWith("--")) throw new Error(`Unknown flag: ${a}`);
    else opts.topicIds.push(a);
  }
  return opts;
}

function usage() {
  console.error(`Usage:
  node src/upload-instagram.js <topic_id> [...]      특정 topic_id 업로드
  node src/upload-instagram.js --all [--limit N]     output/의 모든 미업로드 토픽
  node src/upload-instagram.js <id> --dry-run        imgbb까지만, IG publish 안 함

Required env: ANTHROPIC_API_KEY (없어도 됨), IMGBB_API_KEY, IG_ACCESS_TOKEN, IG_USER_ID`);
}

async function loadState() {
  if (!existsSync(STATE_PATH)) return {};
  try {
    return JSON.parse(await readFile(STATE_PATH, "utf-8"));
  } catch (err) {
    console.warn(`[upload] state corrupt, starting fresh: ${err.message}`);
    return {};
  }
}

async function saveState(state) {
  await writeFile(STATE_PATH, JSON.stringify(state, null, 2), "utf-8");
}

/** Discover topics in OUTPUT_DIR by scanning {topic_id}.json files. */
async function discoverTopics() {
  const entries = await readdir(OUTPUT_DIR);
  const topics = [];
  for (const name of entries) {
    if (!name.endsWith(".json")) continue;
    if (STATE_FILES.has(name)) continue;
    const topic_id = name.slice(0, -5);
    topics.push(topic_id);
  }
  return topics;
}

/** Find image files for a topic (cover, body, cta). Returns paths in slide order. */
async function findImagesForTopic(topic_id) {
  const entries = await readdir(OUTPUT_DIR);
  const prefix = `${topic_id}_`;
  const matched = entries
    .filter((n) => n.startsWith(prefix) && n.endsWith(".jpg"))
    .sort(); // names contain zero-padded slide numbers, so lex sort = slide order
  return matched.map((n) => join(OUTPUT_DIR, n));
}

function formatCaption(caption) {
  if (!caption || typeof caption !== "object") return "";
  const parts = [];
  if (caption.title) parts.push(caption.title);
  if (caption.body) parts.push(caption.body);
  if (caption.cta) parts.push(caption.cta);
  if (caption.source) parts.push(caption.source);
  if (caption.hashtags) parts.push(caption.hashtags);
  let text = parts.filter(Boolean).join("\n\n");

  // Hashtag count check
  const hashtagCount = (text.match(/#\S+/g) ?? []).length;
  if (hashtagCount > IG_HASHTAG_LIMIT) {
    console.warn(`  [caption] 해시태그 ${hashtagCount}개 → ${IG_HASHTAG_LIMIT}개 한도 초과 (그대로 보냄, IG가 잘라냄)`);
  }

  // Length check
  if (text.length > IG_CAPTION_LIMIT) {
    console.warn(`  [caption] ${text.length}자 → ${IG_CAPTION_LIMIT}자로 truncate`);
    text = text.slice(0, IG_CAPTION_LIMIT - 3) + "...";
  }
  return text;
}

async function loadTopicContent(topic_id) {
  const jsonPath = join(OUTPUT_DIR, `${topic_id}.json`);
  if (!existsSync(jsonPath)) {
    throw new Error(`${jsonPath} 없음 — 먼저 생성하세요 (npm run pipeline 또는 npm run batch)`);
  }
  const content = JSON.parse(await readFile(jsonPath, "utf-8"));

  const images = await findImagesForTopic(topic_id);
  if (images.length < 2) {
    throw new Error(`이미지가 ${images.length}개 — 최소 2장 필요 (cover + 본문 + cta = 3장 권장)`);
  }

  return { content, images };
}

async function processTopic(topic_id, igClient, state, { dryRun }) {
  const entry = state[topic_id] ?? { topic_id, status: "pending" };
  state[topic_id] = entry;
  entry.attempts = (entry.attempts ?? 0) + 1;
  entry.last_attempt_at = new Date().toISOString();

  try {
    const { content, images } = await loadTopicContent(topic_id);
    const caption = formatCaption(content.caption);

    console.log(`  [imgbb] uploading ${images.length} image(s)...`);
    const imageUrls = [];
    for (const p of images) {
      const url = await uploadImage(p);
      console.log(`    ${basename(p)} → ${url}`);
      imageUrls.push(url);
    }
    entry.image_urls = imageUrls;
    await saveState(state);

    if (dryRun) {
      entry.status = "dry_run";
      delete entry.error;
      await saveState(state);
      console.log("  [dry-run] skipping IG publish");
      return { ok: true, dryRun: true };
    }

    const result = await uploadCarousel(igClient, imageUrls, caption);
    entry.status = "uploaded";
    entry.media_id = result.mediaId;
    entry.permalink = result.permalink;
    entry.uploaded_at = new Date().toISOString();
    delete entry.error;
    await saveState(state);

    return { ok: true, result };
  } catch (err) {
    entry.status = "error";
    entry.error = err.message;
    await saveState(state);
    return { ok: false, error: err };
  }
}

async function main() {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (err) {
    console.error(`[upload] ${err.message}\n`);
    usage();
    process.exit(2);
  }

  if (!opts.all && opts.topicIds.length === 0) {
    usage();
    process.exit(1);
  }

  // Validate envs we need (skip IG check on dry-run since publish doesn't happen)
  if (!process.env.IMGBB_API_KEY) {
    console.error("[upload] IMGBB_API_KEY 환경변수 필요 (https://api.imgbb.com/).");
    process.exit(1);
  }
  if (!opts.dryRun) {
    if (!process.env.IG_ACCESS_TOKEN || !process.env.IG_USER_ID) {
      console.error("[upload] IG_ACCESS_TOKEN, IG_USER_ID 환경변수 필요. --dry-run 으로 imgbb까지만 테스트 가능.");
      process.exit(1);
    }
  }

  await mkdir(OUTPUT_DIR, { recursive: true });
  const state = await loadState();

  let topics;
  if (opts.all) {
    topics = await discoverTopics();
    if (topics.length === 0) {
      console.error("[upload] output/ 에 콘텐츠 JSON이 없습니다. 먼저 npm run batch 실행.");
      process.exit(1);
    }
  } else {
    topics = opts.topicIds;
  }

  const igClient = opts.dryRun ? null : new InstagramClient();

  // Token sanity check (cheap, fails fast on expired token)
  // Disable with IG_SKIP_PREFLIGHT=true (useful in offline/CI tests)
  if (!opts.dryRun && process.env.IG_SKIP_PREFLIGHT !== "true") {
    try {
      const acct = await igClient.getAccountInfo();
      console.log(`[upload] authenticated as @${acct.username ?? acct.name ?? acct.id}`);
    } catch (err) {
      console.error(`[upload] IG 인증 실패: ${err.message}`);
      console.error("        토큰이 만료됐을 수 있습니다 → npm run refresh-token");
      process.exit(1);
    }
  }

  let cancelled = false;
  process.once("SIGINT", () => {
    if (cancelled) return;
    cancelled = true;
    console.log("\n[upload] 신호 받음 — 현재 토픽 마무리하고 종료합니다.");
  });
  process.once("SIGTERM", () => { cancelled = true; });

  const stats = { processed: 0, ok: 0, skipped: 0, failed: 0 };

  for (let i = 0; i < topics.length; i++) {
    if (cancelled) break;
    if (stats.processed >= opts.limit) {
      console.log(`\n[upload] limit ${opts.limit} 도달`);
      break;
    }

    const topic_id = topics[i];
    const prev = state[topic_id];
    console.log(`\n[${i + 1}/${topics.length}] ${topic_id}`);

    if (prev?.status === "uploaded" && !opts.dryRun) {
      console.log(`  ✓ 이미 uploaded (media_id=${prev.media_id}) — 스킵`);
      stats.skipped++;
      continue;
    }

    stats.processed++;
    const result = await processTopic(topic_id, igClient, state, { dryRun: opts.dryRun });
    if (result.ok) {
      if (result.dryRun) {
        console.log("  ✓ dry-run done");
      } else {
        console.log(`  ✓ published: ${result.result.permalink ?? `media_id=${result.result.mediaId}`}`);
      }
      stats.ok++;
    } else {
      console.log(`  ✗ failed: ${result.error.message}`);
      stats.failed++;
    }
  }

  console.log("\n=== upload summary ===");
  console.log(`  total topics: ${topics.length}`);
  console.log(`  processed:    ${stats.processed}`);
  console.log(`  ok:           ${stats.ok}`);
  console.log(`  skipped:      ${stats.skipped}`);
  console.log(`  failed:       ${stats.failed}`);
  if (stats.failed > 0) process.exit(1);
}

main().catch((err) => {
  console.error("\n[upload] fatal:", err.message);
  if (err.stack) console.error(err.stack);
  process.exit(1);
});

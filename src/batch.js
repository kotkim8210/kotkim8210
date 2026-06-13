import "dotenv/config";
import { readFile, writeFile, mkdir, readdir, stat } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve, basename } from "node:path";

import { generateContent } from "./generate-content.js";
import { renderImages, launchRenderer } from "./render-images.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const OUTPUT_DIR = join(ROOT, "output");
const DEFAULT_INPUT = join(ROOT, "data", "topics.json");
const STATE_PATH = join(OUTPUT_DIR, "batch-state.json");

function parseArgs(argv) {
  const opts = { input: null, fromDir: null, retryErrors: false, limit: Infinity };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--retry-errors") opts.retryErrors = true;
    else if (a === "--limit") opts.limit = Number(argv[++i]);
    else if (a === "--from-dir") opts.fromDir = argv[++i];
    else if (a.startsWith("--")) throw new Error(`Unknown flag: ${a}`);
    else if (!opts.input) opts.input = a;
    else throw new Error(`Unexpected argument: ${a}`);
  }
  if (!opts.fromDir && !opts.input) opts.input = DEFAULT_INPUT;
  return opts;
}

function usage() {
  console.error(`Usage:
  node src/batch.js [topics.json] [--retry-errors] [--limit N]
      data/topics.json 의 주제로 Claude 호출 → 렌더링 → 상태 추적

  node src/batch.js --from-dir <dir> [--retry-errors] [--limit N]
      디렉터리 내 모든 *.json 을 사전 생성 콘텐츠로 취급 → 렌더링만 (Claude 호출 안 함)

Examples:
  npm run batch                                       # 기본
  node src/batch.js --from-dir data/contents          # 30개 사전 생성 콘텐츠 전체 렌더링
  node src/batch.js --from-dir data/contents --limit 5
  node src/batch.js --retry-errors                    # error_* 항목 재시도`);
}

async function loadState() {
  if (!existsSync(STATE_PATH)) return {};
  try {
    return JSON.parse(await readFile(STATE_PATH, "utf-8"));
  } catch (err) {
    console.warn(`[batch] state file corrupt, starting fresh: ${err.message}`);
    return {};
  }
}

async function saveState(state) {
  await writeFile(STATE_PATH, JSON.stringify(state, null, 2), "utf-8");
}

async function loadTopics(inputPath) {
  const abs = resolve(inputPath);
  const raw = await readFile(abs, "utf-8");
  const parsed = JSON.parse(raw);
  if (!Array.isArray(parsed)) {
    throw new Error(`${abs}: must be a JSON array of topic strings`);
  }
  const topics = parsed.map((t, i) => {
    if (typeof t !== "string" || t.trim().length === 0) {
      throw new Error(`${abs}[${i}]: every entry must be a non-empty string`);
    }
    return t.trim();
  });
  // Dedupe preserving first occurrence
  const seen = new Set();
  return topics.filter((t) => (seen.has(t) ? false : seen.add(t)));
}

/**
 * Load and validate pre-generated content JSON files from a directory.
 * Returns array of {key, path, content} where key = topic_id.
 */
async function loadContentDir(dirPath) {
  const abs = resolve(dirPath);
  const s = await stat(abs).catch(() => null);
  if (!s?.isDirectory()) throw new Error(`${abs}: not a directory`);
  const entries = await readdir(abs);
  const files = entries.filter((n) => n.endsWith(".json")).sort();
  if (files.length === 0) throw new Error(`${abs}: no *.json files found`);

  const items = [];
  for (const name of files) {
    const fp = join(abs, name);
    let content;
    try {
      content = JSON.parse(await readFile(fp, "utf-8"));
    } catch (err) {
      throw new Error(`${fp}: invalid JSON — ${err.message}`);
    }
    if (!content.topic_id || !Array.isArray(content.slides)) {
      throw new Error(`${fp}: missing topic_id or slides`);
    }
    items.push({ key: content.topic_id, path: fp, content });
  }
  return items;
}

function shouldSkip(entry, retryErrors) {
  if (!entry) return false;
  if (entry.status === "done") return true;
  if (!retryErrors && entry.status?.startsWith("error_")) return true;
  return false;
}

async function processTopic(topic, state, browser) {
  const entry = state[topic] ?? { topic, status: "pending" };
  state[topic] = entry;
  entry.attempts = (entry.attempts ?? 0) + 1;
  entry.last_attempt_at = new Date().toISOString();

  // Stage 1: JSON generation
  const needsJson =
    entry.status === "pending" ||
    entry.status === "error_json" ||
    !entry.json_path ||
    !existsSync(entry.json_path);

  if (needsJson) {
    try {
      console.log("  [1/2] generating JSON via Claude...");
      const content = await generateContent(topic);
      if (!content.topic_id || !Array.isArray(content.slides)) {
        throw new Error("generated JSON missing topic_id or slides");
      }
      entry.topic_id = content.topic_id;
      entry.category = content.category;
      entry.card_type = content.card_type;
      const jsonPath = join(OUTPUT_DIR, `${content.topic_id}.json`);
      await writeFile(jsonPath, JSON.stringify(content, null, 2), "utf-8");
      entry.json_path = jsonPath;
      entry.status = "json_done";
      delete entry.error;
      await saveState(state);
    } catch (err) {
      entry.status = "error_json";
      entry.error = err.message;
      await saveState(state);
      return { ok: false, stage: "json", error: err };
    }
  }

  // Stage 2: image rendering
  try {
    console.log("  [2/2] rendering images via Puppeteer...");
    const content = JSON.parse(await readFile(entry.json_path, "utf-8"));
    const images = await renderImages(content, OUTPUT_DIR, { browser });
    entry.images = images;
    entry.status = "done";
    delete entry.error;
    await saveState(state);
    return { ok: true };
  } catch (err) {
    entry.status = "error_image";
    entry.error = err.message;
    await saveState(state);
    return { ok: false, stage: "image", error: err };
  }
}

/** Render-only processor for pre-generated content (no Claude call). */
async function processContentItem(item, state, browser) {
  const key = item.key;
  const entry = state[key] ?? { topic_id: key, status: "pending", source: "from-dir" };
  state[key] = entry;
  entry.attempts = (entry.attempts ?? 0) + 1;
  entry.last_attempt_at = new Date().toISOString();
  entry.topic_id = item.content.topic_id;
  entry.category = item.content.category;
  entry.card_type = item.content.card_type;
  entry.source_json = item.path;

  // Always (re)write the content into output/ so downstream tools (upload-instagram) find it
  const outJsonPath = join(OUTPUT_DIR, `${item.content.topic_id}.json`);
  await writeFile(outJsonPath, JSON.stringify(item.content, null, 2), "utf-8");
  entry.json_path = outJsonPath;

  try {
    console.log("  [render-only] rendering images via Puppeteer...");
    const images = await renderImages(item.content, OUTPUT_DIR, { browser });
    entry.images = images;
    entry.status = "done";
    delete entry.error;
    await saveState(state);
    return { ok: true };
  } catch (err) {
    entry.status = "error_image";
    entry.error = err.message;
    await saveState(state);
    return { ok: false, stage: "image", error: err };
  }
}

async function main() {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (err) {
    console.error(`[batch] ${err.message}\n`);
    usage();
    process.exit(2);
  }

  // ANTHROPIC_API_KEY only required when generating (not in --from-dir mode)
  if (!opts.fromDir && !process.env.ANTHROPIC_API_KEY) {
    console.error("[batch] ANTHROPIC_API_KEY 가 .env 파일에 설정되어 있어야 합니다.");
    console.error("        (또는 --from-dir <dir> 로 사전 생성 JSON 사용)");
    process.exit(1);
  }

  await mkdir(OUTPUT_DIR, { recursive: true });
  const state = await loadState();

  let items;       // pre-generated content mode
  let topics;      // generate-from-topics mode
  let label;

  if (opts.fromDir) {
    items = await loadContentDir(opts.fromDir);
    label = `${opts.fromDir} (${items.length} JSON files)`;
    console.log(`[batch] mode:   render-only (--from-dir)`);
  } else {
    topics = await loadTopics(opts.input);
    label = `${opts.input} (${topics.length} topics)`;
    console.log(`[batch] mode:   generate + render`);
  }

  console.log(`[batch] input:  ${label}`);
  console.log(`[batch] state:  ${STATE_PATH}`);
  if (opts.retryErrors) console.log("[batch] flag:   --retry-errors (will re-process error_* entries)");
  if (opts.limit !== Infinity) console.log(`[batch] flag:   --limit ${opts.limit}`);

  const browser = await launchRenderer();
  const stats = { ok: 0, skipped: 0, failed: 0, processed: 0 };

  let cancelled = false;
  const onSignal = () => {
    if (cancelled) return;
    cancelled = true;
    console.log("\n[batch] received signal, finishing current item and exiting...");
  };
  process.once("SIGINT", onSignal);
  process.once("SIGTERM", onSignal);

  const queue = opts.fromDir ? items : topics;
  try {
    for (let i = 0; i < queue.length; i++) {
      if (cancelled) break;
      if (stats.processed >= opts.limit) {
        console.log(`\n[batch] limit ${opts.limit} reached`);
        break;
      }

      let key, label;
      if (opts.fromDir) {
        const item = queue[i];
        key = item.key;
        label = `${item.key}  (${basename(item.path)})`;
      } else {
        key = queue[i];
        label = key;
      }

      const prev = state[key];
      console.log(`\n[${i + 1}/${queue.length}] ${label}`);

      if (shouldSkip(prev, opts.retryErrors)) {
        console.log(`  ✓ status=${prev.status} — skipping`);
        stats.skipped++;
        continue;
      }

      stats.processed++;
      const result = opts.fromDir
        ? await processContentItem(queue[i], state, browser)
        : await processTopic(key, state, browser);
      if (result.ok) {
        console.log("  ✓ done");
        stats.ok++;
      } else {
        console.log(`  ✗ ${result.stage} stage failed: ${result.error.message}`);
        stats.failed++;
      }
    }
  } finally {
    await browser.close();
  }

  console.log("\n=== batch summary ===");
  console.log(`  total items:  ${queue.length}`);
  console.log(`  processed:    ${stats.processed}`);
  console.log(`  ok:           ${stats.ok}`);
  console.log(`  skipped:      ${stats.skipped}`);
  console.log(`  failed:       ${stats.failed}`);
  if (stats.failed > 0) {
    console.log(`\n  re-run with --retry-errors to retry failures.`);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("\n[batch] fatal:", err.message);
  if (err.stack) console.error(err.stack);
  process.exit(1);
});

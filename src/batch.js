import "dotenv/config";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

import { generateContent } from "./generate-content.js";
import { renderImages, launchRenderer } from "./render-images.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const OUTPUT_DIR = join(ROOT, "output");
const DEFAULT_INPUT = join(ROOT, "data", "topics.json");
const STATE_PATH = join(OUTPUT_DIR, "batch-state.json");

function parseArgs(argv) {
  const opts = { input: null, retryErrors: false, limit: Infinity };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--retry-errors") opts.retryErrors = true;
    else if (a === "--limit") opts.limit = Number(argv[++i]);
    else if (a.startsWith("--")) throw new Error(`Unknown flag: ${a}`);
    else if (!opts.input) opts.input = a;
    else throw new Error(`Unexpected argument: ${a}`);
  }
  if (!opts.input) opts.input = DEFAULT_INPUT;
  return opts;
}

function usage() {
  console.error(`Usage: node src/batch.js [topics.json] [--retry-errors] [--limit N]

Reads a JSON array of topic strings, generates content + images for each,
tracks progress in output/batch-state.json so reruns skip completed topics.

Examples:
  node src/batch.js                              # uses data/topics.json
  node src/batch.js my-topics.json
  node src/batch.js --limit 3                    # only first 3 unfinished
  node src/batch.js --retry-errors               # re-process error_* entries`);
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

async function main() {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (err) {
    console.error(`[batch] ${err.message}\n`);
    usage();
    process.exit(2);
  }

  if (!process.env.ANTHROPIC_API_KEY) {
    console.error("[batch] ANTHROPIC_API_KEY 가 .env 파일에 설정되어 있어야 합니다.");
    process.exit(1);
  }

  await mkdir(OUTPUT_DIR, { recursive: true });
  const topics = await loadTopics(opts.input);
  const state = await loadState();

  console.log(`[batch] input:  ${opts.input}`);
  console.log(`[batch] topics: ${topics.length}`);
  console.log(`[batch] state:  ${STATE_PATH}`);
  if (opts.retryErrors) console.log("[batch] flag:   --retry-errors (will re-process error_* entries)");
  if (opts.limit !== Infinity) console.log(`[batch] flag:   --limit ${opts.limit}`);

  const browser = await launchRenderer();
  const stats = { ok: 0, skipped: 0, failed: 0, processed: 0 };

  // Cleanup on Ctrl-C
  let cancelled = false;
  const onSignal = async () => {
    if (cancelled) return;
    cancelled = true;
    console.log("\n[batch] received signal, finishing current topic and exiting...");
  };
  process.once("SIGINT", onSignal);
  process.once("SIGTERM", onSignal);

  try {
    for (let i = 0; i < topics.length; i++) {
      if (cancelled) break;
      if (stats.processed >= opts.limit) {
        console.log(`\n[batch] limit ${opts.limit} reached`);
        break;
      }

      const topic = topics[i];
      const prev = state[topic];
      console.log(`\n[${i + 1}/${topics.length}] ${topic}`);

      if (shouldSkip(prev, opts.retryErrors)) {
        console.log(`  ✓ status=${prev.status} — skipping`);
        stats.skipped++;
        continue;
      }

      stats.processed++;
      const result = await processTopic(topic, state, browser);
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
  console.log(`  total topics: ${topics.length}`);
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

import "dotenv/config";
import { writeFile, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { generateContent } from "./generate-content.js";
import { renderImages, launchRenderer } from "./render-images.js";
import { uploadImage } from "./image-host.js";
import { InstagramClient, uploadCarousel } from "./instagram.js";
import { SheetsClient } from "./sheets-client.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const OUTPUT_DIR = join(ROOT, "output");

const DEFAULT_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes
const IG_CAPTION_LIMIT = 2200;

function parseArgs(argv) {
  const opts = {
    watch: false,
    intervalMs: DEFAULT_INTERVAL_MS,
    limit: Infinity,
    publish: true,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--watch") opts.watch = true;
    else if (a === "--interval") {
      const sec = Number(argv[++i]);
      if (!Number.isFinite(sec) || sec <= 0) throw new Error(`--interval needs positive seconds`);
      opts.intervalMs = sec * 1000;
    } else if (a === "--limit") opts.limit = Number(argv[++i]);
    else if (a === "--no-publish") opts.publish = false;
    else if (a.startsWith("--")) throw new Error(`Unknown flag: ${a}`);
    else throw new Error(`Unexpected positional arg: ${a}`);
  }
  return opts;
}

function usage() {
  console.error(`Usage: node src/sheets-runner.js [--watch] [--interval N] [--limit N] [--no-publish]

  --watch              계속 폴링 (기본 1회만 실행)
  --interval N         폴링 간격 (초, 기본 300초)
  --limit N            한 사이클당 최대 N개 처리
  --no-publish         imgbb URL까지만 쓰고 IG 발행은 스킵 (status: images_done)

Required env: ANTHROPIC_API_KEY, IMGBB_API_KEY, GOOGLE_SHEETS_ID, GOOGLE_SERVICE_ACCOUNT_JSON
Required for IG publish: IG_ACCESS_TOKEN, IG_USER_ID`);
}

function formatCaption(caption) {
  if (!caption || typeof caption !== "object") return "";
  const parts = [caption.title, caption.body, caption.cta, caption.source, caption.hashtags];
  let text = parts.filter(Boolean).join("\n\n");
  if (text.length > IG_CAPTION_LIMIT) text = text.slice(0, IG_CAPTION_LIMIT - 3) + "...";
  return text;
}

async function processRow(row, deps) {
  const { sheets, browser, igClient, publish } = deps;
  const startedAt = new Date().toISOString();

  try {
    // Mark as processing for visibility
    await sheets.updateCells(row.rowIndex, { status: "processing", processed_at: startedAt });

    // 1. Generate JSON
    console.log("  [1/4] generating JSON via Claude...");
    const content = await generateContent(row.topic_title);
    if (!content.topic_id || !Array.isArray(content.slides)) {
      throw new Error("generated JSON missing topic_id or slides");
    }
    const captionText = formatCaption(content.caption);

    // 2. Render images locally
    console.log("  [2/4] rendering images...");
    const localPaths = await renderImages(content, OUTPUT_DIR, { browser });

    // 3. Upload images to imgbb (public URLs)
    console.log(`  [3/4] uploading ${localPaths.length} images to imgbb...`);
    const urls = [];
    for (const p of localPaths) urls.push(await uploadImage(p));

    // Persist content + URLs to sheet right away (so user sees progress even if IG step fails)
    const slideTypes = content.slides.map((s) => s.type);
    const idxCover = slideTypes.indexOf("cover");
    const idxCta = slideTypes.lastIndexOf("cta");
    const idxBody = slideTypes.findIndex((t, i) => i !== idxCover && i !== idxCta);
    const cover_img_url = idxCover >= 0 ? urls[idxCover] : urls[0];
    const body_img_url = idxBody >= 0 ? urls[idxBody] : urls[1] ?? "";
    const cta_img_url = idxCta >= 0 ? urls[idxCta] : urls[2] ?? urls[urls.length - 1];

    await sheets.updateCells(row.rowIndex, {
      topic_id: content.topic_id,
      category: content.category ?? "",
      card_type: content.card_type ?? "",
      json_data: JSON.stringify(content),
      cover_img_url,
      body_img_url,
      cta_img_url,
      caption: captionText,
      status: "images_done",
      error_message: "",
      processed_at: new Date().toISOString(),
    });

    if (!publish) {
      return { ok: true, stage: "images_done", topic_id: content.topic_id };
    }

    // 4. Publish to Instagram
    console.log("  [4/4] publishing to Instagram...");
    const result = await uploadCarousel(igClient, urls, captionText);

    await sheets.updateCells(row.rowIndex, {
      status: "uploaded",
      error_message: result.permalink ?? `media_id=${result.mediaId}`,
      processed_at: new Date().toISOString(),
    });

    return { ok: true, stage: "uploaded", topic_id: content.topic_id, permalink: result.permalink, mediaId: result.mediaId };
  } catch (err) {
    // Determine which stage failed for clearer status
    const statusBefore = row.status?.toLowerCase();
    let errStatus = "error_json";
    if (statusBefore === "images_done") errStatus = "error_upload";
    else if (err.message?.includes("imgbb") || err.message?.includes("Puppeteer") || err.message?.includes("template")) errStatus = "error_image";
    else if (err.message?.startsWith("Graph API") || err.message?.includes("Instagram")) errStatus = "error_upload";

    try {
      await sheets.updateCells(row.rowIndex, {
        status: errStatus,
        error_message: String(err.message ?? err).slice(0, 1000),
        processed_at: new Date().toISOString(),
      });
    } catch (writeErr) {
      console.error(`  ⚠ also failed to write error to sheet: ${writeErr.message}`);
    }
    return { ok: false, error: err, stage: errStatus };
  }
}

async function runOneCycle(opts, deps) {
  const all = await deps.sheets.readAll();
  const pending = all.filter((r) => r.status?.toLowerCase() === "pending" && r.topic_title);
  console.log(`[cycle] found ${pending.length} pending row(s)`);

  const stats = { processed: 0, ok: 0, failed: 0 };
  for (const row of pending) {
    if (stats.processed >= opts.limit) {
      console.log(`[cycle] limit ${opts.limit} reached`);
      break;
    }
    if (deps.cancelled?.()) break;
    stats.processed++;
    console.log(`\n[row ${row.rowIndex}] ${row.topic_title}`);
    const r = await processRow(row, deps);
    if (r.ok) {
      console.log(`  ✓ ${r.stage}${r.permalink ? ` → ${r.permalink}` : ""}`);
      stats.ok++;
    } else {
      console.log(`  ✗ ${r.stage}: ${r.error.message}`);
      stats.failed++;
    }
  }
  return stats;
}

async function main() {
  let opts;
  try { opts = parseArgs(process.argv.slice(2)); }
  catch (err) { console.error(`[sheets] ${err.message}\n`); usage(); process.exit(2); }

  if (!process.env.ANTHROPIC_API_KEY) { console.error("[sheets] ANTHROPIC_API_KEY 필요"); process.exit(1); }
  if (!process.env.IMGBB_API_KEY) { console.error("[sheets] IMGBB_API_KEY 필요"); process.exit(1); }
  if (!process.env.GOOGLE_SHEETS_ID) { console.error("[sheets] GOOGLE_SHEETS_ID 필요"); process.exit(1); }
  if (!process.env.GOOGLE_SERVICE_ACCOUNT_JSON) { console.error("[sheets] GOOGLE_SERVICE_ACCOUNT_JSON (파일 경로) 필요"); process.exit(1); }
  if (opts.publish && (!process.env.IG_ACCESS_TOKEN || !process.env.IG_USER_ID)) {
    console.error("[sheets] IG_ACCESS_TOKEN/IG_USER_ID 필요. --no-publish 로 imgbb까지만 가능.");
    process.exit(1);
  }

  await mkdir(OUTPUT_DIR, { recursive: true });

  const sheets = new SheetsClient({
    spreadsheetId: process.env.GOOGLE_SHEETS_ID,
    keyFile: process.env.GOOGLE_SERVICE_ACCOUNT_JSON,
  });

  console.log("[sheets] verifying headers...");
  const hdr = await sheets.ensureHeaders();
  if (hdr.created) console.log("[sheets] header row created (시트 1행에 컬럼명 자동 입력)");

  const stale = await sheets.resetStaleProcessing();
  if (stale > 0) console.log(`[sheets] reset ${stale} stale 'processing' row(s) → pending (crash recovery)`);

  const igClient = opts.publish ? new InstagramClient() : null;
  if (igClient && process.env.IG_SKIP_PREFLIGHT !== "true") {
    try {
      const acct = await igClient.getAccountInfo();
      console.log(`[sheets] IG authenticated as @${acct.username ?? acct.id}`);
    } catch (err) {
      console.error(`[sheets] IG 인증 실패: ${err.message}`);
      console.error("        토큰 만료 가능성 → npm run refresh-token");
      process.exit(1);
    }
  }

  const browser = await launchRenderer();
  let cancelled = false;
  process.once("SIGINT", () => { cancelled = true; console.log("\n[sheets] 신호 받음 — 현재 row 마무리 후 종료"); });
  process.once("SIGTERM", () => { cancelled = true; });

  const deps = { sheets, browser, igClient, publish: opts.publish, cancelled: () => cancelled };

  try {
    if (!opts.watch) {
      const stats = await runOneCycle(opts, deps);
      console.log(`\n=== summary === processed=${stats.processed} ok=${stats.ok} failed=${stats.failed}`);
      if (stats.failed > 0) process.exit(1);
      return;
    }

    console.log(`[sheets] watch mode: poll every ${opts.intervalMs / 1000}s`);
    while (!cancelled) {
      try {
        const stats = await runOneCycle(opts, deps);
        if (stats.processed > 0) console.log(`[cycle done] processed=${stats.processed} ok=${stats.ok} failed=${stats.failed}`);
      } catch (err) {
        console.error(`[cycle error] ${err.message}`);
      }
      if (cancelled) break;
      await new Promise((r) => setTimeout(r, opts.intervalMs));
    }
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error("\n[sheets] fatal:", err.message);
  if (err.stack) console.error(err.stack);
  process.exit(1);
});

import "dotenv/config";
import { readFile, writeFile, readdir, mkdir } from "node:fs/promises";
import { existsSync, writeFileSync, unlinkSync, statSync, readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join, basename } from "node:path";

import { uploadImage } from "./image-host.js";
import { InstagramClient, uploadCarousel } from "./instagram.js";
import { debugToken, refreshLongLivedToken, updateEnvTokenLine } from "./token.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const OUTPUT_DIR = join(ROOT, "output");
const STATE_PATH = join(OUTPUT_DIR, "upload-state.json");
const HISTORY_PATH = join(OUTPUT_DIR, "insights-history.json");
const LOCK_PATH = join(OUTPUT_DIR, ".upload.lock");
const ENV_PATH = join(ROOT, ".env");

const IG_CAPTION_LIMIT = 2200;
const IG_HASHTAG_LIMIT = 30;
// State files we should never treat as content JSON
const STATE_FILES = new Set(["upload-state.json", "batch-state.json", "insights-history.json"]);

const DAY_MS = 24 * 60 * 60 * 1000;
const LOCK_STALE_MS = 3 * 60 * 60 * 1000;   // 3h 넘은 락은 죽은 프로세스로 간주
const TOKEN_WARN_DAYS = 14;                  // 만료 N일 전부터 경고/자동갱신
const SNAPSHOT_MIN_GAP_H = 6;                // 같은 게시물 스냅샷 최소 간격
const SNAPSHOT_MAX_AGE_D = 30;               // 30일 지난 게시물은 스냅샷 중단 (지표 정체)

function parseArgs(argv) {
  const opts = {
    topicIds: [], all: false, dryRun: false, limit: Infinity,
    interval: 0, dailyCap: Infinity, label: null,
    report: false, snapshot: false, at: 48, hashtagsInComment: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--all") opts.all = true;
    else if (a === "--dry-run") opts.dryRun = true;
    else if (a === "--report") opts.report = true;
    else if (a === "--snapshot") opts.snapshot = true;
    else if (a === "--hashtags-in-comment") opts.hashtagsInComment = true;
    else if (a === "--limit") opts.limit = Number(argv[++i]);
    else if (a === "--interval") opts.interval = Number(argv[++i]);     // 발행 사이 대기(초)
    else if (a === "--daily-cap") opts.dailyCap = Number(argv[++i]);    // 지난 24h 누적 발행 상한
    else if (a === "--label") opts.label = argv[++i];                   // 슬롯 태그 (예: morning/evening)
    else if (a === "--at") opts.at = Number(argv[++i]);                 // 리포트 비교 기준 나이(시간)
    else if (a.startsWith("--")) throw new Error(`Unknown flag: ${a}`);
    else opts.topicIds.push(a);
  }
  if (Number.isNaN(opts.limit) || opts.limit < 0) throw new Error("--limit 는 0 이상 숫자");
  if (Number.isNaN(opts.interval) || opts.interval < 0) throw new Error("--interval 는 0 이상 숫자(초)");
  if (Number.isNaN(opts.dailyCap) || opts.dailyCap < 1) throw new Error("--daily-cap 은 1 이상 숫자");
  if (Number.isNaN(opts.at) || opts.at <= 0) throw new Error("--at 은 0보다 큰 숫자(시간)");
  return opts;
}

function usage() {
  console.error(`Usage:
  node src/upload-instagram.js <topic_id> [...]            특정 topic_id 업로드
  node src/upload-instagram.js --all [--limit N]           미업로드 토픽 자동 발행 (카테고리 로테이션·시즌 우선 큐)
  node src/upload-instagram.js <id> --dry-run              imgbb까지만, IG publish 안 함

안전 발행 (throttle):
  --interval <초>          한 실행 안에서 발행 사이 대기 (예: --interval 1800 = 30분)
  --daily-cap <N>          지난 24시간 누적 발행 상한 (upload-state 기준 자동 계산, 초과 시 중단)
  --label <이름>           각 발행에 슬롯 태그 저장 (A/B용, 예: --label morning)
  --hashtags-in-comment    해시태그를 캡션 대신 첫 댓글로 발행

A/B 인사이트:
  --snapshot               업로드 게시물 지표를 insights-history.json 에 기록 (매일 cron 권장)
  --report [--at 48]       스냅샷 기반, 게시 후 <at>시간 시점 지표를 슬롯별 비교 (기본 48h)

예) 출근길: node src/upload-instagram.js --all --limit 1 --daily-cap 2 --label morning
    스냅샷: node src/upload-instagram.js --snapshot        (매일 23:50 cron)
    비교:   node src/upload-instagram.js --report --at 48

Required env: IMGBB_API_KEY, IG_ACCESS_TOKEN, IG_USER_ID (--dry-run은 IMGBB만 / --report·--snapshot은 IG만)
Optional env: WEBHOOK_URL (실패 알림), AUTO_REFRESH_TOKEN=true + FB_APP_ID/FB_APP_SECRET (토큰 자동 갱신)`);
}

/* ─────────────────────────── 알림 (웹훅) ─────────────────────────── */

/** WEBHOOK_URL 로 실패/경고 알림 (Slack `text` · Discord `content` 겸용, best-effort). */
async function notify(text) {
  const url = process.env.WEBHOOK_URL;
  if (!url) return;
  try {
    await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text, content: text }),
      signal: AbortSignal.timeout(5000),
    });
  } catch (err) {
    console.warn(`  [notify] 웹훅 전송 실패 (무시): ${err.message}`);
  }
}

/* ─────────────────────────── 동시 실행 락 ─────────────────────────── */

/** cron 중복/수동 동시 실행 방지. 3h 넘은 락은 죽은 프로세스로 보고 탈취. */
function acquireLock() {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      writeFileSync(LOCK_PATH, JSON.stringify({ pid: process.pid, started_at: new Date().toISOString() }), { flag: "wx" });
      return { ok: true };
    } catch (err) {
      if (err.code !== "EEXIST") throw err;
      let info = {};
      try { info = JSON.parse(readFileSync(LOCK_PATH, "utf-8")); } catch { /* 손상된 락 */ }
      const ageMs = Date.now() - statSync(LOCK_PATH).mtimeMs;
      if (ageMs < LOCK_STALE_MS) {
        return { ok: false, pid: info.pid, ageMin: Math.round(ageMs / 60000) };
      }
      console.warn(`[lock] ${Math.round(ageMs / 3600000)}h 지난 락(pid=${info.pid ?? "?"}) — 죽은 프로세스로 간주하고 대체`);
      try { unlinkSync(LOCK_PATH); } catch { /* 경합 시 다음 시도에서 판정 */ }
    }
  }
  return { ok: false, pid: null, ageMin: 0 };
}

function releaseLockSync() {
  try { if (existsSync(LOCK_PATH)) unlinkSync(LOCK_PATH); } catch { /* best-effort */ }
}

/* ─────────────────────────── 유틸 ─────────────────────────── */

/** 지난 windowMs(기본 24h) 안에 status=uploaded 된 건수 (rolling). */
function countRecentUploads(state, windowMs = DAY_MS, now = Date.now()) {
  let n = 0;
  for (const k of Object.keys(state)) {
    const e = state[k];
    if (e?.status === "uploaded" && e.uploaded_at && now - new Date(e.uploaded_at).getTime() < windowMs) n++;
  }
  return n;
}

/** 취소 가능한 sleep — isCancelled()가 true가 되면 즉시 깨어남. */
function sleep(ms, isCancelled = () => false) {
  return new Promise((resolve) => {
    if (ms <= 0) return resolve();
    const tick = Math.min(1000, ms);
    let elapsed = 0;
    const t = setInterval(() => {
      elapsed += tick;
      if (elapsed >= ms || isCancelled()) { clearInterval(t); resolve(); }
    }, tick);
  });
}

async function loadJsonFile(path, fallback) {
  if (!existsSync(path)) return fallback;
  try {
    return JSON.parse(await readFile(path, "utf-8"));
  } catch (err) {
    console.warn(`[upload] ${basename(path)} corrupt, starting fresh: ${err.message}`);
    return fallback;
  }
}

const loadState = () => loadJsonFile(STATE_PATH, {});
const saveState = (state) => writeFile(STATE_PATH, JSON.stringify(state, null, 2), "utf-8");
const loadHistory = () => loadJsonFile(HISTORY_PATH, {});
const saveHistory = (h) => writeFile(HISTORY_PATH, JSON.stringify(h, null, 2), "utf-8");

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
  return topics.sort(); // 결정적 순서 (재실행/슬롯 분배 일관성)
}

/* ──────────────── 발행 큐: 시즌 우선 + 카테고리 로테이션 ──────────────── */

/** season 필드가 현재 달에 제철인지. 상시/미지정은 항상 true. */
function seasonInWindow(season, month) {
  if (season === "상반기") return month >= 1 && month <= 6;
  if (season === "하반기") return month >= 7 && month <= 12;
  return true;
}

/**
 * 같은 카테고리 연속 발행을 피하도록 큐를 정렬한다.
 * - 제철(시즌) 토픽 먼저, 비시즌은 큐 맨 뒤로 (스킵하지 않음)
 * - 카테고리 round-robin, 직전 발행 카테고리의 다음 카테고리부터 시작
 * - 카테고리·토픽 정렬로 결정적(재실행 일관) 순서
 *
 * @param {{topic_id:string, category?:string, season?:string}[]} metas
 * @param {string|null} lastCategory - 직전 업로드의 카테고리
 * @param {Date} [now]
 */
function orderQueue(metas, lastCategory, now = new Date()) {
  const month = now.getMonth() + 1;
  const inSeason = metas.filter((m) => seasonInWindow(m.season, month));
  const offSeason = metas.filter((m) => !seasonInWindow(m.season, month));

  const roundRobin = (list, startAfter) => {
    const byCat = new Map();
    for (const m of [...list].sort((a, b) => a.topic_id.localeCompare(b.topic_id))) {
      const c = m.category ?? "기타";
      if (!byCat.has(c)) byCat.set(c, []);
      byCat.get(c).push(m);
    }
    const cats = [...byCat.keys()].sort();
    if (cats.length === 0) return [];
    let idx = 0;
    if (startAfter) {
      const i = cats.indexOf(startAfter);
      if (i >= 0) idx = (i + 1) % cats.length;
    }
    const ordered = [];
    let remaining = list.length;
    while (remaining > 0) {
      const q = byCat.get(cats[idx % cats.length]);
      idx++;
      if (q && q.length) { ordered.push(q.shift()); remaining--; }
    }
    return ordered;
  };

  const first = roundRobin(inSeason, lastCategory);
  const lastCatOfFirst = first.length ? first[first.length - 1].category ?? null : lastCategory;
  return { ordered: [...first, ...roundRobin(offSeason, lastCatOfFirst)], offSeasonCount: offSeason.length };
}

/** output/{id}.json 에서 큐 정렬용 메타(category/season)만 읽는다. */
async function loadMetas(topicIds) {
  const metas = [];
  for (const id of topicIds) {
    try {
      const c = JSON.parse(await readFile(join(OUTPUT_DIR, `${id}.json`), "utf-8"));
      metas.push({ topic_id: id, category: c.category ?? null, season: c.season ?? null });
    } catch {
      metas.push({ topic_id: id, category: null, season: null });
    }
  }
  return metas;
}

/** 가장 최근 업로드의 카테고리 (로테이션 시작점). */
function latestUploadedCategory(state) {
  let latest = null;
  for (const e of Object.values(state)) {
    if (e?.status !== "uploaded" || !e.uploaded_at) continue;
    if (!latest || new Date(e.uploaded_at) > new Date(latest.uploaded_at)) latest = e;
  }
  return latest?.category ?? null;
}

/* ─────────────────────────── 캡션 ─────────────────────────── */

/**
 * 콘텐츠 caption 객체 → 발행용 텍스트.
 * @returns {{text:string, hashtags:string|null}} hashtagsInComment=true 면 해시태그를 분리해 반환
 */
function formatCaption(caption, { hashtagsInComment = false } = {}) {
  if (!caption || typeof caption !== "object") return { text: "", hashtags: null };
  const parts = [];
  if (caption.title) parts.push(caption.title);
  if (caption.body) parts.push(caption.body);
  if (caption.cta) parts.push(caption.cta);
  if (caption.source) parts.push(caption.source);
  const hashtags = caption.hashtags || null;
  if (hashtags && !hashtagsInComment) parts.push(hashtags);
  let text = parts.filter(Boolean).join("\n\n");

  // Hashtag count check (캡션+댓글 어디로 가든 총량 기준)
  const hashtagCount = ((hashtags ?? "").match(/#\S+/g) ?? []).length;
  if (hashtagCount > IG_HASHTAG_LIMIT) {
    console.warn(`  [caption] 해시태그 ${hashtagCount}개 → ${IG_HASHTAG_LIMIT}개 한도 초과 (그대로 보냄, IG가 잘라냄)`);
  }

  // Length check
  if (text.length > IG_CAPTION_LIMIT) {
    console.warn(`  [caption] ${text.length}자 → ${IG_CAPTION_LIMIT}자로 truncate`);
    text = text.slice(0, IG_CAPTION_LIMIT - 3) + "...";
  }
  return { text, hashtags: hashtagsInComment ? hashtags : null };
}

/* ─────────────────────────── 스냅샷 / 리포트 ─────────────────────────── */

/** 업로드된 게시물의 현재 지표를 insights-history.json 에 누적 기록. */
async function runSnapshot(igClient, state) {
  const uploaded = Object.values(state).filter((e) => e.status === "uploaded" && e.media_id && e.uploaded_at);
  if (uploaded.length === 0) {
    console.log("[snapshot] 업로드된 게시물이 없습니다.");
    return;
  }
  const history = await loadHistory();
  const now = Date.now();
  let taken = 0, skippedFresh = 0, skippedOld = 0, failed = 0;

  for (const e of uploaded) {
    const ageH = (now - new Date(e.uploaded_at).getTime()) / 3600000;
    if (ageH > SNAPSHOT_MAX_AGE_D * 24) { skippedOld++; continue; }
    const snaps = history[e.topic_id] ?? [];
    const last = snaps[snaps.length - 1];
    if (last && (now - new Date(last.at).getTime()) / 3600000 < SNAPSHOT_MIN_GAP_H) { skippedFresh++; continue; }

    const ins = await igClient.getMediaInsights(e.media_id);
    if (ins.reach === null && ins.likes === null) { failed++; console.warn(`  [snapshot] ${e.topic_id}: 지표 조회 실패 (${ins.insightsError ?? ins.error ?? "?"})`); continue; }
    snaps.push({
      at: new Date(now).toISOString(),
      age_h: Math.round(ageH * 10) / 10,
      reach: ins.reach, likes: ins.likes, comments: ins.comments, saved: ins.saved, interactions: ins.interactions,
    });
    history[e.topic_id] = snaps;
    taken++;
    console.log(`  ✓ ${e.topic_id} (age ${Math.round(ageH)}h) reach=${ins.reach ?? "-"} ♥=${ins.likes ?? "-"}`);
  }

  await saveHistory(history);
  console.log(`\n[snapshot] 기록 ${taken} · 최근기록있어스킵 ${skippedFresh} · ${SNAPSHOT_MAX_AGE_D}일경과스킵 ${skippedOld} · 실패 ${failed}`);
  console.log(`           → ${HISTORY_PATH}`);
}

/** 목표 나이(targetH)에 가장 가까운 스냅샷 선택 (±50% 창 밖이면 null). */
function chooseSnapshot(snaps, targetH) {
  if (!Array.isArray(snaps) || snaps.length === 0) return null;
  const windowLo = targetH * 0.5, windowHi = targetH * 1.5;
  let best = null;
  for (const s of snaps) {
    if (typeof s.age_h !== "number" || s.age_h < windowLo || s.age_h > windowHi) continue;
    if (!best || Math.abs(s.age_h - targetH) < Math.abs(best.age_h - targetH)) best = s;
  }
  return best;
}

/**
 * A/B 리포트: 슬롯(label)별 지표 비교.
 * 스냅샷이 있으면 "게시 후 --at 시간" 시점 지표로 나이를 통제해 공정 비교,
 * 스냅샷이 없는 게시물은 라이브 현재값으로 폴백(나이 편향 표시).
 */
async function runReport(igClient, state, { at = 48 } = {}) {
  const uploaded = Object.values(state).filter((e) => e.status === "uploaded" && e.media_id);
  if (uploaded.length === 0) {
    console.log("[report] 업로드된 게시물이 없습니다.");
    return;
  }
  const history = await loadHistory();
  const hasHistory = Object.keys(history).length > 0;
  console.log(`[report] ${uploaded.length}개 게시물 · 비교 기준: 게시 후 ${at}h ${hasHistory ? "(스냅샷 기반)" : "(스냅샷 없음 → 현재 누적값, 나이 편향 있음)"}\n`);

  const rows = [];
  for (const e of uploaded) {
    const slot = e.slot || "(미지정)";
    const snap = chooseSnapshot(history[e.topic_id], at);
    if (snap) {
      rows.push({ slot, source: "snap", age_h: snap.age_h, reach: snap.reach, likes: snap.likes, comments: snap.comments, saved: snap.saved, interactions: snap.interactions });
    } else {
      const ins = await igClient.getMediaInsights(e.media_id);
      const ageH = e.uploaded_at ? Math.round((Date.now() - new Date(e.uploaded_at).getTime()) / 3600000) : null;
      rows.push({ slot, source: "live", age_h: ageH, reach: ins.reach, likes: ins.likes, comments: ins.comments, saved: ins.saved, interactions: ins.interactions });
    }
  }

  const groups = {};
  for (const r of rows) (groups[r.slot] ??= []).push(r);

  const avg = (arr, key) => {
    const vals = arr.map((x) => x[key]).filter((v) => typeof v === "number");
    return vals.length ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : null;
  };
  const fmt = (v) => (v === null ? "-" : String(v));

  console.log(`슬롯별 평균 (n / 평균나이 / reach / ♥ / 💬 / 🔖 / Σ상호작용)`);
  console.log("─".repeat(78));
  const slots = Object.keys(groups).sort();
  for (const slot of slots) {
    const g = groups[slot];
    const snapN = g.filter((r) => r.source === "snap").length;
    console.log(
      `${slot.padEnd(12)} n=${String(g.length).padEnd(3)} age≈${fmt(avg(g, "age_h")).padStart(4)}h  ` +
      `reach=${fmt(avg(g, "reach")).padStart(6)}  ♥=${fmt(avg(g, "likes")).padStart(5)}  ` +
      `💬=${fmt(avg(g, "comments")).padStart(4)}  🔖=${fmt(avg(g, "saved")).padStart(4)}  ` +
      `Σ=${fmt(avg(g, "interactions")).padStart(5)}  (스냅 ${snapN}/라이브 ${g.length - snapN})`,
    );
  }
  console.log("─".repeat(78));

  if (slots.length >= 2 && slots.every((s) => avg(groups[s], "reach") !== null)) {
    const ranked = slots.map((s) => [s, avg(groups[s], "reach")]).sort((a, b) => b[1] - a[1]);
    console.log(`\n📊 reach 우세 슬롯: ${ranked[0][0]} (평균 ${ranked[0][1]}) > ${ranked.slice(1).map(([s, v]) => `${s} (${v})`).join(" > ")}`);
    console.log("   ※ 슬롯당 7건+ 쌓인 뒤 판단. 주제 차이가 섞여 있으니 참고용.");
  }
  if (!hasHistory) console.log("\n팁: 매일 `node src/upload-instagram.js --snapshot` cron 을 걸면 다음 리포트부터 나이 통제 비교가 됩니다.");
}

/* ─────────────────────────── 발행 ─────────────────────────── */

/** Find image files for a topic (cover, body, cta). Returns paths in slide order. */
async function findImagesForTopic(topic_id) {
  const entries = await readdir(OUTPUT_DIR);
  const prefix = `${topic_id}_`;
  const matched = entries
    .filter((n) => n.startsWith(prefix) && n.endsWith(".jpg"))
    .sort(); // names contain zero-padded slide numbers, so lex sort = slide order
  return matched.map((n) => join(OUTPUT_DIR, n));
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

async function processTopic(topic_id, igClient, state, { dryRun, label, hashtagsInComment }) {
  const entry = state[topic_id] ?? { topic_id, status: "pending" };
  state[topic_id] = entry;
  entry.attempts = (entry.attempts ?? 0) + 1;
  entry.last_attempt_at = new Date().toISOString();

  try {
    const { content, images } = await loadTopicContent(topic_id);
    const { text: caption, hashtags } = formatCaption(content.caption, { hashtagsInComment });
    entry.category = content.category ?? entry.category ?? null;

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
    if (label) entry.slot = label;
    delete entry.error;
    await saveState(state);

    // 해시태그 첫 댓글 (best-effort — 실패해도 발행 자체는 성공)
    if (hashtagsInComment && hashtags) {
      try {
        entry.hashtag_comment_id = await igClient.postComment(result.mediaId, hashtags);
        await saveState(state);
        console.log("  [IG] 해시태그 첫 댓글 작성 완료");
      } catch (err) {
        console.warn(`  [IG] 해시태그 댓글 실패 (게시물은 정상): ${err.message}`);
      }
    }

    return { ok: true, result };
  } catch (err) {
    entry.status = "error";
    entry.error = err.message;
    await saveState(state);
    return { ok: false, error: err };
  }
}

/* ───────────────────── 토큰 preflight (만료 감지/자동갱신) ───────────────────── */

async function tokenPreflight(igClient) {
  const appCreds = { appId: process.env.FB_APP_ID, appSecret: process.env.FB_APP_SECRET };
  const dbg = await debugToken(igClient.accessToken, appCreds);
  if (!dbg?.expiresAt) return; // 만료 없음(0) 또는 조회 불가 → 조용히 통과

  if (dbg.daysLeft > TOKEN_WARN_DAYS) {
    console.log(`[upload] 토큰 만료까지 ${dbg.daysLeft}일`);
    return;
  }

  console.warn(`[upload] ⚠️ IG 토큰 만료 ${dbg.daysLeft}일 전 (${dbg.expiresAt.toISOString()})`);
  if (process.env.AUTO_REFRESH_TOKEN === "true") {
    try {
      const r = await refreshLongLivedToken(igClient.accessToken, appCreds);
      await updateEnvTokenLine(ENV_PATH, r.accessToken);
      igClient.accessToken = r.accessToken;
      console.log(`[upload] ✓ 토큰 자동 갱신 완료 (${r.method}, ~${Math.round(r.expiresInSec / 86400)}일) — .env 반영됨`);
    } catch (err) {
      console.error(`[upload] 토큰 자동 갱신 실패: ${err.message}`);
      await notify(`⚠️ [알쓸지잡10] IG 토큰 자동 갱신 실패 (만료 ${dbg.daysLeft}일 전): ${err.message}`);
    }
  } else {
    console.warn(`        → npm run refresh-token -- --write (또는 .env 에 AUTO_REFRESH_TOKEN=true)`);
    await notify(`⚠️ [알쓸지잡10] IG 토큰 만료 ${dbg.daysLeft}일 전 — refresh-token 실행 필요`);
  }
}

/* ─────────────────────────── main ─────────────────────────── */

async function main() {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (err) {
    console.error(`[upload] ${err.message}\n`);
    usage();
    process.exit(2);
  }

  // --report / --snapshot: 읽기 전용 계열 (IG 토큰만 필요, IMGBB·락 불필요)
  if (opts.report || opts.snapshot) {
    if (!process.env.IG_ACCESS_TOKEN || !process.env.IG_USER_ID) {
      console.error(`[${opts.report ? "report" : "snapshot"}] IG_ACCESS_TOKEN, IG_USER_ID 환경변수 필요.`);
      process.exit(1);
    }
    const client = new InstagramClient();
    const state = await loadState();
    if (opts.snapshot) await runSnapshot(client, state);
    if (opts.report) await runReport(client, state, { at: opts.at });
    return;
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

  // 동시 실행 방지 (state 경합 → daily-cap 오작동 차단)
  const lock = acquireLock();
  if (!lock.ok) {
    console.error(`[upload] 다른 업로드가 실행 중입니다 (pid=${lock.pid ?? "?"}, ${lock.ageMin}분 경과) — 종료`);
    console.error(`         강제 해제: rm ${LOCK_PATH}`);
    process.exit(1);
  }
  process.on("exit", releaseLockSync);

  const state = await loadState();

  let topics;
  if (opts.all) {
    const ids = await discoverTopics();
    if (ids.length === 0) {
      console.error("[upload] output/ 에 콘텐츠 JSON이 없습니다. 먼저 npm run batch 실행.");
      process.exit(1);
    }
    const metas = await loadMetas(ids);
    // dry-run 은 uploaded 여부와 무관하게 전체 재검증이 목적 → 제외하지 않음
    const pending = opts.dryRun ? metas : metas.filter((m) => state[m.topic_id]?.status !== "uploaded");
    const excluded = metas.length - pending.length;
    const { ordered, offSeasonCount } = orderQueue(pending, latestUploadedCategory(state));
    topics = ordered.map((m) => m.topic_id);
    console.log(`[upload] 큐 ${topics.length}건 (uploaded ${excluded}건 제외) · 카테고리 로테이션${offSeasonCount ? ` · 비시즌 ${offSeasonCount}건은 뒤로` : ""}`);
    if (topics.length === 0) {
      console.log("[upload] 발행할 항목이 없습니다 — 모두 uploaded.");
      return;
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
      console.error("        토큰이 만료됐을 수 있습니다 → npm run refresh-token -- --write");
      await notify(`🚨 [알쓸지잡10] IG 인증 실패 — 업로드 중단: ${err.message.slice(0, 200)}`);
      process.exit(1);
    }
    await tokenPreflight(igClient);
  }

  let cancelled = false;
  process.once("SIGINT", () => {
    if (cancelled) return;
    cancelled = true;
    console.log("\n[upload] 신호 받음 — 현재 토픽 마무리하고 종료합니다.");
  });
  process.once("SIGTERM", () => { cancelled = true; });

  if (opts.dailyCap !== Infinity && !opts.dryRun) {
    console.log(`[upload] daily-cap ${opts.dailyCap} (지난 24h 발행 ${countRecentUploads(state)}건)`);
  }
  if (opts.interval > 0) console.log(`[upload] interval ${opts.interval}s (발행 사이 대기)`);

  const stats = { processed: 0, ok: 0, skipped: 0, failed: 0 };
  const failures = [];

  for (let i = 0; i < topics.length; i++) {
    if (cancelled) break;
    if (stats.processed >= opts.limit) {
      console.log(`\n[upload] limit ${opts.limit} 도달`);
      break;
    }
    if (!opts.dryRun && opts.dailyCap !== Infinity && countRecentUploads(state) >= opts.dailyCap) {
      console.log(`\n[upload] daily-cap ${opts.dailyCap} 도달 (지난 24h) — 중단`);
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
    const result = await processTopic(topic_id, igClient, state, {
      dryRun: opts.dryRun, label: opts.label, hashtagsInComment: opts.hashtagsInComment,
    });
    if (result.ok) {
      if (result.dryRun) {
        console.log("  ✓ dry-run done");
      } else {
        console.log(`  ✓ published${opts.label ? ` [${opts.label}]` : ""}: ${result.result.permalink ?? `media_id=${result.result.mediaId}`}`);
      }
      stats.ok++;
    } else {
      console.log(`  ✗ failed: ${result.error.message}`);
      stats.failed++;
      failures.push({ topic_id, message: result.error.message.split("\n")[0] });
    }

    // throttle: 다음 발행 전 대기 (마지막·취소·한도 도달 시 생략)
    if (result.ok && !result.dryRun && opts.interval > 0 && !cancelled) {
      const capReached = opts.dailyCap !== Infinity && countRecentUploads(state) >= opts.dailyCap;
      const limitReached = stats.processed >= opts.limit;
      if (!capReached && !limitReached && i < topics.length - 1) {
        console.log(`  [throttle] ${opts.interval}s 대기 후 다음...`);
        await sleep(opts.interval * 1000, () => cancelled);
      }
    }
  }

  console.log("\n=== upload summary ===");
  console.log(`  total topics: ${topics.length}`);
  console.log(`  processed:    ${stats.processed}`);
  console.log(`  ok:           ${stats.ok}`);
  console.log(`  skipped:      ${stats.skipped}`);
  console.log(`  failed:       ${stats.failed}`);

  if (stats.failed > 0) {
    const detail = failures.slice(0, 3).map((f) => `${f.topic_id}: ${f.message}`).join(" | ");
    await notify(`🚨 [알쓸지잡10] 업로드 실패 ${stats.failed}건 — ${detail}${failures.length > 3 ? " …" : ""}`);
    process.exit(1);
  }
}

// 테스트에서 import 가능하도록 CLI 직접 실행일 때만 main() 구동
const isCLI = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isCLI) {
  main().catch(async (err) => {
    console.error("\n[upload] fatal:", err.message);
    if (err.stack) console.error(err.stack);
    await notify(`🚨 [알쓸지잡10] 업로드 fatal: ${String(err.message).slice(0, 200)}`);
    process.exit(1);
  });
}

export { formatCaption, countRecentUploads, orderQueue, seasonInWindow, chooseSnapshot };

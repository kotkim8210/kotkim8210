import { readFile, writeFile, readdir, mkdir, copyFile, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * 콘텐츠 JSON(data/contents/*.json) → 인스타/쓰레드 업로드용 번들 생성.
 *
 *   output/instagram_bundles/{topic_id}/
 *       1_표지.jpg 2_본문.jpg 3_cta.jpg   (output/ 에 렌더된 이미지가 있을 때만 복사)
 *       caption.txt          ← 인스타 캐러셀용 (제목+본문+CTA+출처+해시태그)
 *       threads_caption.txt  ← 쓰레드용 (훅+대화체+답글유도 질문+주제태그 1개)
 *   output/instagram_by_category/{n_카테고리}/{topic_id}/  ← 위와 동일 + 카테고리 분류
 *
 * 이미지가 없어도(텍스트만) 동작 → 캡션만 먼저 뽑을 때 유용.
 * 사용: node scripts/build-bundles.js
 */

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const CDIR = join(ROOT, "data", "contents");
const OUT = join(ROOT, "output");
const BUN = join(OUT, "instagram_bundles");
const CAT = join(OUT, "instagram_by_category");

const CAT_DIR = {
  "취업/연봉": "1_취업연봉",
  "재테크/돈": "2_재테크돈",
  "대학/입시": "3_대학입시",
  "심리/관계": "4_심리관계",
  "생활꿀팁": "5_생활꿀팁",
};

// 쓰레드는 주제 태그 1개 권장 (여러 개 = 스팸 판정 → 노출 제한)
function pickTag(c) {
  const id = c.topic_id;
  if (/mbti/i.test(id)) return "#MBTI";
  if (/zodiac/i.test(id)) return "#운세";
  if (/cert|sqld|adsp/i.test(id)) return "#자격증";
  if (/salary|income|bonus|wage/i.test(id)) return "#연봉";
  if (/recruit|interview|hiring|job_priority|civil_public/i.test(id)) return "#취업";
  if (/savings|isa|kpass|credit|rent|100m|subsidy|loan|side_job/i.test(id)) return "#재테크";
  if (/ai_tools|free_sites|hidden_free|laptop|essential_sites|consumption/i.test(id)) return "#꿀팁";
  const map = { "취업/연봉": "#취업", "재테크/돈": "#재테크", "대학/입시": "#대학생", "심리/관계": "#심리", "생활꿀팁": "#꿀팁" };
  return map[c.category] || "#정보";
}

// 답글 유도 질문 — 본문에 이미 질문이 있으면 생략
const QUESTIONS = {
  "취업/연봉": ["여러분 생각은 어때요? 🤔", "본인은 어디쯤인 것 같아요?", "이거 현실적으로 어떻게들 준비해요?"],
  "재테크/돈": ["이거 다들 챙기고 있어요? 👀", "여러분은 이미 하고 있어요?", "이런 거 보면 바로 챙겨야겠죠?"],
  "대학/입시": ["이거 어떻게 생각하세요?", "후배들한테 뭐라고 말해줄래요?", "지금 다시 고른다면 어떻게 할래요?"],
  "심리/관계": ["본인은 어디 해당돼요? 👀", "이거 맞는 것 같아요?", "댓글로 본인 거 알려줘요!"],
  "생활꿀팁": ["이거 알고 있었어요?", "안 쓰면 손해겠죠?", "하나라도 써본 거 있어요?"],
};

function threadsCaption(c, idx) {
  const cap = c.caption || {};
  const body = (cap.body || "").trim();
  const parts = [body];
  if (!/[?？]/.test(body)) {
    const pool = QUESTIONS[c.category] || ["여러분 생각은 어때요?"];
    parts.push(pool[idx % pool.length]);
  }
  let text = parts.join("\n\n") + "\n" + pickTag(c);
  if (text.length > 500) text = text.slice(0, 497) + "..."; // 쓰레드 500자 제한
  return text + "\n";
}

function igCaption(c) {
  const cap = c.caption || {};
  return [
    cap.title || "", "",
    cap.body || "", "",
    cap.cta || "", "",
    cap.source ? "※ " + cap.source : "", "",
    cap.hashtags || "",
  ].filter((l, i, a) => !(l === "" && a[i - 1] === "")).join("\n").trim() + "\n";
}

async function main() {
  await rm(BUN, { recursive: true, force: true });
  await rm(CAT, { recursive: true, force: true });

  const files = (await readdir(CDIR)).filter((f) => f.endsWith(".json")).sort((a, b) => parseInt(a) - parseInt(b));
  let n = 0, withImg = 0;
  const allThreads = [];

  for (let idx = 0; idx < files.length; idx++) {
    const c = JSON.parse(await readFile(join(CDIR, files[idx]), "utf-8"));
    const id = c.topic_id, bt = c.card_type;
    const dir = join(BUN, id);
    await mkdir(dir, { recursive: true });

    // 이미지 (있을 때만)
    const imgs = [
      [`${id}_01_cover.jpg`, "1_표지.jpg"],
      [`${id}_02_${bt}.jpg`, "2_본문.jpg"],
      [`${id}_03_cta.jpg`, "3_cta.jpg"],
    ];
    let copied = 0;
    for (const [src, dst] of imgs) {
      const sp = join(OUT, src);
      if (existsSync(sp)) { await copyFile(sp, join(dir, dst)); copied++; }
    }
    if (copied === 3) withImg++;

    // 캡션
    await writeFile(join(dir, "caption.txt"), igCaption(c), "utf-8");
    const tc = threadsCaption(c, idx);
    await writeFile(join(dir, "threads_caption.txt"), tc, "utf-8");
    allThreads.push(`### ${id} [${c.category}]\n${tc}`);

    // 카테고리 트리로 복사
    const cdir = join(CAT, CAT_DIR[c.category] || "9_기타", id);
    await mkdir(cdir, { recursive: true });
    for (const fn of await readdir(dir)) await copyFile(join(dir, fn), join(cdir, fn));
    n++;
  }

  // 쓰레드 캡션 전체 모음 (빠른 복붙용)
  await writeFile(join(OUT, "threads_captions_all.txt"), allThreads.join("\n"), "utf-8");

  console.log(`번들 생성: ${n}개 (이미지 포함 ${withImg}/${n})`);
  console.log(`  - ${BUN}`);
  console.log(`  - ${CAT}`);
  console.log(`  - ${join(OUT, "threads_captions_all.txt")} (전체 쓰레드 캡션 모음)`);
  if (withImg < n) console.log(`  ※ 이미지 없는 번들 존재 → 'node src/batch.js --from-dir data/contents' 먼저 실행하면 이미지까지 채워집니다.`);
}

main().catch((e) => { console.error("[build-bundles] fatal:", e.message); process.exit(1); });

import Handlebars from "handlebars";
import puppeteer from "puppeteer";
import { readFile, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const TEMPLATE_DIR = join(__dirname, "..", "templates");

const TEMPLATE_FILES = {
  cover: "cover.hbs",
  ranking: "ranking.hbs",
  checklist: "checklist.hbs",
  comparison: "comparison.hbs",
  cta: "cta.hbs",
};

let cachedTemplates = null;

async function loadTemplates() {
  if (cachedTemplates) return cachedTemplates;
  const compiled = {};
  for (const [type, file] of Object.entries(TEMPLATE_FILES)) {
    const src = await readFile(join(TEMPLATE_DIR, file), "utf-8");
    compiled[type] = Handlebars.compile(src, { noEscape: false });
  }
  cachedTemplates = compiled;
  return compiled;
}

function annotateRanking(items) {
  return items.map((item) => ({
    ...item,
    top3: typeof item.rank === "number" && item.rank <= 3,
  }));
}

function buildSlideContext(slide, globals) {
  const ctx = { ...slide, handle: globals.handle };
  if (slide.type === "ranking" && Array.isArray(slide.items)) {
    ctx.items = annotateRanking(slide.items);
  }
  return ctx;
}

function getLaunchOptions() {
  const opts = {
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--font-render-hinting=none"],
  };
  if (process.env.PUPPETEER_EXECUTABLE_PATH) {
    opts.executablePath = process.env.PUPPETEER_EXECUTABLE_PATH;
  }
  return opts;
}

export async function launchRenderer() {
  return puppeteer.launch(getLaunchOptions());
}

export async function renderImages(
  content,
  outputDir,
  { handle, browser: providedBrowser } = {},
) {
  await mkdir(outputDir, { recursive: true });

  const templates = await loadTemplates();
  const globals = { handle: handle ?? process.env.DEFAULT_HANDLE ?? "@알쓸지잡10" };

  const browser = providedBrowser ?? (await puppeteer.launch(getLaunchOptions()));
  const ownsBrowser = !providedBrowser;
  const outputs = [];
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });

    for (const slide of content.slides) {
      const tmpl = templates[slide.type];
      if (!tmpl) {
        throw new Error(`알 수 없는 슬라이드 타입: ${slide.type}`);
      }

      const html = tmpl(buildSlideContext(slide, globals));
      await page.setContent(html, { waitUntil: "networkidle0", timeout: 60000 });

      // Wait for Google Fonts to load before screenshot
      await page.evaluate(() => document.fonts.ready);

      // Auto-shrink marked text so it stays within its line budget (prevents
      // mid-word wrapping on long headlines/titles). Must run after fonts load.
      await page.evaluate(() => {
        for (const el of document.querySelectorAll("[data-autofit]")) {
          const maxLines = Number(el.dataset.autofitLines || 2);
          const minSize = Number(el.dataset.autofitMin || 48);
          const cs = getComputedStyle(el);
          let size = parseFloat(cs.fontSize);
          const lhRatio = parseFloat(cs.lineHeight) / size || 1.2;
          let guard = 60;
          while (guard-- > 0 && size > minSize) {
            const allowed = Math.ceil(size * lhRatio * maxLines) + 2;
            if (el.scrollHeight <= allowed) break;
            size -= 3;
            el.style.fontSize = `${size}px`;
          }
        }
      });

      // Small additional buffer for layout settle
      await new Promise((r) => setTimeout(r, 200));

      const filename = `${content.topic_id}_${String(slide.slide_number).padStart(2, "0")}_${slide.type}.jpg`;
      const path = join(outputDir, filename);
      await page.screenshot({
        path,
        type: "jpeg",
        quality: 92,
        fullPage: false,
        clip: { x: 0, y: 0, width: 1080, height: 1920 },
      });

      console.log(`[render-images] saved ${filename}`);
      outputs.push(path);
    }

    await page.close();
  } finally {
    if (ownsBrowser) await browser.close();
  }

  return outputs;
}

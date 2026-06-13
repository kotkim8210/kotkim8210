const { createCanvas, GlobalFonts, loadImage } = require('@napi-rs/canvas');
const fs = require('fs');
const D = '/tmp/journal';
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo.ttf`, 'NMR');
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo-Bold.ttf`, 'NMB');
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo-ExtraBold.ttf`, 'NMX');

const S = 1000;
const CREAM = '#F6F1E6', PANEL = '#FBF8F1', INK = '#54603F', CTXT = '#F3EEE0';
const BODY = 'rgba(68,74,52,0.95)', SOFT = 'rgba(84,96,63,0.6)';

function P(bg) { const c = createCanvas(S, S); const x = c.getContext('2d'); x.fillStyle = bg; x.fillRect(0, 0, S, S); return { c, x }; }
function frame(x, i, col) { x.strokeStyle = col; x.lineWidth = 2; x.strokeRect(i, i, S - i * 2, S - i * 2); }
function multi(x, text, cx, topY, size, fam, color, lh) {
  x.fillStyle = color; x.textAlign = 'center'; x.textBaseline = 'top';
  text.split('\n').forEach((ln, i) => { x.font = `${size}px "${fam}"`; x.fillText(ln, cx, topY + i * lh + (lh - size) / 2); });
}
function caps(x, text, cx, topY, size, color) {
  x.font = `${size}px "NMR"`; x.fillStyle = color; x.textBaseline = 'top'; x.textAlign = 'left';
  const sp = size * 0.42, ch = [...text]; let t = 0; for (const c of ch) t += x.measureText(c).width + sp; t -= sp;
  let px = cx - t / 2; for (const c of ch) { x.fillText(c, px, topY); px += x.measureText(c).width + sp; }
}
function shot(x, img, cx, topY, w, border) {
  const ix = cx - w / 2, h = w * img.height / img.width;
  x.save(); x.shadowColor = 'rgba(84,96,63,0.22)'; x.shadowBlur = 26; x.shadowOffsetY = 14; x.drawImage(img, ix, topY, w, h); x.restore();
  x.strokeStyle = border || 'rgba(84,96,63,0.35)'; x.lineWidth = 1.5; x.strokeRect(ix, topY, w, h); return h;
}
function leaf(x, len, wid, color) { x.beginPath(); x.moveTo(0, 0); x.quadraticCurveTo(wid, -len * .45, 0, -len); x.quadraticCurveTo(-wid, -len * .45, 0, 0); x.fillStyle = color; x.fill(); }
function sprig(x, cx, topY, scale, color) {
  x.save(); x.translate(cx, topY + 122 * scale); x.scale(scale, scale);
  x.strokeStyle = color; x.lineWidth = 3; x.beginPath(); x.moveTo(0, 0); x.quadraticCurveTo(4, -60, 0, -120); x.stroke();
  for (const [y, sc] of [[-108, .55], [-78, .7], [-46, .82], [-16, .7]]) { x.save(); x.translate(0, y); x.rotate(-.9); x.scale(sc, sc); leaf(x, 52, 17, color); x.restore(); x.save(); x.translate(0, y + 8); x.rotate(.9); x.scale(sc, sc); leaf(x, 52, 17, color); x.restore(); }
  x.fillStyle = color; x.globalAlpha = .85; x.beginPath(); x.arc(-9, -30, 7, 0, 7); x.fill(); x.beginPath(); x.arc(10, -54, 6, 0, 7); x.fill(); x.globalAlpha = 1; x.restore();
}

(async () => {
  const cover = await loadImage(`${D}/01_cover.png`);
  const daily = await loadImage(`${D}/04_daily.png`);
  const log = await loadImage(`${D}/05_log.png`);
  const reading = await loadImage(`${D}/p_reading_ot.png`);

  // T1 — 대표 (clean product hero)
  { const { c, x } = P(CREAM); frame(x, 40, 'rgba(84,96,63,0.28)'); sprig(x, S / 2, 70, .62, INK);
    shot(x, cover, S / 2, 215, 470); multi(x, '자녀를 위해, 매일 한 장', S / 2, 905, 40, 'NMB', INK, 50);
    fs.writeFileSync(`${D}/thumb_1_main.png`, c.toBuffer('image/png')); }

  // T2 — 후킹/benefit (dark band)
  { const { c, x } = P(INK); sprig(x, S / 2, 70, .62, CTXT);
    multi(x, '엄마의 기도는\n아이의 평생을\n바꿉니다', S / 2, 215, 76, 'NMX', CTXT, 104);
    shot(x, cover, S / 2, 600, 250, 'rgba(243,238,224,0.5)');
    fs.writeFileSync(`${D}/thumb_2_hook.png`, c.toBuffer('image/png')); }

  // T3 — 기능(기록)
  { const { c, x } = P(CREAM); caps(x, 'HOW IT WORKS', S / 2, 90, 24, SOFT);
    multi(x, '기도제목부터 응답까지\n기록하는 1년', S / 2, 150, 50, 'NMX', INK, 72);
    shot(x, daily, S / 2, 330, 380);
    fs.writeFileSync(`${D}/thumb_3_feature.png`, c.toBuffer('image/png')); }

  // T4 — 구성 (collage)
  { const { c, x } = P(PANEL); multi(x, '이 한 권에 담긴 것', S / 2, 95, 50, 'NMX', INK, 64);
    multi(x, '자녀를 위한 기도 92편   ·   기도 응답 기록\n성경 통독표 (66권)   ·   약 110페이지', S / 2, 235, 31, 'NMR', BODY, 56);
    const w = 250, gap = 34, total = w * 3 + gap * 2, x0 = (S - total) / 2, ty = 440;
    [daily, log, reading].forEach((im, i) => shot(x, im, x0 + w / 2 + i * (w + gap), ty, w));
    fs.writeFileSync(`${D}/thumb_4_inside.png`, c.toBuffer('image/png')); }

  // T5 — 선물
  { const { c, x } = P(CREAM); frame(x, 40, 'rgba(84,96,63,0.22)'); sprig(x, S / 2, 80, .6, INK);
    multi(x, '믿음의 엄마에게\n드리는 선물', S / 2, 220, 56, 'NMX', INK, 78);
    multi(x, '권사님께  ·  며느리에게  ·  나에게', S / 2, 410, 30, 'NMR', SOFT, 46);
    shot(x, cover, S / 2, 480, 360);
    fs.writeFileSync(`${D}/thumb_5_gift.png`, c.toBuffer('image/png')); }

  console.log('DONE thumbnails 5');
})();

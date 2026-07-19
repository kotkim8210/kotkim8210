const { createCanvas, GlobalFonts, loadImage } = require('@napi-rs/canvas');
const fs = require('fs');
const D = '/tmp/journal';
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo.ttf`, 'NMR');
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo-Bold.ttf`, 'NMB');
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo-ExtraBold.ttf`, 'NMX');

const S = 1000;
const CREAM = '#F4EEDE', PANEL = '#EFE8D6', INK = '#4C5A3C';
const DARK = '#2E3A32', CTXT = '#F3EEDE', STRONG = '#3D4630';

function P(bg) { const c = createCanvas(S, S); const x = c.getContext('2d'); x.fillStyle = bg; x.fillRect(0, 0, S, S); return { c, x }; }
function frame(x, i, col, lw) { x.strokeStyle = col; x.lineWidth = lw || 2.5; x.strokeRect(i, i, S - i * 2, S - i * 2); }
function multi(x, text, cx, topY, size, fam, color, lh) {
  x.fillStyle = color; x.textAlign = 'center'; x.textBaseline = 'top';
  text.split('\n').forEach((ln, i) => { x.font = `${size}px "${fam}"`; x.fillText(ln, cx, topY + i * lh + (lh - size) / 2); });
}
function caps(x, text, cx, topY, size, color) {
  x.font = `${size}px "NMB"`; x.fillStyle = color; x.textBaseline = 'top'; x.textAlign = 'left';
  const sp = size * 0.34, ch = [...text]; let t = 0; for (const c of ch) t += x.measureText(c).width + sp; t -= sp;
  let px = cx - t / 2; for (const c of ch) { x.fillText(c, px, topY); px += x.measureText(c).width + sp; }
}
function brandMark(x, cx, y, size, color) { caps(x, '씨앗과 기도', cx, y, size, color); }
function bullets(x, items, cx, topY, size, lh, color) {
  x.textBaseline = 'top';
  items.forEach((it, i) => {
    const y = topY + i * lh; x.font = `${size}px "NMB"`;
    const tw = x.measureText(it).width;
    x.fillStyle = color; x.beginPath(); x.arc(cx - tw / 2 - 28, y + size / 2 + 4, 7, 0, 7); x.fill();
    x.textAlign = 'center'; x.fillText(it, cx, y);
  });
}
function pill(x, text, cx, topY, size, bg, fg) {
  x.font = `${size}px "NMB"`; const w = x.measureText(text).width, padX = 36, padY = 16, h = size + padY * 2;
  const bx = cx - (w + padX * 2) / 2, bw = w + padX * 2;
  x.fillStyle = bg; x.beginPath(); x.roundRect(bx, topY, bw, h, h / 2); x.fill();
  x.fillStyle = fg; x.textAlign = 'center'; x.textBaseline = 'top'; x.fillText(text, cx, topY + padY);
  return h;
}
function shot(x, img, cx, topY, w, border) {
  const ix = cx - w / 2, h = w * img.height / img.width;
  x.save(); x.shadowColor = 'rgba(40,50,40,0.28)'; x.shadowBlur = 26; x.shadowOffsetY = 13; x.drawImage(img, ix, topY, w, h); x.restore();
  x.strokeStyle = border || 'rgba(76,90,60,0.45)'; x.lineWidth = 2; x.strokeRect(ix, topY, w, h); return h;
}
function leaf(x, len, wid, color) { x.beginPath(); x.moveTo(0, 0); x.quadraticCurveTo(wid, -len * .45, 0, -len); x.quadraticCurveTo(-wid, -len * .45, 0, 0); x.fillStyle = color; x.fill(); }
function sprig(x, cx, topY, scale, color) {
  x.save(); x.translate(cx, topY + 122 * scale); x.scale(scale, scale);
  x.strokeStyle = color; x.lineWidth = 4; x.beginPath(); x.moveTo(0, 0); x.quadraticCurveTo(4, -60, 0, -120); x.stroke();
  for (const [y, sc] of [[-108, .55], [-78, .7], [-46, .82], [-16, .7]]) { x.save(); x.translate(0, y); x.rotate(-.9); x.scale(sc, sc); leaf(x, 52, 17, color); x.restore(); x.save(); x.translate(0, y + 8); x.rotate(.9); x.scale(sc, sc); leaf(x, 52, 17, color); x.restore(); }
  x.fillStyle = color; x.globalAlpha = .9; x.beginPath(); x.arc(-9, -30, 7, 0, 7); x.fill(); x.beginPath(); x.arc(10, -54, 6, 0, 7); x.fill(); x.globalAlpha = 1; x.restore();
}

(async () => {
  const cover = await loadImage(`${D}/01_cover.png`);
  const daily = await loadImage(`${D}/04_daily.png`);
  const log = await loadImage(`${D}/05_log.png`);
  const reading = await loadImage(`${D}/p_reading_ot.png`);

  // T1 — 대표 (product hero; title readable on cover)
  { const { c, x } = P(CREAM); frame(x, 38, 'rgba(76,90,60,0.45)', 3); sprig(x, S / 2, 52, .54, INK);
    shot(x, cover, S / 2, 168, 432);
    multi(x, '자녀를 위해, 매일 한 장', S / 2, 820, 58, 'NMX', INK, 70);
    brandMark(x, S / 2, 922, 24, 'rgba(76,90,60,0.72)');
    fs.writeFileSync(`${D}/thumb_1_main.png`, c.toBuffer('image/png')); }

  // T2 — 후킹 (deep green, all fresh text, no small cover)
  { const { c, x } = P(DARK); frame(x, 34, 'rgba(243,238,222,0.30)', 2);
    sprig(x, S / 2, 92, .66, CTXT);
    multi(x, '엄마의 기도는\n아이의 평생을\n바꿉니다', S / 2, 258, 86, 'NMX', CTXT, 112);
    multi(x, '엄마의 기도 노트', S / 2, 712, 52, 'NMX', CTXT, 64);
    multi(x, '자녀를 위한 기도 저널', S / 2, 800, 30, 'NMB', 'rgba(243,238,222,0.82)', 42);
    brandMark(x, S / 2, 898, 26, 'rgba(243,238,222,0.66)');
    fs.writeFileSync(`${D}/thumb_2_hook.png`, c.toBuffer('image/png')); }

  // T3 — 기능: 큰 리스트로 칸 이름 직접 노출 (읽힘)
  { const { c, x } = P(CREAM); frame(x, 38, 'rgba(76,90,60,0.45)', 3); caps(x, 'HOW IT WORKS', S / 2, 96, 26, INK);
    multi(x, '기도제목부터 응답까지\n기록하는 1년', S / 2, 160, 54, 'NMX', INK, 78);
    bullets(x, ['오늘의 말씀', '자녀를 위한 기도제목', '기도 응답 기록', '오늘의 감사'], S / 2, 430, 42, 88, INK);
    brandMark(x, S / 2, 882, 28, 'rgba(76,90,60,0.72)');
    fs.writeFileSync(`${D}/thumb_3_feature.png`, c.toBuffer('image/png')); }

  // T4 — 구성: 페이지 컷 + 각 컷 아래 큰 캡션
  { const { c, x } = P(PANEL); multi(x, '이 한 권에 담긴 것', S / 2, 84, 58, 'NMX', INK, 72);
    multi(x, '기도 92편 · 응답 기록 · 통독표 · 약 110p', S / 2, 240, 40, 'NMB', STRONG, 56);
    const w = 226, gap = 46, total = w * 3 + gap * 2, x0 = (S - total) / 2, ty = 374;
    const labels = ['자녀 기도', '응답 기록', '성경 통독표'];
    [daily, log, reading].forEach((im, i) => {
      const cx = x0 + w / 2 + i * (w + gap); const h = shot(x, im, cx, ty, w);
      multi(x, labels[i], cx, ty + h + 28, 38, 'NMB', INK, 46);
    });
    brandMark(x, S / 2, 858, 28, 'rgba(76,90,60,0.72)');
    fs.writeFileSync(`${D}/thumb_4_inside.png`, c.toBuffer('image/png')); }

  // T5 — 선물 (cover sized within frame)
  { const { c, x } = P(CREAM); frame(x, 38, 'rgba(76,90,60,0.4)', 3); sprig(x, S / 2, 70, .56, INK);
    multi(x, '믿음의 엄마에게\n드리는 선물', S / 2, 178, 60, 'NMX', INK, 82);
    pill(x, '권사님께 · 며느리에게 · 나에게', S / 2, 358, 36, INK, CTXT);
    shot(x, cover, S / 2, 470, 300);
    brandMark(x, S / 2, 922, 24, 'rgba(76,90,60,0.72)');
    fs.writeFileSync(`${D}/thumb_5_gift.png`, c.toBuffer('image/png')); }

  console.log('DONE thumbnails 5 (v3)');
})();

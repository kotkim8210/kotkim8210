// 인쇄용 컬러 표지 (와이어제본: 앞/뒤 분리). A5 + 도련 3mm.
const { createCanvas, GlobalFonts } = require('@napi-rs/canvas');
const fs = require('fs');
const D = '/tmp/journal';
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo.ttf`, 'NMR');
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo-Bold.ttf`, 'NMB');
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo-ExtraBold.ttf`, 'NMX');

// A5 trim 148x210mm @300dpi = 1748x2480 ; bleed 3mm = 35px each side
const TW = 1748, TH = 2480, BLEED = 35;
const W = TW + BLEED * 2, H = TH + BLEED * 2;   // 1818 x 2550
const CREAM = '#F6F1E6', INK = '#54603F';
const INK_SOFT = 'rgba(84,96,63,0.58)', INK_FAINT = 'rgba(84,96,63,0.32)';
const SAFE = 105; // frame/safe inset from bleed edge (≈70px inside trim)

function page() { const c = createCanvas(W, H); const x = c.getContext('2d'); x.fillStyle = CREAM; x.fillRect(0, 0, W, H); return { c, x }; }
function fit(x, t, maxW, base, fam) { let s = base; do { x.font = `${s}px "${fam}"`; if (x.measureText(t).width <= maxW) break; s -= 2; } while (s > 10); return s; }
function center(x, t, cx, y, px, fam, color) { x.font = `${px}px "${fam}"`; x.fillStyle = color; x.textAlign = 'center'; x.textBaseline = 'alphabetic'; x.fillText(t, cx, y); }
function spaced(x, t, cx, y, px, fam, color, sp) { x.font = `${px}px "${fam}"`; x.fillStyle = color; x.textBaseline = 'alphabetic'; x.textAlign = 'left'; const ch = [...t]; let tot = 0; for (const c of ch) tot += x.measureText(c).width + sp; tot -= sp; let cur = cx - tot / 2; for (const c of ch) { x.fillText(c, cur, y); cur += x.measureText(c).width + sp; } }
function rule(x, x1, y, x2, color, w) { x.strokeStyle = color; x.lineWidth = w || 2; x.beginPath(); x.moveTo(x1, y); x.lineTo(x2, y); x.stroke(); }
function leaf(x, len, wid, color) { x.beginPath(); x.moveTo(0, 0); x.quadraticCurveTo(wid, -len * .45, 0, -len); x.quadraticCurveTo(-wid, -len * .45, 0, 0); x.fillStyle = color; x.fill(); }
function sprig(x, cx, cy, scale, color) { x.save(); x.translate(cx, cy); x.scale(scale, scale); x.strokeStyle = color; x.lineWidth = 3; x.beginPath(); x.moveTo(0, 0); x.quadraticCurveTo(4, -60, 0, -120); x.stroke(); for (const [y, sc] of [[-108, .55], [-78, .7], [-46, .82], [-16, .7]]) { x.save(); x.translate(0, y); x.rotate(-.9); x.scale(sc, sc); leaf(x, 52, 17, color); x.restore(); x.save(); x.translate(0, y + 8); x.rotate(.9); x.scale(sc, sc); leaf(x, 52, 17, color); x.restore(); } x.fillStyle = color; x.globalAlpha = .85; x.beginPath(); x.arc(-9, -30, 7, 0, 7); x.fill(); x.beginPath(); x.arc(10, -54, 6, 0, 7); x.fill(); x.globalAlpha = 1; x.restore(); }
function frame(x) { x.strokeStyle = INK_SOFT; x.lineWidth = 2.5; x.strokeRect(SAFE, SAFE, W - SAFE * 2, H - SAFE * 2); x.strokeStyle = INK_FAINT; x.lineWidth = 1.5; x.strokeRect(SAFE + 14, SAFE + 14, W - (SAFE + 14) * 2, H - (SAFE + 14) * 2); }
const CX = W / 2, O = BLEED; // vertical offset = bleed (content from trim-space + O)

// FRONT
function front() {
  const { c, x } = page(); frame(x);
  spaced(x, 'PRAYER JOURNAL', CX, O + 455, 44, 'NMR', INK_SOFT, 22);
  sprig(x, CX, O + 770, 1.7, INK);
  const t = '엄마의 기도 노트';
  center(x, t, CX, O + 1140, fit(x, t, TW - 400, 168, 'NMX'), 'NMX', INK);
  rule(x, CX - 130, O + 1220, CX + 130, INK_SOFT, 2.5);
  center(x, '자녀를 위한 기도 저널', CX, O + 1335, 84, 'NMB', 'rgba(84,96,63,0.92)');
  center(x, '쉬지 말고 기도하라', CX, O + 2025, 70, 'NMB', INK);
  center(x, '데살로니가전서 5 : 17', CX, O + 2120, 48, 'NMR', INK_SOFT);
  center(x, '씨앗과 기도', CX, O + 2330, 50, 'NMB', INK_SOFT);
  return c;
}
// BACK
function back() {
  const { c, x } = page(); frame(x);
  sprig(x, CX, O + 720, 1.3, INK);
  center(x, '이 한 권에 적힌 기도가', CX, O + 1170, 54, 'NMR', INK);
  center(x, '아이의 평생을 지키기를.', CX, O + 1270, 54, 'NMR', INK);
  rule(x, CX - 70, O + 1360, CX + 70, INK_FAINT, 2);
  center(x, '씨앗과 기도', CX, O + 2120, 58, 'NMB', INK);
  center(x, '엄마의 기도 노트 · 자녀를 위한 기도 저널', CX, O + 2205, 34, 'NMR', INK_SOFT);
  return c;
}
// guide overlay (review only): trim(red) + safe(blue)
function guides(base) {
  const c = createCanvas(W, H); const x = c.getContext('2d'); x.drawImage(base, 0, 0);
  x.setLineDash([18, 12]); x.lineWidth = 3;
  x.strokeStyle = 'rgba(210,60,60,0.9)'; x.strokeRect(BLEED, BLEED, TW, TH);                 // trim
  x.strokeStyle = 'rgba(60,110,210,0.85)'; x.strokeRect(BLEED + 70, BLEED + 70, TW - 140, TH - 140); // safe
  x.setLineDash([]); x.fillStyle = 'rgba(210,60,60,0.95)'; x.font = '30px "NMR"'; x.textAlign = 'left';
  x.fillText('빨강 = 재단선(trim) / 파랑 = 안전선(safe) / 바깥 = 도련(bleed)', BLEED + 80, BLEED + 50);
  return c;
}

const f = front(), b = back();
fs.writeFileSync(`${D}/cover_front_print.png`, f.toBuffer('image/png'));
fs.writeFileSync(`${D}/cover_back_print.png`, b.toBuffer('image/png'));
fs.writeFileSync(`${D}/cover_front_guides.png`, guides(f).toBuffer('image/png'));
console.log('DONE cover ' + W + 'x' + H + ' (trim ' + TW + 'x' + TH + ', bleed ' + BLEED + ')');

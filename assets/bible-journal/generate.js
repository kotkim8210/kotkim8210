const { createCanvas, GlobalFonts } = require('@napi-rs/canvas');
const fs = require('fs');
const PDFDocument = require('pdfkit');

const DIR = '/tmp/journal';
GlobalFonts.registerFromPath(`${DIR}/NanumMyeongjo.ttf`, 'NMR');
GlobalFonts.registerFromPath(`${DIR}/NanumMyeongjo-Bold.ttf`, 'NMB');
GlobalFonts.registerFromPath(`${DIR}/NanumMyeongjo-ExtraBold.ttf`, 'NMX');

// A5 @ 300 DPI
const W = 1748, H = 2480, M = 165;
const CREAM = '#F6F1E6';
const INK = '#54603F';            // deep olive (single print ink)
const INK_SOFT = 'rgba(84,96,63,0.62)';
const INK_FAINT = 'rgba(84,96,63,0.30)';
const INK_RULE  = 'rgba(84,96,63,0.38)';

function newPage() {
  const c = createCanvas(W, H);
  const x = c.getContext('2d');
  x.fillStyle = CREAM; x.fillRect(0, 0, W, H);
  return { c, x };
}
function fit(x, text, maxW, base, fam) {
  let s = base;
  do { x.font = `${s}px "${fam}"`; if (x.measureText(text).width <= maxW) break; s -= 2; } while (s > 10);
  return s;
}
function center(x, text, cx, y, px, fam, color) {
  x.font = `${px}px "${fam}"`; x.fillStyle = color; x.textAlign = 'center'; x.textBaseline = 'alphabetic';
  x.fillText(text, cx, y);
}
function spaced(x, text, cx, y, px, fam, color, sp) {
  x.font = `${px}px "${fam}"`; x.fillStyle = color; x.textBaseline = 'alphabetic'; x.textAlign = 'left';
  const chars = [...text];
  let total = 0; for (const ch of chars) total += x.measureText(ch).width + sp; total -= sp;
  let cur = cx - total / 2;
  for (const ch of chars) { x.fillText(ch, cur, y); cur += x.measureText(ch).width + sp; }
}
function rule(x, x1, y, x2, color, w) { x.strokeStyle = color; x.lineWidth = w || 2; x.beginPath(); x.moveTo(x1, y); x.lineTo(x2, y); x.stroke(); }
function vline(x, x1, y1, y2, color, w) { x.strokeStyle = color; x.lineWidth = w || 1.5; x.beginPath(); x.moveTo(x1, y1); x.lineTo(x1, y2); x.stroke(); }

// elegant olive sprig (vertical), drawn around (cx,cy)
function leaf(x, len, wid, color) {
  x.beginPath(); x.moveTo(0, 0);
  x.quadraticCurveTo(wid, -len * 0.45, 0, -len);
  x.quadraticCurveTo(-wid, -len * 0.45, 0, 0);
  x.fillStyle = color; x.fill();
}
function sprig(x, cx, cy, scale, color, rot = 0) {
  x.save(); x.translate(cx, cy); x.rotate(rot); x.scale(scale, scale);
  // stem
  x.strokeStyle = color; x.lineWidth = 3; x.beginPath(); x.moveTo(0, 0); x.quadraticCurveTo(4, -60, 0, -120); x.stroke();
  const pairs = [[-108, 0.55], [-78, 0.7], [-46, 0.82], [-16, 0.7]];
  for (const [y, sc] of pairs) {
    x.save(); x.translate(0, y); x.rotate(-0.9); x.scale(sc, sc); leaf(x, 52, 17, color); x.restore();
    x.save(); x.translate(0, y + 8); x.rotate(0.9); x.scale(sc, sc); leaf(x, 52, 17, color); x.restore();
  }
  // small olives
  x.fillStyle = color; x.globalAlpha = 0.85;
  x.beginPath(); x.arc(-9, -30, 7, 0, 7); x.fill();
  x.beginPath(); x.arc(10, -54, 6, 0, 7); x.fill();
  x.globalAlpha = 1; x.restore();
}
function frame(x, inset) {
  x.strokeStyle = INK_SOFT; x.lineWidth = 2.5;
  x.strokeRect(inset, inset, W - inset * 2, H - inset * 2);
  x.strokeStyle = INK_FAINT; x.lineWidth = 1.5;
  x.strokeRect(inset + 14, inset + 14, W - (inset + 14) * 2, H - (inset + 14) * 2);
}

const pages = [];

// ---------- PAGE 1: COVER ----------
{
  const { c, x } = newPage();
  frame(x, 70);
  spaced(x, 'PRAYER JOURNAL', W / 2, 455, 44, 'NMR', INK_SOFT, 22);
  sprig(x, W / 2, 770, 1.7, INK);
  const t = '엄마의 기도 노트';
  const ts = fit(x, t, W - M * 2 - 120, 168, 'NMX');
  center(x, t, W / 2, 1140, ts, 'NMX', INK);
  rule(x, W / 2 - 130, 1220, W / 2 + 130, INK_SOFT, 2.5);
  center(x, '자녀를 위한 기도 저널', W / 2, 1335, 84, 'NMB', 'rgba(84,96,63,0.92)');
  center(x, '쉬지 말고 기도하라', W / 2, 2025, 70, 'NMB', INK);
  center(x, '데살로니가전서 5 : 17', W / 2, 2120, 48, 'NMR', INK_SOFT);
  center(x, '씨앗과 기도', W / 2, 2330, 50, 'NMB', INK_SOFT);
  pages.push(c);
}

// ---------- PAGE 2: TITLE / 속표지 ----------
{
  const { c, x } = newPage();
  sprig(x, W / 2, 760, 1.3, INK);
  const t = '엄마의 기도 노트';
  const ts = fit(x, t, W - M * 2 - 200, 150, 'NMX');
  center(x, t, W / 2, 1080, ts, 'NMX', INK);
  rule(x, W / 2 - 90, 1160, W / 2 + 90, INK_FAINT, 2);
  center(x, '자녀를 위한 기도 저널', W / 2, 1255, 52, 'NMR', INK_SOFT);
  center(x, '이 노트는', W / 2, 1700, 40, 'NMR', INK_SOFT);
  rule(x, W / 2 - 320, 1790, W / 2 + 320, INK_FAINT, 2);
  center(x, '의 기도 기록입니다', W / 2, 1890, 40, 'NMR', INK_SOFT);
  pages.push(c);
}

// ---------- PAGE 3: SECTION DIVIDER / 섹션표지 ----------
{
  const { c, x } = newPage();
  frame(x, 90);
  spaced(x, 'SECTION', W / 2, 1010, 32, 'NMR', INK_SOFT, 16);
  center(x, '자녀를 위한 기도', W / 2, 1240, 110, 'NMX', INK);
  rule(x, W / 2 - 110, 1330, W / 2 + 110, INK_SOFT, 2.5);
  sprig(x, W / 2, 1620, 1.5, INK);
  pages.push(c);
}

// ---------- PAGE 4: DAILY PRAYER / 데일리 내지 ----------
{
  const { c, x } = newPage();
  // header
  x.textAlign = 'left';
  x.font = `44px "NMB"`; x.fillStyle = INK; x.fillText('날짜', M, 250);
  rule(x, M + 110, 258, M + 620, INK_RULE, 2);
  x.textAlign = 'right'; x.font = `30px "NMR"`; x.fillStyle = INK_SOFT;
  x.fillText('DAILY  PRAYER', W - M, 250); x.textAlign = 'left';
  rule(x, M, 300, W - M, INK_FAINT, 1.5);

  function section(label, y, lines, gap = 96) {
    x.font = `46px "NMB"`; x.fillStyle = INK; x.textAlign = 'left'; x.fillText(label, M, y);
    for (let i = 0; i < lines; i++) rule(x, M, y + 70 + i * gap, W - M, INK_FAINT, 1.6);
    return y + 70 + lines * gap;
  }
  let y = 430;
  y = section('오늘의 말씀', y, 3) + 70;
  y = section('자녀를 위한 기도제목', y, 4) + 70;
  y = section('기도 응답 기록', y, 3) + 70;
  y = section('오늘의 감사', y, 2) + 40;
  sprig(x, W - M - 30, H - 150, 1.0, INK, 0.15);
  pages.push(c);
}

// ---------- PAGE 5: PRAYER-ANSWER LOG / 기도 응답 기록 ----------
{
  const { c, x } = newPage();
  center(x, '기도 응답 기록', W / 2, 280, 78, 'NMX', INK);
  spaced(x, 'ANSWERED PRAYERS', W / 2, 345, 28, 'NMR', INK_SOFT, 12);
  const top = 470, bottom = H - 230, left = M, right = W - M;
  const c1 = left + 230, c2 = left + 760; // column separators
  // outer + header
  x.strokeStyle = INK_SOFT; x.lineWidth = 2.5; x.strokeRect(left, top, right - left, bottom - top);
  const headH = 110;
  rule(x, left, top + headH, right, INK_SOFT, 2.5);
  x.textAlign = 'center'; x.font = `40px "NMB"`; x.fillStyle = INK;
  x.fillText('날짜', (left + c1) / 2, top + 70);
  x.fillText('기도제목', (c1 + c2) / 2, top + 70);
  x.fillText('응답하심', (c2 + right) / 2, top + 70);
  // columns
  vline(x, c1, top, bottom, INK_FAINT, 1.5); vline(x, c2, top, bottom, INK_FAINT, 1.5);
  // rows
  const rows = 11; const rh = (bottom - (top + headH)) / rows;
  for (let i = 1; i < rows; i++) rule(x, left, top + headH + i * rh, right, INK_FAINT, 1.4);
  sprig(x, W / 2, H - 130, 0.8, INK);
  pages.push(c);
}

// export PNGs
const names = ['01_cover', '02_title', '03_section', '04_daily', '05_log'];
pages.forEach((c, i) => fs.writeFileSync(`${DIR}/${names[i]}.png`, c.toBuffer('image/png')));

// build print-ready A5 PDF
const doc = new PDFDocument({ size: 'A5', margin: 0 });
const out = fs.createWriteStream(`${DIR}/엄마의_기도_노트_내지.pdf`);
doc.pipe(out);
const A5W = 419.528, A5H = 595.276;
pages.forEach((c, i) => { if (i) doc.addPage({ size: 'A5', margin: 0 }); doc.image(`${DIR}/${names[i]}.png`, 0, 0, { width: A5W, height: A5H }); });
doc.end();
out.on('finish', () => console.log('DONE pages=' + pages.length));

const { createCanvas, GlobalFonts } = require('@napi-rs/canvas');
const fs = require('fs');
const D = '/tmp/journal';
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo.ttf`, 'NMR');
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo-Bold.ttf`, 'NMB');
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo-ExtraBold.ttf`, 'NMX');

const GREEN = '#2E3A32', CREAM = '#F6F1E6', CTXT = '#F3EEDE';
const SOFT_D = 'rgba(46,58,50,0.55)', SOFT_C = 'rgba(243,238,222,0.7)';

function leaf(x, len, wid, color) { x.beginPath(); x.moveTo(0, 0); x.quadraticCurveTo(wid, -len * .45, 0, -len); x.quadraticCurveTo(-wid, -len * .45, 0, 0); x.fillStyle = color; x.fill(); }
// "seed + sprout" mark: a seed at base, stem, two opening leaves
function sprout(x, cx, baseY, scale, color) {
  x.save(); x.translate(cx, baseY); x.scale(scale, scale);
  // seed (almond at base)
  x.save(); x.rotate(0.0); x.fillStyle = color; x.beginPath(); x.ellipse(0, 6, 17, 9, 0, 0, 7); x.fill(); x.restore();
  // stem
  x.strokeStyle = color; x.lineWidth = 6; x.lineCap = 'round'; x.beginPath(); x.moveTo(0, 2); x.quadraticCurveTo(2, -55, 0, -112); x.stroke();
  // two leaves near top
  x.save(); x.translate(0, -104); x.rotate(-0.62); leaf(x, 70, 26, color); x.restore();
  x.save(); x.translate(0, -104); x.rotate(0.62); leaf(x, 70, 26, color); x.restore();
  x.restore();
}
function textC(x, t, cx, topY, size, fam, color) { x.font = `${size}px "${fam}"`; x.fillStyle = color; x.textAlign = 'center'; x.textBaseline = 'top'; x.fillText(t, cx, topY); }
function measure(x, t, size, fam) { x.font = `${size}px "${fam}"`; return x.measureText(t).width; }

// 1) STACKED (transparent) — symbol over name + tagline
{ const c = createCanvas(900, 1020); const x = c.getContext('2d');
  sprout(x, 450, 360, 2.4, GREEN);
  textC(x, '씨앗과 기도', 450, 470, 150, 'NMX', GREEN);
  textC(x, '엄마의 기도 노트', 450, 660, 52, 'NMB', SOFT_D);
  fs.writeFileSync(`${D}/logo_stacked.png`, c.toBuffer('image/png')); }

// 2) PRIMARY (transparent) — horizontal lockup
{ const c = createCanvas(1320, 430); const x = c.getContext('2d');
  const tw = measure(x, '씨앗과 기도', 150, 'NMX');
  const iconW = 150, gap = 64, total = iconW + gap + tw, sx = (1320 - total) / 2;
  sprout(x, sx + iconW / 2, 300, 1.9, GREEN);
  x.font = '150px "NMX"'; x.fillStyle = GREEN; x.textAlign = 'left'; x.textBaseline = 'top';
  x.fillText('씨앗과 기도', sx + iconW + gap, 138);
  fs.writeFileSync(`${D}/logo_primary.png`, c.toBuffer('image/png')); }

// 3) PROFILE — cream bg (square 1000)
{ const c = createCanvas(1000, 1000); const x = c.getContext('2d'); x.fillStyle = CREAM; x.fillRect(0, 0, 1000, 1000);
  x.strokeStyle = 'rgba(46,58,50,0.28)'; x.lineWidth = 6; x.beginPath(); x.arc(500, 500, 430, 0, 7); x.stroke();
  sprout(x, 500, 530, 1.7, GREEN);
  textC(x, '씨앗과 기도', 500, 585, 112, 'NMX', GREEN);
  textC(x, '엄마의 기도 노트', 500, 724, 40, 'NMB', SOFT_D);
  fs.writeFileSync(`${D}/logo_profile_cream.png`, c.toBuffer('image/png')); }

// 4) PROFILE — deep green bg (square 1000)
{ const c = createCanvas(1000, 1000); const x = c.getContext('2d'); x.fillStyle = GREEN; x.fillRect(0, 0, 1000, 1000);
  x.strokeStyle = 'rgba(243,238,222,0.32)'; x.lineWidth = 6; x.beginPath(); x.arc(500, 500, 430, 0, 7); x.stroke();
  sprout(x, 500, 530, 1.7, CTXT);
  textC(x, '씨앗과 기도', 500, 585, 112, 'NMX', CTXT);
  textC(x, '엄마의 기도 노트', 500, 724, 40, 'NMB', SOFT_C);
  fs.writeFileSync(`${D}/logo_profile_green.png`, c.toBuffer('image/png')); }

console.log('DONE logos 4');

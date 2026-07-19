const { createCanvas, GlobalFonts, loadImage } = require('@napi-rs/canvas');
const fs = require('fs');
const D = '/tmp/journal';
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo.ttf`, 'NMR');
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo-Bold.ttf`, 'NMB');
GlobalFonts.registerFromPath(`${D}/NanumMyeongjo-ExtraBold.ttf`, 'NMX');

const W = 1080, PAD = 120;
const CREAM = '#F6F1E6', PANEL = '#FBF8F1', INK = '#54603F', CTXT = '#F3EEE0';
const DARK = '#2E3A32';  // deep green (brand-consistent with thumbnails)
const BODY = 'rgba(68,74,52,0.95)', SOFT = 'rgba(84,96,63,0.62)';

let ctx; // active context (set per pass)

function wrap(text, font, maxW) {
  ctx.font = font;
  const out = [];
  for (const para of text.split('\n')) {
    let cur = '';
    for (const ch of [...para]) {
      if (cur && ctx.measureText(cur + ch).width > maxW) { out.push(cur); cur = ch; }
      else cur += ch;
    }
    out.push(cur);
  }
  return out;
}
function fontOf(el) { const fam = el.t === 'h' ? 'NMX' : 'NMR'; return `${el.size}px "${fam}"`; }
function maxWOf(el) { return el.maxW || (el.t === 'h' ? W - 300 : W - PAD * 2); }

function measureEl(el) {
  switch (el.t) {
    case 'label': return Math.round(el.size * 1.8);
    case 'rule': return 70;
    case 'gap': return el.h;
    case 'sprig': return Math.round(130 * (el.scale || 1));
    case 'img': return el.w * el.img.height / el.img.width;
    case 'h': case 'body': return wrap(el.text, fontOf(el), maxWOf(el)).length * el.lh;
  }
  return 0;
}

function leaf(len, wid, color) { ctx.beginPath(); ctx.moveTo(0, 0); ctx.quadraticCurveTo(wid, -len * .45, 0, -len); ctx.quadraticCurveTo(-wid, -len * .45, 0, 0); ctx.fillStyle = color; ctx.fill(); }
function sprig(cx, topY, scale, color) {
  const cy = topY + 125 * scale;
  ctx.save(); ctx.translate(cx, cy); ctx.scale(scale, scale);
  ctx.strokeStyle = color; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(0, 0); ctx.quadraticCurveTo(4, -60, 0, -120); ctx.stroke();
  for (const [y, sc] of [[-108, .55], [-78, .7], [-46, .82], [-16, .7]]) {
    ctx.save(); ctx.translate(0, y); ctx.rotate(-.9); ctx.scale(sc, sc); leaf(52, 17, color); ctx.restore();
    ctx.save(); ctx.translate(0, y + 8); ctx.rotate(.9); ctx.scale(sc, sc); leaf(52, 17, color); ctx.restore();
  }
  ctx.fillStyle = color; ctx.globalAlpha = .85; ctx.beginPath(); ctx.arc(-9, -30, 7, 0, 7); ctx.fill(); ctx.beginPath(); ctx.arc(10, -54, 6, 0, 7); ctx.fill(); ctx.globalAlpha = 1; ctx.restore();
}
function spacedCaps(text, cx, topY, size, color) {
  ctx.font = `${size}px "NMR"`; ctx.fillStyle = color; ctx.textBaseline = 'top'; ctx.textAlign = 'left';
  const sp = size * 0.42, chars = [...text];
  let tot = 0; for (const c of chars) tot += ctx.measureText(c).width + sp; tot -= sp;
  let x = cx - tot / 2; for (const c of chars) { ctx.fillText(c, x, topY); x += ctx.measureText(c).width + sp; }
}
function drawEl(el, y, C) {
  const cx = W / 2;
  switch (el.t) {
    case 'label': spacedCaps(el.text, cx, y + el.size * 0.3, el.size, el.color || C.label); break;
    case 'sprig': sprig(cx, y, el.scale || 1, el.color || INK); break;
    case 'rule': ctx.strokeStyle = el.color || C.soft; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(cx - 70, y + 35); ctx.lineTo(cx + 70, y + 35); ctx.stroke(); break;
    case 'gap': break;
    case 'h': case 'body': {
      ctx.font = fontOf(el); ctx.fillStyle = el.color || (el.t === 'h' ? C.head : C.body); ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      const lines = wrap(el.text, fontOf(el), maxWOf(el));
      lines.forEach((ln, i) => ctx.fillText(ln, cx, y + i * el.lh + (el.lh - el.size) / 2));
      break;
    }
    case 'img': {
      const x = (W - el.w) / 2, h = el.w * el.img.height / el.img.width;
      ctx.save(); ctx.shadowColor = 'rgba(84,96,63,0.20)'; ctx.shadowBlur = 30; ctx.shadowOffsetY = 16; ctx.drawImage(el.img, x, y, el.w, h); ctx.restore();
      ctx.strokeStyle = 'rgba(84,96,63,0.35)'; ctx.lineWidth = 1.5; ctx.strokeRect(x, y, el.w, h);
      break;
    }
  }
}

let Y = 0;
const sectionLog = [];
function section(bg, els, padTop = 95, padBottom = 95) {
  let inner = 0; for (const el of els) inner += measureEl(el);
  const h = padTop + inner + padBottom;
  ctx.fillStyle = bg; ctx.fillRect(0, Y, W, h);
  const C = (bg === INK || bg === DARK)
    ? { head: CTXT, body: 'rgba(243,238,224,0.88)', label: 'rgba(243,238,224,0.7)', soft: 'rgba(243,238,224,0.5)' }
    : { head: INK, body: BODY, label: SOFT, soft: SOFT };
  let cy = Y + padTop;
  for (const el of els) { drawEl(el, cy, C); cy += measureEl(el); }
  Y += h; sectionLog.push(h); return h;
}

(async () => {
  const cover = await loadImage(`${D}/01_cover.png`);
  const daily = await loadImage(`${D}/04_daily.png`);
  const log = await loadImage(`${D}/05_log.png`);
  const reading = await loadImage(`${D}/p_reading_ot.png`);
  const children = await loadImage(`${D}/p_children.png`);

  const big = createCanvas(W, 14000); ctx = big.getContext('2d');
  ctx.fillStyle = CREAM; ctx.fillRect(0, 0, W, 14000);

  // HERO
  const heroH = section(CREAM, [
    { t: 'label', text: 'A PRAYER JOURNAL FOR MOM', size: 24 },
    { t: 'gap', h: 26 }, { t: 'sprig', scale: 1.05 }, { t: 'gap', h: 30 },
    { t: 'h', text: '엄마의 잔소리는 하루를 바꾸지만,\n엄마의 기도는 아이의 평생을 바꿉니다.', size: 50, lh: 78, maxW: W - 180 },
    { t: 'gap', h: 28 },
    { t: 'body', text: '오늘 드린 기도, 기록하지 않으면 사라집니다.', size: 30, lh: 46, color: SOFT },
    { t: 'gap', h: 56 }, { t: 'img', img: cover, w: 560 },
  ], 120, 100);

  // EMPATHY
  section(PANEL, [
    { t: 'label', text: 'WHY THIS JOURNAL', size: 23 }, { t: 'gap', h: 30 },
    { t: 'h', text: '우리는 매일 기도하지만,\n어디에도 남기지 않습니다.', size: 44, lh: 66 }, { t: 'gap', h: 34 },
    { t: 'body', text: '등굣길에, 설거지하다, 잠든 얼굴을 보며 —\n우리는 늘 아이를 위해 기도합니다.\n하지만 그 기도를 적어두지 않으면,\n응답이 와도 그게 응답인 줄 모르고 지나갑니다.', size: 32, lh: 56 },
  ]);

  // SOLUTION
  section(CREAM, [
    { t: 'sprig', scale: .8 }, { t: 'gap', h: 22 },
    { t: 'body', text: '그래서 만들었습니다.', size: 34, lh: 50, color: SOFT }, { t: 'gap', h: 14 },
    { t: 'h', text: '엄마의 기도 노트', size: 62, lh: 84 }, { t: 'gap', h: 24 },
    { t: 'body', text: '매일 한 장, 아이의 이름을 부르며 기도하고\n그 기도가 응답으로 채워지는 1년.', size: 32, lh: 56 },
  ]);

  // FEATURES HEADER
  section(DARK, [
    { t: 'label', text: 'HOW IT WORKS', size: 23 }, { t: 'gap', h: 18 },
    { t: 'h', text: '이렇게 채워갑니다', size: 46, lh: 64 },
  ], 70, 70);

  // FEATURE 1
  section(CREAM, [
    { t: 'h', text: '하루 한 장, 자녀를 위한 기도', size: 40, lh: 58 }, { t: 'gap', h: 22 },
    { t: 'body', text: '오늘의 말씀 · 기도제목 · 응답 · 감사로 나뉘어\n막막하지 않게, 더 깊이 기도할 수 있어요.', size: 31, lh: 52 },
    { t: 'gap', h: 46 }, { t: 'img', img: daily, w: 470 },
  ]);
  // FEATURE 2
  section(PANEL, [
    { t: 'h', text: '기도가 간증이 되는 자리', size: 40, lh: 58 }, { t: 'gap', h: 22 },
    { t: 'body', text: '응답된 기도를 따로 적어두면,\n1년 뒤 그 페이지가\n하나님이 일하신 증거가 됩니다.', size: 31, lh: 52 },
    { t: 'gap', h: 46 }, { t: 'img', img: log, w: 470 },
  ]);
  // FEATURE 3
  section(CREAM, [
    { t: 'h', text: '말씀과 함께 가는 1년', size: 40, lh: 58 }, { t: 'gap', h: 22 },
    { t: 'body', text: '성경 66권을 한 칸씩 채우며\n기도와 말씀이 같이 자라요.', size: 31, lh: 52 },
    { t: 'gap', h: 46 }, { t: 'img', img: reading, w: 470 },
  ]);
  // FEATURE 4
  section(PANEL, [
    { t: 'h', text: '우리 아이를 위한 첫 장', size: 40, lh: 58 }, { t: 'gap', h: 22 },
    { t: 'body', text: '아이의 이름과 기도 키워드로 시작하는\n세상에 하나뿐인 기도 노트.', size: 31, lh: 52 },
    { t: 'gap', h: 46 }, { t: 'img', img: children, w: 470 },
  ]);

  // PAPER REASON (band)
  section(DARK, [
    { t: 'label', text: 'WHY ON PAPER', size: 23 }, { t: 'gap', h: 18 },
    { t: 'h', text: '왜 손으로 적어야 할까요?', size: 44, lh: 64 }, { t: 'gap', h: 28 },
    { t: 'body', text: '앱은 알림을 주지만, 손글씨는 마음을 남깁니다.\n크림빛 종이 위에 아이의 이름을 또박또박 적는\n그 시간이, 가장 깊은 기도가 됩니다.', size: 32, lh: 58 },
  ]);

  // SPEC
  section(CREAM, [
    { t: 'label', text: 'PRODUCT', size: 23 }, { t: 'gap', h: 20 },
    { t: 'h', text: '구성과 사양', size: 40, lh: 58 }, { t: 'gap', h: 16 }, { t: 'rule' }, { t: 'gap', h: 30 },
    { t: 'body', text: '판형   ·   A5 (148 × 210 mm)\n분량   ·   약 110 페이지\n내지   ·   크림 종이 + 올리브 1도 인쇄\n제본   ·   와이어링 (평평하게 펼쳐짐)', size: 31, lh: 58 },
    { t: 'gap', h: 30 }, { t: 'rule' }, { t: 'gap', h: 28 },
    { t: 'body', text: '표지 · 헌사 · 자녀 인덱스\n자녀를 위한 기도 92편\n기도 응답 기록 · 성경 통독표 · 연말 회고', size: 29, lh: 52, color: SOFT },
  ]);

  // GIFT
  section(PANEL, [
    { t: 'sprig', scale: .8 }, { t: 'gap', h: 16 },
    { t: 'h', text: '믿음의 엄마에게 드리는 선물', size: 40, lh: 58 }, { t: 'gap', h: 24 },
    { t: 'body', text: '권사님께, 며느리에게, 그리고 나 자신에게 —\n기도라는, 가장 오래 남는 선물.', size: 31, lh: 52 },
  ]);

  // FINAL CTA (band)
  section(DARK, [
    { t: 'sprig', scale: 1.0, color: CTXT }, { t: 'gap', h: 26 },
    { t: 'h', text: '오늘부터,\n아이를 위한 기도를 남기세요.', size: 48, lh: 72 }, { t: 'gap', h: 30 },
    { t: 'h', text: '엄마의 기도 노트', size: 40, lh: 56 }, { t: 'gap', h: 22 },
    { t: 'body', text: '쉬지 말고 기도하라 — 데살로니가전서 5 : 17', size: 27, lh: 44, color: 'rgba(243,238,224,0.72)' },
    { t: 'gap', h: 34 },
    { t: 'body', text: '첫 제작은 한정 수량으로 준비됩니다.', size: 30, lh: 48 },
    { t: 'gap', h: 44 },
    { t: 'body', text: '씨앗과 기도', size: 36, lh: 50, color: CTXT },
  ], 100, 110);

  // trim
  const out = createCanvas(W, Y); const o = out.getContext('2d'); o.drawImage(big, 0, 0);
  fs.writeFileSync(`${D}/detail_full.png`, out.toBuffer('image/png'));
  // hero standalone
  const hero = createCanvas(W, heroH); hero.getContext('2d').drawImage(big, 0, 0);
  fs.writeFileSync(`${D}/detail_hero.png`, hero.toBuffer('image/png'));
  // slice into upload-ready parts (cut only at section boundaries → no text cut)
  const b = [0]; for (const h of sectionLog) b.push(b[b.length - 1] + h);
  const chunks = [[0, 0], [1, 2], [3, 5], [6, 7], [8, 9], [10, 11]];
  chunks.forEach((ch, i) => {
    const y0 = Math.round(b[ch[0]]), y1 = Math.round(b[ch[1] + 1]), h = y1 - y0;
    const part = createCanvas(W, h); part.getContext('2d').drawImage(big, 0, y0, W, h, 0, 0, W, h);
    fs.writeFileSync(`${D}/detail_part_${i + 1}.png`, part.toBuffer('image/png'));
  });
  console.log('DONE  totalH=' + Y + '  heroH=' + heroH + '  sections=' + sectionLog.length + '  parts=' + chunks.length);
})();

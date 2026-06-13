const { createCanvas, GlobalFonts } = require('@napi-rs/canvas');
const fs = require('fs');
const PDFDocument = require('pdfkit');

const DIR = '/tmp/journal';
GlobalFonts.registerFromPath(`${DIR}/NanumMyeongjo.ttf`, 'NMR');
GlobalFonts.registerFromPath(`${DIR}/NanumMyeongjo-Bold.ttf`, 'NMB');
GlobalFonts.registerFromPath(`${DIR}/NanumMyeongjo-ExtraBold.ttf`, 'NMX');

const W = 1748, H = 2480, M = 165;
const CREAM = '#F6F1E6', INK = '#54603F';
const INK_SOFT = 'rgba(84,96,63,0.62)', INK_FAINT = 'rgba(84,96,63,0.30)', INK_RULE = 'rgba(84,96,63,0.38)';

function page() { const c = createCanvas(W, H); const x = c.getContext('2d'); x.fillStyle = CREAM; x.fillRect(0, 0, W, H); return { c, x }; }
function fit(x, t, maxW, base, fam) { let s = base; do { x.font = `${s}px "${fam}"`; if (x.measureText(t).width <= maxW) break; s -= 2; } while (s > 10); return s; }
function center(x, t, cx, y, px, fam, color) { x.font = `${px}px "${fam}"`; x.fillStyle = color; x.textAlign = 'center'; x.textBaseline = 'alphabetic'; x.fillText(t, cx, y); }
function left(x, t, lx, y, px, fam, color) { x.font = `${px}px "${fam}"`; x.fillStyle = color; x.textAlign = 'left'; x.textBaseline = 'alphabetic'; x.fillText(t, lx, y); }
function spaced(x, t, cx, y, px, fam, color, sp) { x.font = `${px}px "${fam}"`; x.fillStyle = color; x.textBaseline = 'alphabetic'; x.textAlign = 'left'; const ch = [...t]; let tot = 0; for (const c of ch) tot += x.measureText(c).width + sp; tot -= sp; let cur = cx - tot / 2; for (const c of ch) { x.fillText(c, cur, y); cur += x.measureText(c).width + sp; } }
function rule(x, x1, y, x2, color, w) { x.strokeStyle = color; x.lineWidth = w || 2; x.beginPath(); x.moveTo(x1, y); x.lineTo(x2, y); x.stroke(); }
function vline(x, x1, y1, y2, color, w) { x.strokeStyle = color; x.lineWidth = w || 1.5; x.beginPath(); x.moveTo(x1, y1); x.lineTo(x1, y2); x.stroke(); }
function wrap(x, t, maxW, px, fam) { x.font = `${px}px "${fam}"`; const words = t.split(' '); const lines = []; let cur = ''; for (const w of words) { const tr = cur ? cur + ' ' + w : w; if (x.measureText(tr).width > maxW && cur) { lines.push(cur); cur = w; } else cur = tr; } if (cur) lines.push(cur); return lines; }
function leaf(x, len, wid, color) { x.beginPath(); x.moveTo(0, 0); x.quadraticCurveTo(wid, -len * 0.45, 0, -len); x.quadraticCurveTo(-wid, -len * 0.45, 0, 0); x.fillStyle = color; x.fill(); }
function sprig(x, cx, cy, scale, color, rot = 0) { x.save(); x.translate(cx, cy); x.rotate(rot); x.scale(scale, scale); x.strokeStyle = color; x.lineWidth = 3; x.beginPath(); x.moveTo(0, 0); x.quadraticCurveTo(4, -60, 0, -120); x.stroke(); const pairs = [[-108, .55], [-78, .7], [-46, .82], [-16, .7]]; for (const [y, sc] of pairs) { x.save(); x.translate(0, y); x.rotate(-.9); x.scale(sc, sc); leaf(x, 52, 17, color); x.restore(); x.save(); x.translate(0, y + 8); x.rotate(.9); x.scale(sc, sc); leaf(x, 52, 17, color); x.restore(); } x.fillStyle = color; x.globalAlpha = .85; x.beginPath(); x.arc(-9, -30, 7, 0, 7); x.fill(); x.beginPath(); x.arc(10, -54, 6, 0, 7); x.fill(); x.globalAlpha = 1; x.restore(); }
function frame(x, i) { x.strokeStyle = INK_SOFT; x.lineWidth = 2.5; x.strokeRect(i, i, W - i * 2, H - i * 2); x.strokeStyle = INK_FAINT; x.lineWidth = 1.5; x.strokeRect(i + 14, i + 14, W - (i + 14) * 2, H - (i + 14) * 2); }
function checkbox(x, bx, by, s) { x.strokeStyle = INK_SOFT; x.lineWidth = 2; x.strokeRect(bx, by, s, s); }

// ---------- renderers ----------
function rCover() { const { c, x } = page(); frame(x, 70); spaced(x, 'PRAYER JOURNAL', W / 2, 455, 44, 'NMR', INK_SOFT, 22); sprig(x, W / 2, 770, 1.7, INK); const t = '엄마의 기도 노트'; center(x, t, W / 2, 1140, fit(x, t, W - M * 2 - 120, 168, 'NMX'), 'NMX', INK); rule(x, W / 2 - 130, 1220, W / 2 + 130, INK_SOFT, 2.5); center(x, '자녀를 위한 기도 저널', W / 2, 1335, 84, 'NMB', 'rgba(84,96,63,0.92)'); center(x, '쉬지 말고 기도하라', W / 2, 2025, 70, 'NMB', INK); center(x, '데살로니가전서 5 : 17', W / 2, 2120, 48, 'NMR', INK_SOFT); center(x, '씨앗과 기도', W / 2, 2330, 50, 'NMB', INK_SOFT); return c; }
function rTitle() { const { c, x } = page(); sprig(x, W / 2, 760, 1.3, INK); const t = '엄마의 기도 노트'; center(x, t, W / 2, 1080, fit(x, t, W - M * 2 - 200, 150, 'NMX'), 'NMX', INK); rule(x, W / 2 - 90, 1160, W / 2 + 90, INK_FAINT, 2); center(x, '자녀를 위한 기도 저널', W / 2, 1255, 52, 'NMR', INK_SOFT); center(x, '이 노트는', W / 2, 1700, 40, 'NMR', INK_SOFT); rule(x, W / 2 - 320, 1790, W / 2 + 320, INK_FAINT, 2); center(x, '의 기도 기록입니다', W / 2, 1890, 40, 'NMR', INK_SOFT); return c; }
function rHowTo() { const { c, x } = page(); spaced(x, 'HOW TO USE', W / 2, 320, 30, 'NMR', INK_SOFT, 14); center(x, '이 노트를 시작하며', W / 2, 430, 68, 'NMX', INK); rule(x, W / 2 - 90, 500, W / 2 + 90, INK_FAINT, 2); const intro = '하루 한 장, 자녀의 이름을 부르며 기도하는 자리입니다. 잘 쓰려 애쓰지 마세요. 그저 마음을 그대로 적으면, 그 페이지가 훗날 응답의 간증이 됩니다.'; let y = 640; for (const ln of wrap(x, intro, W - M * 2, 42, 'NMR')) { center(x, ln, W / 2, y, 42, 'NMR', INK); y += 70; } y += 60; const steps = ['1.  날짜와 오늘의 말씀을 적습니다.', '2.  자녀를 위한 기도제목을 구체적으로 적습니다.', '3.  떠오른 마음·응답을 기록합니다.', '4.  응답된 기도는 「기도 응답 기록」에 옮겨 적어', '      한 해의 간증으로 남깁니다.', '5.  말씀을 읽으며 「성경 통독표」를 채워갑니다.']; for (const s of steps) { left(x, s, M + 40, y, 44, 'NMR', INK); y += 96; } sprig(x, W - M - 30, H - 150, 1.0, INK, .15); return c; }
function rOwner() { const { c, x } = page(); frame(x, 90); center(x, '이 기도 노트의 주인', W / 2, 560, 70, 'NMX', INK); sprig(x, W / 2, 760, 1.0, INK); left(x, '이름', M + 120, 1080, 46, 'NMB', INK); rule(x, M + 360, 1090, W - M - 120, INK_RULE, 2); left(x, '시작한 날', M + 120, 1260, 46, 'NMB', INK); rule(x, M + 360, 1270, W - M - 120, INK_RULE, 2); center(x, '사랑하는 나의 자녀를 위하여', W / 2, 1560, 48, 'NMR', INK_SOFT); center(x, '네 자녀를 여호와의 교양과 훈계로 양육하라', W / 2, 1980, 42, 'NMR', INK); center(x, '에베소서 6 : 4', W / 2, 2050, 34, 'NMR', INK_SOFT); return c; }
function rChildren() { const { c, x } = page(); spaced(x, 'OUR CHILDREN', W / 2, 300, 30, 'NMR', INK_SOFT, 14); center(x, '우리 아이들', W / 2, 410, 66, 'NMX', INK); rule(x, W / 2 - 80, 478, W / 2 + 80, INK_FAINT, 2); let y = 640; for (let i = 0; i < 3; i++) { left(x, '이름', M, y, 42, 'NMB', INK); rule(x, M + 150, y + 8, M + 620, INK_RULE, 2); left(x, '생일', M + 700, y, 42, 'NMB', INK); rule(x, M + 850, y + 8, W - M, INK_RULE, 2); left(x, '기도 키워드', M, y + 120, 38, 'NMR', INK_SOFT); rule(x, M, y + 200, W - M, INK_FAINT, 1.6); rule(x, M, y + 290, W - M, INK_FAINT, 1.6); y += 430; } return c; }
function rSection(title) { const { c, x } = page(); frame(x, 90); spaced(x, 'SECTION', W / 2, 1010, 32, 'NMR', INK_SOFT, 16); center(x, title, W / 2, 1240, fit(x, title, W - M * 2 - 100, 110, 'NMX'), 'NMX', INK); rule(x, W / 2 - 110, 1330, W / 2 + 110, INK_SOFT, 2.5); sprig(x, W / 2, 1620, 1.5, INK); return c; }
function rDaily() { const { c, x } = page(); left(x, '날짜', M, 250, 44, 'NMB', INK); rule(x, M + 110, 258, M + 620, INK_RULE, 2); x.textAlign = 'right'; x.font = '30px "NMR"'; x.fillStyle = INK_SOFT; x.fillText('DAILY  PRAYER', W - M, 250); x.textAlign = 'left'; rule(x, M, 300, W - M, INK_FAINT, 1.5); function sec(label, y, lines, gap = 96) { left(x, label, M, y, 46, 'NMB', INK); for (let i = 0; i < lines; i++) rule(x, M, y + 70 + i * gap, W - M, INK_FAINT, 1.6); return y + 70 + lines * gap; } let y = 430; y = sec('오늘의 말씀', y, 3) + 70; y = sec('자녀를 위한 기도제목', y, 4) + 70; y = sec('기도 응답 기록', y, 3) + 70; y = sec('오늘의 감사', y, 2) + 40; sprig(x, W - M - 30, H - 150, 1.0, INK, .15); return c; }
function rLog() { const { c, x } = page(); center(x, '기도 응답 기록', W / 2, 280, 78, 'NMX', INK); spaced(x, 'ANSWERED PRAYERS', W / 2, 345, 28, 'NMR', INK_SOFT, 12); const top = 470, bot = H - 230, l = M, r = W - M, c1 = l + 230, c2 = l + 760, hH = 110; x.strokeStyle = INK_SOFT; x.lineWidth = 2.5; x.strokeRect(l, top, r - l, bot - top); rule(x, l, top + hH, r, INK_SOFT, 2.5); center(x, '날짜', (l + c1) / 2, top + 70, 40, 'NMB', INK); center(x, '기도제목', (c1 + c2) / 2, top + 70, 40, 'NMB', INK); center(x, '응답하심', (c2 + r) / 2, top + 70, 40, 'NMB', INK); vline(x, c1, top, bot, INK_FAINT, 1.5); vline(x, c2, top, bot, INK_FAINT, 1.5); const rows = 11, rh = (bot - (top + hH)) / rows; for (let i = 1; i < rows; i++) rule(x, l, top + hH + i * rh, r, INK_FAINT, 1.4); sprig(x, W / 2, H - 130, .8, INK); return c; }
function rReading(title, books, cols) { const { c, x } = page(); center(x, title, W / 2, 280, 70, 'NMX', INK); spaced(x, 'BIBLE READING', W / 2, 345, 26, 'NMR', INK_SOFT, 12); const top = 470, colW = (W - M * 2) / cols, rows = Math.ceil(books.length / cols), rh = Math.min(118, (H - top - 230) / rows); for (let i = 0; i < books.length; i++) { const col = Math.floor(i / rows), row = i % rows; const bx = M + col * colW, by = top + row * rh; checkbox(x, bx, by, 34); left(x, books[i], bx + 56, by + 30, 34, 'NMR', INK); } sprig(x, W / 2, H - 130, .7, INK); return c; }
function rReflection() { const { c, x } = page(); spaced(x, 'LOOKING BACK', W / 2, 300, 30, 'NMR', INK_SOFT, 14); center(x, '한 해의 기도를 돌아보며', W / 2, 420, 60, 'NMX', INK); rule(x, W / 2 - 90, 490, W / 2 + 90, INK_FAINT, 2); const blocks = ['올해 가장 큰 기도 응답', '내 마음에 일어난 변화', '내년, 자녀를 위한 새 기도']; let y = 660; for (const b of blocks) { left(x, b, M, y, 46, 'NMB', INK); for (let i = 0; i < 3; i++) rule(x, M, y + 80 + i * 96, W - M, INK_FAINT, 1.6); y += 480; } sprig(x, W - M - 30, H - 150, 1.0, INK, .15); return c; }

const OT = ['창세기','출애굽기','레위기','민수기','신명기','여호수아','사사기','룻기','사무엘상','사무엘하','열왕기상','열왕기하','역대상','역대하','에스라','느헤미야','에스더','욥기','시편','잠언','전도서','아가','이사야','예레미야','예레미야애가','에스겔','다니엘','호세아','요엘','아모스','오바댜','요나','미가','나훔','하박국','스바냐','학개','스가랴','말라기'];
const NT = ['마태복음','마가복음','누가복음','요한복음','사도행전','로마서','고린도전서','고린도후서','갈라디아서','에베소서','빌립보서','골로새서','데살로니가전서','데살로니가후서','디모데전서','디모데후서','디도서','빌레몬서','히브리서','야고보서','베드로전서','베드로후서','요한일서','요한이서','요한삼서','유다서','요한계시록'];

// ---------- assemble book ----------
const DAILY = 92, LOG = 7;
const order = [];
order.push(rCover(), rTitle(), rHowTo(), rOwner(), rChildren(), rSection('자녀를 위한 기도'));
const dailyBuf = rDaily().toBuffer('image/png'); for (let i = 0; i < DAILY; i++) order.push(dailyBuf);
order.push(rSection('기도 응답 기록'));
const logBuf = rLog().toBuffer('image/png'); for (let i = 0; i < LOG; i++) order.push(logBuf);
order.push(rSection('말씀 읽기'), rReading('성경 통독표 · 구약', OT, 3), rReading('성경 통독표 · 신약', NT, 3), rReflection());

const A5W = 419.528, A5H = 595.276;
const doc = new PDFDocument({ size: 'A5', margin: 0 });
const out = fs.createWriteStream(`${DIR}/엄마의_기도_노트_완제품.pdf`);
doc.pipe(out);
order.forEach((p, i) => { if (i) doc.addPage({ size: 'A5', margin: 0 }); const buf = Buffer.isBuffer(p) ? p : p.toBuffer('image/png'); doc.image(buf, 0, 0, { width: A5W, height: A5H }); });
doc.end();
out.on('finish', () => console.log('DONE total pages = ' + order.length));

// also export the new sample pages for preview
fs.writeFileSync(`${DIR}/p_howto.png`, rHowTo().toBuffer('image/png'));
fs.writeFileSync(`${DIR}/p_children.png`, rChildren().toBuffer('image/png'));
fs.writeFileSync(`${DIR}/p_reading_ot.png`, rReading('성경 통독표 · 구약', OT, 3).toBuffer('image/png'));
fs.writeFileSync(`${DIR}/p_owner.png`, rOwner().toBuffer('image/png'));
fs.writeFileSync(`${DIR}/p_reflection.png`, rReflection().toBuffer('image/png'));

/**
 * 당근마켓 시세 추적기 v3 (Google Sheets + Apps Script) — 무료
 * ------------------------------------------------------------------
 * v2 대비 자동화 강화:
 *  ① Web App 엔드포인트(doPost) — 외부(브라우저 북마클릿/모바일/스크립트)에서 직접 기록
 *  ② 자동 단위 추론(상품명/옵션 텍스트에서 kg/박스/개 자동 인식)
 *  ③ 자유 텍스트 옵션 파싱 — "10개 14,820원", "4.5kg 30000" 등도 인식 (폴백)
 *  ④ 토큰 인증 — 무작위 토큰을 한 번 발급해 북마클릿에 저장(인터넷 누구나 호출 차단)
 *  ⑤ 일괄 등록 — 한 번의 POST로 여러 상품/옵션 등록
 *  ⑥ 메뉴에 'Web App URL/토큰 보기' 추가
 *
 * [한계] '수집'은 사용자가 본인 브라우저로 페이지를 연 뒤 북마클릿 클릭으로 추출하는 방식.
 *        서버 스크래핑이 아니므로 약관·봇차단 이슈 없음. 계산/기록/대시보드/알림은 100% 자동.
 * [설치] setup() → installDailyTrigger() → 메뉴 '🔐 Web App 발급/보기' → 배포 → 북마클릿에 URL+토큰 입력.
 */

const SHEET_LOG   = '시세기록';
const SHEET_INPUT = '입력';
const SHEET_DASH  = '대시보드';
const UNITS = ['개', '박스', 'kg'];

// ★ 변동 알림 받을 이메일 — 채우는 것을 권장(비우면 트리거에서 발신이 안 될 수 있음)
const ALERT_EMAIL = '';

/* ---------- 헬퍼 ---------- */
function toNum(v){ const n = parseFloat(String(v).replace(/[^0-9.]/g, '')); return isNaN(n) ? 0 : n; }
function toPrice(v){ const n = parseInt(String(v).replace(/[^0-9]/g, ''), 10); return isNaN(n) ? 0 : n; }
function normUnit(v){
  const u = String(v).trim().toLowerCase();
  if (['kg','킬로','키로','킬로그램','kg당','그램','g'].indexOf(u) >= 0) return 'kg';
  if (['박스','box','상자','박스당','팩','세트'].indexOf(u) >= 0) return '박스';
  if (['개','ea','개당','입','과','알','구','마리','통'].indexOf(u) >= 0) return '개';
  return '';
}
function ymd(d){ return Utilities.formatDate(new Date(d), Session.getScriptTimeZone(), 'yyyy-MM-dd'); }
function recipient(){ if (ALERT_EMAIL) return ALERT_EMAIL; const e = Session.getEffectiveUser().getEmail(); return e || ''; }

/**
 * 상품명/옵션 텍스트에서 단위 자동 추론.
 * 예) "초당옥수수 20개" → '개', "복숭아 4.5kg" → 'kg', "감귤 5kg 박스" → 'kg'
 */
function inferUnit(text){
  const s = String(text || '').toLowerCase();
  if (/(\d+(?:\.\d+)?)\s*(kg|킬로|키로|킬로그램)/.test(s)) return 'kg';
  if (/(\d+(?:\.\d+)?)\s*(g|그램)\b/.test(s)) return 'kg';  // g도 kg 카테고리로 묶음
  if (/(박스|상자|box|팩|세트)/.test(s)) return '박스';
  if (/(개|알|구|마리|통|입|과)\b/.test(s)) return '개';
  return '';
}

/**
 * 자유 텍스트 옵션 한 줄을 파싱.
 * 입력 예: "10개 14,820원", "4.5kg 30000", "5박스 / 25000원"
 * 반환:    { qty, unit, price } 또는 null
 */
function parseFreeOption(line){
  const s = String(line || '').trim();
  if (!s) return null;
  // 1) 가격 추출: "...원" 또는 라인 끝의 숫자(콤마 허용)
  let price = 0;
  let priceMatch = s.match(/([\d,]+)\s*원/);
  if (priceMatch) price = toPrice(priceMatch[1]);
  if (!price) {
    const m = s.match(/([\d,]{3,})/g); // 가격은 보통 3자리 이상
    if (m && m.length) price = toPrice(m[m.length - 1]);
  }
  if (!price) return null;
  // 2) 수량+단위
  const qm = s.match(/(\d+(?:\.\d+)?)\s*(kg|킬로|키로|킬로그램|g|그램|박스|상자|box|팩|세트|개|알|구|마리|통|입|과)/i);
  if (qm) {
    const qty = toNum(qm[1]);
    const unit = normUnit(qm[2]);
    if (qty && unit) return { qty, unit, price };
  }
  // 3) 단위 없는 숫자만 → 단위는 호출자가 추론
  const onlyNum = s.match(/^\s*(\d+(?:\.\d+)?)\s/);
  if (onlyNum) return { qty: toNum(onlyNum[1]), unit: '', price };
  return null;
}

/* ---------- 메뉴 ---------- */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📊 시세추적기')
    .addItem('① 입력 → 기록 추가', 'addEntries')
    .addItem('② 대시보드 새로고침', 'refreshDashboard')
    .addItem('③ 가격변동 지금 점검', 'checkNow')
    .addSeparator()
    .addItem('🔐 Web App URL / 토큰 보기', 'showWebAppInfo')
    .addItem('🔁 토큰 새로 발급(기존 무효화)', 'rotateApiToken')
    .addSeparator()
    .addItem('최초 1회: 시트 생성(setup)', 'setup')
    .addItem('최초 1회: 매일 알림 설치', 'installDailyTrigger')
    .addToUi();
}

/* ---------- 설치 ---------- */
function setup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // 시세기록
  let log = ss.getSheetByName(SHEET_LOG) || ss.insertSheet(SHEET_LOG);
  if (log.getLastRow() === 0) {
    log.appendRow(['기록일시','검색어','상품명','판매자','수량','단위','가격','단위당단가','평점','후기수','찜수','비고']);
    log.setFrozenRows(1);
    log.getRange('A1:L1').setFontWeight('bold').setBackground('#FFE7C2');
    log.getRange('E2:E').setNumberFormat('0.###');
    log.getRange('G2:H').setNumberFormat('#,##0');
  }

  // 입력 양식
  let inp = ss.getSheetByName(SHEET_INPUT) || ss.insertSheet(SHEET_INPUT);
  inp.clear();
  inp.getRange('B9:B200').clearDataValidations();
  inp.getRange(1, 1, 6, 2).setValues([
    ['검색어','초당옥수수'],
    ['상품명','달콤달달 꿀당도 초당옥수수 산지직송'],
    ['판매자','오늘팜365'],
    ['평점',4.4],
    ['후기수',28],
    ['찜수',177],
  ]);
  inp.getRange('A1:A6').setFontWeight('bold');
  inp.getRange('A8:C8').setValues([['수량','단위','가격']]).setFontWeight('bold').setBackground('#FFF2CC');
  inp.getRange(9, 1, 4, 3).setValues([
    [5,  '개', 9820],
    [10, '개', 14820],
    [15, '개', 20820],
    [20, '개', 25820],
  ]);
  const rule = SpreadsheetApp.newDataValidation().requireValueInList(UNITS, true).setAllowInvalid(true).build();
  inp.getRange('B9:B200').setDataValidation(rule);
  inp.getRange('A9:A200').setNumberFormat('0.###');
  inp.getRange('C9:C200').setNumberFormat('#,##0');
  inp.setColumnWidths(1, 3, 130);
  inp.getRange('A8').setNote('옥수수=개, 복숭아=kg, 묶음=박스. 북마클릿 사용 시 자동 입력됩니다.');

  // 대시보드
  let dash = ss.getSheetByName(SHEET_DASH) || ss.insertSheet(SHEET_DASH);
  dash.clear();
  dash.getRange('A1').setValue('대시보드는 메뉴 ②(새로고침)을 누르면 자동 생성됩니다.').setFontStyle('italic');

  // 신규상품 감지 기준 시각 초기화
  PropertiesService.getScriptProperties().setProperty('lastCheck', '0');
  // 토큰 자동 생성(없을 때만)
  ensureApiToken_();

  SpreadsheetApp.getUi().alert(
    '설치 완료!\n\n' +
    '1) [입력] 시트에 수동 입력하거나,\n' +
    '2) 메뉴 "🔐 Web App URL / 토큰 보기"로 발급된 정보를 북마클릿에 넣으면\n' +
    '   당근 상품 페이지에서 클릭 한 번으로 자동 기록됩니다.'
  );
}

/* ---------- 토큰 / Web App 정보 ---------- */
function ensureApiToken_(){
  const props = PropertiesService.getScriptProperties();
  let token = props.getProperty('apiToken');
  if (!token) {
    token = Utilities.getUuid().replace(/-/g, '');
    props.setProperty('apiToken', token);
  }
  return token;
}
function rotateApiToken(){
  const token = Utilities.getUuid().replace(/-/g, '');
  PropertiesService.getScriptProperties().setProperty('apiToken', token);
  SpreadsheetApp.getUi().alert('새 토큰 발급 완료. 메뉴의 "🔐 Web App URL / 토큰 보기"에서 확인하세요.\n기존 북마클릿은 더 이상 동작하지 않습니다.');
}
function showWebAppInfo(){
  const token = ensureApiToken_();
  let url = '';
  try { url = ScriptApp.getService().getUrl() || ''; } catch (e) {}
  const ui = SpreadsheetApp.getUi();
  const msg =
    '== Web App 배포 ==\n' +
    '1) 우측 상단 [배포] → [새 배포] → 유형 "웹 앱"\n' +
    '2) 액세스 권한: "모든 사용자" (Anyone) / 실행: "나"\n' +
    '3) 배포 후 표시되는 URL을 아래 칸에 채우세요.\n\n' +
    '현재 URL: ' + (url ? url : '(아직 배포되지 않음)') + '\n' +
    '토큰: ' + token + '\n\n' +
    '※ 북마클릿 설정 화면에 위 URL과 토큰을 붙여넣으세요.\n' +
    '※ 토큰이 노출되면 메뉴 "🔁 토큰 새로 발급"으로 무효화하세요.';
  ui.alert(msg);
}

/* ---------- Web App 엔드포인트 ---------- */
/**
 * POST 본문 예:
 * {
 *   "token": "....",
 *   "keyword": "초당옥수수",
 *   "name": "달콤달달 꿀당도 초당옥수수 산지직송",
 *   "seller": "오늘팜365",
 *   "rating": 4.4, "reviews": 28, "likes": 177,
 *   "options": [
 *     {"qty": 5, "unit": "개", "price": 9820},
 *     {"qty": 10, "unit": "개", "price": 14820}
 *   ],
 *   "optionsText": "10개 14,820원\n20개 25,820원"   // (대안) 자유텍스트로도 가능
 * }
 */
function doPost(e){
  try {
    const body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    const token = ensureApiToken_();
    if (!body.token || body.token !== token) return jsonOut_({ ok: false, error: 'unauthorized' });
    if (Array.isArray(body.items)) {
      let added = 0; const skipped = [];
      body.items.forEach(it => { const r = ingestOne_(it); added += r.added; r.skipped.forEach(s => skipped.push(s)); });
      refreshDashboard();
      return jsonOut_({ ok: true, added, skipped });
    }
    const r = ingestOne_(body);
    refreshDashboard();
    return jsonOut_({ ok: true, added: r.added, skipped: r.skipped });
  } catch (err) {
    return jsonOut_({ ok: false, error: String(err && err.message || err) });
  }
}
function doGet(e){
  // 헬스체크
  return jsonOut_({ ok: true, service: 'karrot-tracker', version: 'v3' });
}
function jsonOut_(obj){
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/**
 * 한 상품의 옵션들을 시세기록에 기록.
 * payload: { keyword, name, seller, rating, reviews, likes, options?, optionsText? }
 */
function ingestOne_(payload){
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const log = ss.getSheetByName(SHEET_LOG);
  if (!log) throw new Error('setup() 미실행');

  const keyword = String(payload.keyword || '').trim();
  const name    = String(payload.name || '').trim();
  const seller  = String(payload.seller || '').trim();
  const rating  = payload.rating ?? '';
  const reviews = payload.reviews ?? '';
  const likes   = payload.likes ?? '';
  if (!keyword || !name) throw new Error('keyword/name 필수');

  // 옵션 정규화
  let options = [];
  if (Array.isArray(payload.options) && payload.options.length) {
    options = payload.options.map(o => ({
      qty: toNum(o.qty), unit: normUnit(o.unit) || inferUnit((o.unit || '') + ' ' + name), price: toPrice(o.price)
    }));
  } else if (typeof payload.optionsText === 'string' && payload.optionsText.trim()) {
    payload.optionsText.split(/[\n\r]+/).forEach(line => {
      const p = parseFreeOption(line);
      if (p) { if (!p.unit) p.unit = inferUnit(name); options.push(p); }
    });
  }
  if (!options.length) throw new Error('options/optionsText 없음 또는 파싱 실패');

  // 중복 차단을 위한 기존 키 인덱싱
  const existing = {};
  const data = log.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    const r = data[i]; if (!r[0]) continue;
    existing[ymd(r[0]) + '|' + r[1] + '|' + r[2] + '|' + r[4] + '|' + r[5] + '|' + toPrice(r[6])] = true;
  }
  const today = ymd(new Date()), now = new Date();
  const rows = [], skipped = [];
  options.forEach((o, i) => {
    if (!o.qty || !o.price) { skipped.push('· 옵션 ' + (i+1) + ': 수량/가격 누락'); return; }
    if (!o.unit) { skipped.push('· 옵션 ' + (i+1) + ': 단위 인식 실패'); return; }
    const k = today + '|' + keyword + '|' + name + '|' + o.qty + '|' + o.unit + '|' + o.price;
    if (existing[k]) { skipped.push('· 옵션 ' + (i+1) + ': 오늘 같은 값 중복'); return; }
    rows.push([now, keyword, name, seller, o.qty, o.unit, o.price, Math.round(o.price / o.qty), rating, reviews, likes, '']);
    existing[k] = true;
  });
  if (rows.length) log.getRange(log.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows);
  return { added: rows.length, skipped };
}

/* ---------- 수동 기록 추가 (시트의 [입력] 시트에서) ---------- */
function addEntries() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const inp = ss.getSheetByName(SHEET_INPUT);
  const log = ss.getSheetByName(SHEET_LOG);
  if (!inp || !log) { ui.alert('먼저 메뉴에서 setup()을 실행하세요.'); return; }

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(20000)) { ui.alert('다른 작업이 실행 중입니다. 잠시 후 다시 시도하세요.'); return; }

  try {
    const keyword = String(inp.getRange('B1').getValue()).trim();
    const name    = String(inp.getRange('B2').getValue()).trim();
    const seller  = String(inp.getRange('B3').getValue()).trim();
    const rating  = inp.getRange('B4').getValue();
    const reviews = inp.getRange('B5').getValue();
    const likes   = inp.getRange('B6').getValue();
    if (!keyword || !name) { ui.alert('검색어(B1)와 상품명(B2)을 먼저 입력하세요.'); return; }

    const lastRow = inp.getLastRow();
    if (lastRow < 9) { ui.alert('옵션(수량/단위/가격)을 9행부터 입력하세요.'); return; }
    const opt = inp.getRange(9, 1, lastRow - 8, 3).getValues();

    const options = [];
    for (let i = 0; i < opt.length; i++) {
      const qRaw = opt[i][0], uRaw = opt[i][1], pRaw = opt[i][2];
      if (String(qRaw).trim() === '' && String(uRaw).trim() === '' && String(pRaw).trim() === '') continue;
      options.push({ qty: toNum(qRaw), unit: normUnit(uRaw) || inferUnit(uRaw + ' ' + name), price: toPrice(pRaw) });
    }
    const res = ingestOne_({ keyword, name, seller, rating, reviews, likes, options });
    if (res.added > 0) refreshDashboard();
    let msg = res.added + '건 기록했습니다.';
    if (res.skipped.length) msg += '\n\n[건너뜀 ' + res.skipped.length + '건]\n' + res.skipped.join('\n');
    ui.alert(msg);
  } catch (err) {
    ui.alert('오류: ' + err.message);
  } finally {
    lock.releaseLock();
  }
}

/* ---------- 대시보드 ---------- */
function refreshDashboard() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const log = ss.getSheetByName(SHEET_LOG);
  const dash = ss.getSheetByName(SHEET_DASH);
  if (!log || !dash) return;
  const data = log.getDataRange().getValues();
  if (data.length < 2) { dash.clear(); dash.getRange('A1').setValue('아직 기록이 없습니다.'); return; }
  const rows = data.slice(1).filter(r => r[0]);

  // 옵션 최신(검색어|상품|수량|단위)
  const latestOpt = {};
  rows.forEach(r => {
    const key = r[1] + '|' + r[2] + '|' + r[4] + '|' + r[5];
    const t = new Date(r[0]).getTime();
    if (!latestOpt[key] || t > latestOpt[key].t) latestOpt[key] = { t, r };
  });

  // 상품 단위(검색어|상품|단위) → 최저 단가 + 최신 메타
  const prod = {};
  Object.values(latestOpt).forEach(o => {
    const r = o.r, key = r[1] + '|' + r[2] + '|' + r[5], d = new Date(r[0]);
    if (!prod[key]) {
      prod[key] = { kw: r[1], name: r[2], seller: r[3], unit: r[5], minPer: Number(r[7]),
                    rating: r[8], reviews: r[9], likes: r[10], date: r[0] };
    } else {
      if (Number(r[7]) < prod[key].minPer) prod[key].minPer = Number(r[7]);
      if (d > new Date(prod[key].date)) {
        prod[key].date = r[0]; prod[key].seller = r[3];
        prod[key].rating = r[8]; prod[key].reviews = r[9]; prod[key].likes = r[10];
      }
    }
  });
  const prodList = Object.values(prod);

  dash.clear();
  const tz = Session.getScriptTimeZone();
  let row = 1;
  dash.getRange(row++, 1).setValue('📊 당근 시세 대시보드   (갱신: ' + Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd HH:mm') + ')')
    .setFontWeight('bold').setFontSize(12);
  dash.getRange(row++, 1).setValue('※ 단위가 다른 상품은 직접 비교 불가 → 단위(개/박스/kg)별로 분리 표시합니다.').setFontStyle('italic');
  row++;

  dash.getRange(row++, 1).setValue('▣ 검색어 × 단위 요약').setFontWeight('bold');
  dash.getRange(row++, 1, 1, 6)
    .setValues([['검색어','단위','상품수','최저 단위당단가','평균 단위당단가','최저가 상품(판매자)']])
    .setFontWeight('bold').setBackground('#FFE7C2');
  const grp = {};
  prodList.forEach(p => { const k = p.kw + '|' + p.unit; (grp[k] = grp[k] || []).push(p); });
  Object.keys(grp).sort().forEach(k => {
    const arr = grp[k], pers = arr.map(p => p.minPer);
    const min = Math.min.apply(null, pers);
    const avg = Math.round(pers.reduce((a, b) => a + b, 0) / pers.length);
    const best = arr.reduce((a, b) => b.minPer < a.minPer ? b : a);
    dash.getRange(row++, 1, 1, 6).setValues([[arr[0].kw, arr[0].unit, arr.length, min, avg, best.name + ' (' + best.seller + ')']]);
  });

  row += 2;
  dash.getRange(row++, 1).setValue('▣ 상품별 최신 스냅샷 (단위별 · 단위당단가 낮은 순)').setFontWeight('bold');
  dash.getRange(row++, 1, 1, 8)
    .setValues([['검색어','단위','상품명','판매자','단위당단가','평점','후기','찜']])
    .setFontWeight('bold').setBackground('#FFE7C2');
  prodList.sort((a, b) => a.unit < b.unit ? -1 : a.unit > b.unit ? 1 : a.minPer - b.minPer).forEach(p => {
    dash.getRange(row++, 1, 1, 8).setValues([[p.kw, p.unit, p.name, p.seller, p.minPer, p.rating, p.reviews, p.likes]]);
  });

  dash.getRange('D:E').setNumberFormat('#,##0');
  dash.autoResizeColumns(1, 8);
}

/* ---------- 변동 점검 (수동 래퍼) ---------- */
function checkNow() {
  const res = checkPriceChanges();
  const ui = SpreadsheetApp.getUi();
  let msg;
  if (res.priceChanges.length === 0 && res.newProducts.length === 0) {
    msg = '변동 없음 — 가격 변동/신규 상품이 감지되지 않았습니다.';
  } else {
    msg = '';
    if (res.priceChanges.length) msg += '가격 변동 ' + res.priceChanges.length + '건\n';
    if (res.newProducts.length)  msg += '신규 상품 ' + res.newProducts.length + '건\n';
    msg += res.sent ? ('\n알림 메일을 ' + res.to + ' 로 보냈습니다.')
                    : '\n⚠️ 보낼 이메일이 없어 메일은 생략했습니다. 코드 상단 ALERT_EMAIL을 채우세요.';
  }
  ui.alert(msg);
}

/* ---------- 변동 점검 (핵심 · 트리거가 호출) ---------- */
function checkPriceChanges() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const log = ss.getSheetByName(SHEET_LOG);
  const out = { priceChanges: [], newProducts: [], sent: false, to: '' };
  if (!log) return out;
  const data = log.getDataRange().getValues();
  if (data.length < 2) return out;
  const rows = data.slice(1).filter(r => r[0]);

  const props = PropertiesService.getScriptProperties();
  const lastCheck = Number(props.getProperty('lastCheck') || '0');

  const groups = {};
  rows.forEach(r => { const key = r[1] + '|' + r[2] + '|' + r[4] + '|' + r[5]; (groups[key] = groups[key] || []).push(r); });
  Object.keys(groups).forEach(key => {
    const g = groups[key].sort((a, b) => new Date(a[0]) - new Date(b[0]));
    if (g.length < 2) return;
    const last = g[g.length - 1], prev = g[g.length - 2];
    if (Number(last[6]) !== Number(prev[6])) {
      const p = key.split('|');
      out.priceChanges.push({ kw: p[0], name: p[1], qty: p[2], unit: p[3],
        oldP: Number(prev[6]), newP: Number(last[6]), oldU: Number(prev[7]), newU: Number(last[7]) });
    }
  });

  const firstSeen = {};
  rows.forEach(r => { const key = r[1] + '|' + r[2] + '|' + r[3]; const t = new Date(r[0]).getTime();
    if (!firstSeen[key] || t < firstSeen[key]) firstSeen[key] = t; });
  Object.keys(firstSeen).forEach(key => {
    if (firstSeen[key] > lastCheck) { const p = key.split('|'); out.newProducts.push({ kw: p[0], name: p[1], seller: p[2] }); }
  });

  props.setProperty('lastCheck', String(Date.now()));
  if (out.priceChanges.length === 0 && out.newProducts.length === 0) return out;

  let body = '당근 시세 점검 결과 (' + Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm') + ')\n\n';
  if (out.priceChanges.length) {
    body += '■ 가격 변동\n';
    out.priceChanges.forEach(c => {
      const dir = c.newP > c.oldP ? '▲인상' : '▼인하';
      body += '· [' + c.kw + '] ' + c.name + ' ' + c.qty + c.unit + '\n';
      body += '   ' + c.oldP.toLocaleString() + '원 → ' + c.newP.toLocaleString() + '원 (' + dir + ')';
      body += ' / ' + c.unit + '당 ' + c.oldU.toLocaleString() + '→' + c.newU.toLocaleString() + '원\n';
    });
    body += '\n';
  }
  if (out.newProducts.length) {
    body += '■ 신규 감지 상품\n';
    out.newProducts.forEach(n => { body += '· [' + n.kw + '] ' + n.name + ' (' + n.seller + ')\n'; });
  }

  const to = recipient();
  if (to) {
    MailApp.sendEmail(to, '📊 당근 시세 점검 (변동 ' + out.priceChanges.length + ' / 신규 ' + out.newProducts.length + ')', body);
    out.sent = true; out.to = to;
  } else {
    console.warn('ALERT_EMAIL이 비어 있고 발신 계정 이메일을 가져오지 못해 메일 발송을 건너뜀.');
  }
  return out;
}

/* ---------- 트리거 설치 ---------- */
function installDailyTrigger() {
  ScriptApp.getProjectTriggers().forEach(t => { if (t.getHandlerFunction() === 'checkPriceChanges') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('checkPriceChanges').timeBased().everyDays(1).atHour(8).create();
  SpreadsheetApp.getUi().alert(
    '매일 오전 8시(스크립트 시간대 기준)에 가격변동·신규상품을 점검해 메일로 알려드립니다.\n\n' +
    '※ 시간대가 한국이 아니면: 확장 > Apps Script > 프로젝트 설정에서 시간대를 (GMT+9) 서울로 변경하세요.'
  );
}

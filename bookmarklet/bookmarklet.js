/**
 * 당근 시세 추적기 — 브라우저 북마클릿 (풀 소스)
 * ------------------------------------------------------------
 * 사용:
 *   1) 당근 상품 페이지를 연다.
 *   2) (선택) 옵션 영역을 마우스로 드래그해 텍스트 선택.
 *   3) 북마클릿 클릭 → 자동 추출된 값 확인 → [전송] → 시트에 자동 기록.
 *
 * 최초 1회: Web App URL과 토큰 입력 프롬프트가 뜸 (이후 localStorage에 저장).
 * 토큰/URL 재설정: 콘솔에 localStorage.removeItem('karrotTracker.url');
 *                       localStorage.removeItem('karrotTracker.token');
 *
 * 빌드: bookmarklet.min.js 는 이 파일을 압축해 javascript: 프리픽스를 붙인 것.
 */
(function(){
  'use strict';
  const KEY_URL = 'karrotTracker.url';
  const KEY_TOKEN = 'karrotTracker.token';

  function $(id){ return document.getElementById(id); }
  function esc(v){ return String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

  function extract(){
    const text = (document.body && document.body.innerText) || '';
    const d = { keyword:'', name:'', seller:'', rating:'', reviews:'', likes:'', optionsText:'', url: location.href };

    // 상품명: og:title 우선
    const og = document.querySelector('meta[property="og:title"]');
    if (og && og.content) d.name = og.content.replace(/\s*[|\-–·•].*$/, '').trim();
    if (!d.name) {
      const h1 = document.querySelector('h1');
      if (h1) d.name = h1.innerText.trim();
    }
    if (!d.name) d.name = document.title.replace(/\s*[|\-–·•].*$/, '').trim();

    // 평점: "4.5점" 또는 "★ 4.5" 또는 "별점 4.5"
    const mR = text.match(/별점\s*([0-9]\.[0-9])/) || text.match(/(?:★|⭐)\s*([0-9]\.[0-9])/) || text.match(/([0-9]\.[0-9])\s*점/);
    if (mR) d.rating = parseFloat(mR[1]);

    // 후기수: "후기 28" / "리뷰 28개" / "후기(28)"
    const mRv = text.match(/(?:후기|리뷰)\s*[\(\s]?\s*([\d,]+)/);
    if (mRv) d.reviews = parseInt(mRv[1].replace(/,/g,''), 10);

    // 찜수: "찜 177" / "관심 177"
    const mL = text.match(/(?:찜|관심)\s*[\(\s]?\s*([\d,]+)/);
    if (mL) d.likes = parseInt(mL[1].replace(/,/g,''), 10);

    // 판매자: "판매자" / "스토어" 다음 줄
    const mS = text.match(/(?:판매자|스토어|상점)\s*[:|\n]\s*([^\n]+)/);
    if (mS) d.seller = mS[1].trim().slice(0, 40);

    // 검색어 초기값: 상품명의 첫 의미 토큰
    if (d.name) {
      const tk = d.name.split(/\s+/).filter(t => t.length >= 2)[0];
      if (tk) d.keyword = tk;
    }

    // 옵션 텍스트: 드래그 선택이 있으면 그것, 없으면 페이지에서 가격 패턴 라인 추출
    const sel = (window.getSelection && window.getSelection().toString().trim()) || '';
    if (sel) {
      d.optionsText = sel;
    } else {
      // best-effort: "숫자(개|kg|박스 등) ... 숫자원" 패턴 라인만 추출
      const lines = text.split(/\n/).map(l => l.trim()).filter(Boolean);
      const optLines = lines.filter(l =>
        /(\d+(?:\.\d+)?\s*(?:kg|킬로|키로|박스|상자|개|알|입|구|마리|통|팩|세트))/i.test(l) &&
        /[\d,]+\s*원/.test(l)
      ).slice(0, 12);
      d.optionsText = optLines.join('\n');
    }
    return d;
  }

  function showModal(data){
    const old = $('karrot-tracker-modal'); if (old) old.remove();

    const modal = document.createElement('div');
    modal.id = 'karrot-tracker-modal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:2147483647;display:flex;align-items:center;justify-content:center;font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;';

    modal.innerHTML = ''
      + '<div style="background:#fff;padding:20px 22px;border-radius:14px;max-width:520px;width:92%;max-height:88vh;overflow:auto;box-shadow:0 16px 40px rgba(0,0,0,.25);color:#222;">'
      +   '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">'
      +     '<div style="font-size:17px;font-weight:700;">📊 당근 시세 추적기</div>'
      +     '<button id="kt-x" style="border:none;background:transparent;font-size:22px;cursor:pointer;color:#999;">×</button>'
      +   '</div>'
      +   '<div style="font-size:12px;color:#666;margin-bottom:14px;line-height:1.45;">'
      +     '자동 추출된 값을 확인/수정 후 <b>전송</b> 누르세요.<br>'
      +     '<b>옵션</b>은 한 줄=한 옵션 (예: <code>10개 14,820원</code>, <code>4.5kg 30000</code>).'
      +   '</div>'
      + lbl('검색어 (분류 키워드)') + inp('kt-keyword', data.keyword)
      + lbl('상품명')               + inp('kt-name',    data.name)
      + lbl('판매자')               + inp('kt-seller',  data.seller)
      +   '<div style="display:flex;gap:8px;">'
      +     col('평점',    'kt-rating',  data.rating)
      +     col('후기수',  'kt-reviews', data.reviews)
      +     col('찜수',    'kt-likes',   data.likes)
      +   '</div>'
      + lbl('옵션 (한 줄=한 옵션)')
      +   '<textarea id="kt-options" rows="6" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;box-sizing:border-box;font:13px/1.4 ui-monospace,Menlo,Consolas,monospace;">' + esc(data.optionsText) + '</textarea>'
      +   '<div style="display:flex;gap:8px;margin-top:16px;justify-content:flex-end;align-items:center;">'
      +     '<div id="kt-status" style="flex:1;font-size:12px;color:#666;"></div>'
      +     '<button id="kt-settings" style="padding:8px 12px;border:1px solid #ddd;background:#fafafa;border-radius:8px;cursor:pointer;font-size:12px;">설정</button>'
      +     '<button id="kt-cancel" style="padding:8px 14px;border:1px solid #ddd;background:#fff;border-radius:8px;cursor:pointer;">취소</button>'
      +     '<button id="kt-send" style="padding:8px 18px;border:none;background:#FF6F0F;color:#fff;border-radius:8px;cursor:pointer;font-weight:700;">전송 →</button>'
      +   '</div>'
      + '</div>';

    function lbl(t){ return '<div style="font-size:12px;color:#555;margin:8px 0 4px;font-weight:600;">' + t + '</div>'; }
    function inp(id, v){ return '<input id="' + id + '" value="' + esc(v) + '" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;box-sizing:border-box;font-size:14px;">'; }
    function col(t, id, v){ return '<div style="flex:1;">' + lbl(t) + inp(id, v) + '</div>'; }

    document.body.appendChild(modal);

    $('kt-x').onclick = $('kt-cancel').onclick = () => modal.remove();
    $('kt-settings').onclick = () => { localStorage.removeItem(KEY_URL); localStorage.removeItem(KEY_TOKEN); modal.remove(); alert('설정 초기화됨. 북마클릿을 다시 눌러주세요.'); };

    $('kt-send').onclick = async () => {
      const url = localStorage.getItem(KEY_URL);
      const token = localStorage.getItem(KEY_TOKEN);
      const status = $('kt-status');
      const payload = {
        token: token,
        keyword: $('kt-keyword').value.trim(),
        name:    $('kt-name').value.trim(),
        seller:  $('kt-seller').value.trim(),
        rating:  parseFloat($('kt-rating').value)  || '',
        reviews: parseInt($('kt-reviews').value, 10) || '',
        likes:   parseInt($('kt-likes').value, 10)   || '',
        optionsText: $('kt-options').value
      };
      if (!payload.keyword || !payload.name) { status.textContent = '⚠️ 검색어/상품명 필수'; status.style.color = '#d33'; return; }
      if (!payload.optionsText.trim()) { status.textContent = '⚠️ 옵션 1줄 이상 필요'; status.style.color = '#d33'; return; }

      status.textContent = '전송 중…'; status.style.color = '#666';
      try {
        // Apps Script Web App은 CORS 응답 헤더가 없어 응답 본문을 못 읽음.
        // text/plain content-type으로 보내면 preflight 없이 simple POST로 처리됨.
        await fetch(url, {
          method: 'POST',
          mode: 'no-cors',
          headers: { 'Content-Type': 'text/plain;charset=utf-8' },
          body: JSON.stringify(payload)
        });
        status.innerHTML = '✓ 전송됨 — 시트에서 확인하세요.';
        status.style.color = '#080';
        setTimeout(() => modal.remove(), 1200);
      } catch (err) {
        status.textContent = '✗ 전송 실패: ' + (err && err.message || err);
        status.style.color = '#d33';
      }
    };
  }

  // 진입점
  let url = localStorage.getItem(KEY_URL);
  let token = localStorage.getItem(KEY_TOKEN);
  if (!url) {
    url = prompt('Apps Script Web App URL을 붙여넣으세요\n(시트 메뉴 → 🔐 Web App URL/토큰 보기)', '');
    if (!url) return;
    url = url.trim();
    localStorage.setItem(KEY_URL, url);
  }
  if (!token) {
    token = prompt('토큰을 붙여넣으세요', '');
    if (!token) return;
    token = token.trim();
    localStorage.setItem(KEY_TOKEN, token);
  }
  showModal(extract());
})();

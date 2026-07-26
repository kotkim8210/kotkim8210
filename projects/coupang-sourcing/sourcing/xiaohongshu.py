"""샤오홍수(小红书/RED) 트렌드 키워드 소스 — '레드오션 중 후기좋은 신제품' 발굴용.

전략: 레드오션(=쿠팡에 이미 경쟁 많음)이라도, 샤오홍수에서 **막 뜨는(후기 좋은 신상)**
아이템은 한국 쿠팡엔 아직 '신제품 각도'로 빈틈이 있다. 그 각도를 키워드로 뽑는다.

현실적 한계(정직하게):
- 샤오홍수는 강력한 반봇 + 로그인 월(wall) + 중국 리전이라 **자동 수집이 매우 불안정**하다.
- 그래서 이 모듈은 두 경로를 제공한다:
    1) fetch_notes(): StealthyFetcher로 시도(불안정 — 성공하면 노트 제목/좋아요 파싱)
    2) load_manual(): 사람이 앱에서 눈으로 보고 적은 키워드 목록(JSON)을 읽어 파이프라인에 투입
- 어떤 경로든 결과는 '한국어 소싱 키워드 후보'로 정규화해 쿠팡 파이프라인에 넘긴다.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger("sourcing.xhs")

SEARCH_URL = "https://www.xiaohongshu.com/search_result?keyword={q}"
MANUAL_FILE = Path(__file__).resolve().parent.parent / "config" / "xhs_manual.json"


def load_manual(path: str | Path | None = None) -> list[dict]:
    """앱에서 직접 관찰한 트렌드 키워드 목록을 읽는다.

    config/xhs_manual.json 형식:
        {"keywords": [
            {"kr": "심리스 팬티", "zh": "无痕内裤", "note": "여름 신상 후기 폭발", "likes": 12000}
        ]}
    """
    p = Path(path) if path else MANUAL_FILE
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.warning("xhs_manual.json 로드 실패: %s", exc)
        return []
    out = []
    for k in data.get("keywords", []):
        kw = k.get("kr") or k.get("keyword") or k.get("zh")
        if kw:
            out.append({
                "keyword": kw,
                "zh": k.get("zh"),
                "note": k.get("note"),
                "likes": k.get("likes"),
                "source": "xhs-manual",
            })
    return out


def fetch_notes(keyword: str, opts=None, limit: int = 20) -> list[dict]:
    """샤오홍수 검색을 StealthyFetcher로 시도(불안정). 실패하면 빈 리스트.

    성공 시 노트 제목/좋아요 수를 뽑아 인기 순으로 반환한다.
    구조가 자주 바뀌므로 __INITIAL_STATE__ JSON을 재귀 탐색한다.
    """
    try:
        # 크롤러 패키지(coupang-naver-crawler)를 재사용
        import sys
        crawler_path = Path(__file__).resolve().parent.parent.parent / "coupang-naver-crawler"
        if str(crawler_path) not in sys.path:
            sys.path.insert(0, str(crawler_path))
        from crawler import common, naver_shopping  # naver_shopping._walk 재사용
        from crawler.common import FetchOptions
    except Exception as exc:  # noqa: BLE001
        log.warning("크롤러 패키지를 찾지 못해 샤오홍수 자동수집을 건너뜁니다: %s", exc)
        return []

    from urllib.parse import quote
    opts = opts or FetchOptions(engine="stealthy", timeout=45000)
    url = SEARCH_URL.format(q=quote(keyword))
    try:
        page = common.with_retry(lambda: common.fetch(url, opts), what="xhs", tries=1)
    except Exception as exc:  # noqa: BLE001
        log.warning("샤오홍수 접근 실패(로그인월/차단 가능): %s", str(exc)[:120])
        return []

    # __INITIAL_STATE__ 류의 상태 JSON에서 노트를 긁는다(제목+좋아요 heuristic)
    notes: list[dict] = []
    raw = None
    for sel in ("script#__INITIAL_STATE__::text", "script[id*='INITIAL']::text"):
        try:
            raw = page.css(sel).get()
        except Exception:  # noqa: BLE001
            raw = None
        if raw:
            break
    if raw:
        try:
            data = json.loads(raw.replace("undefined", "null"))
            _walk_notes(data, notes)
        except Exception:  # noqa: BLE001
            pass
    notes.sort(key=lambda x: x.get("likes") or 0, reverse=True)
    return notes[:limit]


_TITLE_KEYS = ("title", "displayTitle", "desc")
_LIKE_KEYS = ("likedCount", "likes", "interactInfo")


def _walk_notes(node, out: list[dict]) -> None:
    if isinstance(node, dict):
        title = next((node[k] for k in _TITLE_KEYS if isinstance(node.get(k), str) and node.get(k)), None)
        likes = None
        for k in _LIKE_KEYS:
            v = node.get(k)
            if isinstance(v, (int, str)):
                likes = _to_int(v)
                break
            if isinstance(v, dict) and "likedCount" in v:
                likes = _to_int(v["likedCount"])
                break
        if title and likes is not None:
            out.append({"title": title, "likes": likes, "source": "xhs-auto"})
            return
        for v in node.values():
            _walk_notes(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_notes(v, out)


def _to_int(v) -> int:
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).replace("+", "").replace(",", "").strip()
    if s.endswith("万"):
        try:
            return int(float(s[:-1]) * 10000)
        except ValueError:
            return 0
    try:
        return int(s)
    except ValueError:
        return 0

"""네이버 데이터랩 쇼핑인사이트 — 키 없이 쓰는 실시간 시장조사 소스.

왜 이걸 쓰나
------------
쿠팡·네이버쇼핑 HTML은 봇 차단(Akamai 403 / 네이버 418)으로 막히고, 스텔스
브라우저는 개발 샌드박스의 이그레스 정책에 걸린다. 반면 데이터랩의
쇼핑인사이트는 **공개 웹 서비스의 조회 기능**이라 API 키 없이도 응답한다.

여기서 얻는 것(전부 실데이터):
  · 카테고리 트리 (대→중→소분류, cid)
  · 카테고리별 인기 검색어 TOP N (기간·기기·성별·연령 필터)
  · 키워드/카테고리 검색 트렌드 지수(시계열)

이건 '무엇이 지금 팔리는가'를 카테고리 단위로 보는 데 최적이다.
경쟁 상품의 리뷰수·가격은 여기서 안 나오므로, 그 부분은 쿠팡 파트너스
공식 API(coupang_partners.py)나 사용자 PC의 크롤러로 보완한다.

주의: 과도한 호출은 삼간다(기본 지연 내장). 공개 조회 기능을 예의 있게 쓴다.
"""
from __future__ import annotations

import json
import logging
import random
import time
import urllib.parse
import urllib.request

log = logging.getLogger("sourcing.datalab")

BASE = "https://datalab.naver.com/shoppingInsight"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def _post(path: str, data: dict, timeout: int = 20) -> dict | None:
    body = urllib.parse.urlencode(data, encoding="utf-8").encode()
    req = urllib.request.Request(
        f"{BASE}/{path}",
        data=body,
        headers={
            "User-Agent": UA,
            "Referer": f"{BASE}/sCategory.naver",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "ko-KR,ko;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.warning("데이터랩 요청 실패(%s): %s", path, str(exc)[:120])
        return None


def polite() -> None:
    time.sleep(0.8 + random.uniform(0, 0.7))


# --------------------------------------------------------------------------- #
# 카테고리
# --------------------------------------------------------------------------- #
def categories(cid: int | str = 0) -> list[dict]:
    """cid의 하위 카테고리 목록. cid=0이면 대분류 전체."""
    d = _post("getCategory.naver", {"cid": cid})
    if not d:
        return []
    return [
        {"cid": c["cid"], "name": c["name"], "path": c.get("fullPath", c["name"]),
         "level": c.get("level"), "leaf": c.get("leaf", False)}
        for c in d.get("childList", [])
    ]


def find_category(keyword: str, max_depth: int = 3) -> list[dict]:
    """카테고리명에 keyword가 들어가는 항목을 트리에서 찾는다(대→중→소)."""
    found, queue = [], [(0, 0)]
    seen = set()
    while queue:
        cid, depth = queue.pop(0)
        if depth > max_depth or cid in seen:
            continue
        seen.add(cid)
        for c in categories(cid):
            if keyword in c["name"]:
                found.append(c)
            if depth + 1 <= max_depth and not c["leaf"]:
                queue.append((c["cid"], depth + 1))
        polite()
    return found


# --------------------------------------------------------------------------- #
# 인기 검색어
# --------------------------------------------------------------------------- #
def keyword_rank(
    cid: int | str,
    start: str,
    end: str,
    *,
    count: int = 20,
    page: int = 1,
    device: str = "",       # "" 전체 / "pc" / "mo"
    gender: str = "",       # "" 전체 / "f" / "m"
    age: str = "",          # "" 전체 / "10","20",...
    time_unit: str = "date",
) -> list[dict]:
    """카테고리의 인기 검색어 순위. (rank, keyword)"""
    d = _post("getCategoryKeywordRank.naver", {
        "cid": cid, "timeUnit": time_unit, "startDate": start, "endDate": end,
        "age": age, "gender": gender, "device": device, "page": page, "count": count,
    })
    if not d or d.get("statusCode") != 200:
        return []
    return [{"rank": r["rank"], "keyword": r["keyword"]} for r in d.get("ranks", [])]


def keyword_rank_pages(cid, start, end, pages: int = 5, count: int = 20, **kw) -> list[dict]:
    """여러 페이지를 이어붙여 TOP N을 크게 가져온다."""
    out: list[dict] = []
    for p in range(1, pages + 1):
        rows = keyword_rank(cid, start, end, count=count, page=p, **kw)
        if not rows:
            break
        out.extend(rows)
        polite()
    return out


# --------------------------------------------------------------------------- #
# 트렌드(시계열)
# --------------------------------------------------------------------------- #
def category_trend(cid: int | str, start: str, end: str, time_unit: str = "month") -> list[dict]:
    """카테고리 클릭량 추이(상대지수). 계절성 판단에 쓴다."""
    d = _post("getCategoryClickTrend.naver", {
        "cid": cid, "timeUnit": time_unit, "startDate": start, "endDate": end,
        "age": "", "gender": "", "device": "",
    })
    if not d:
        return []
    series = []
    for grp in d.get("result", []):
        for pt in grp.get("data", []):
            series.append({"period": pt.get("period"), "value": pt.get("value")})
    return series


def keyword_trend(cid: int | str, keyword: str, start: str, end: str,
                  time_unit: str = "month") -> list[dict]:
    """특정 키워드의 카테고리 내 클릭 추이."""
    d = _post("getKeywordClickTrend.naver", {
        "cid": cid, "timeUnit": time_unit, "startDate": start, "endDate": end,
        "age": "", "gender": "", "device": "", "keyword": keyword,
    })
    if not d:
        return []
    series = []
    for grp in d.get("result", []):
        for pt in grp.get("data", []):
            series.append({"period": pt.get("period"), "value": pt.get("value")})
    return series

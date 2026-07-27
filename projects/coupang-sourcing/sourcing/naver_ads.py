"""네이버 검색광고 API 클라이언트 — 키워드 월간 검색량 조회.

'검색량이 높고'를 판정하는 표준 소스다. API는 **무료**지만 키가 필요하다.
키가 없으면 이 모듈은 조용히 None을 반환하고, 파이프라인은 검색량 신호만 빼고 진행한다.

키 발급: 네이버 검색광고(searchad.naver.com) 로그인 → 도구 → API 사용관리 →
         API 라이선스 신청. 아래 3개 값을 환경변수로 넣는다:
    NAVER_AD_API_KEY       (액세스 라이선스)
    NAVER_AD_SECRET_KEY    (비밀키)
    NAVER_AD_CUSTOMER_ID   (고객 ID)

엔드포인트: GET https://api.searchad.naver.com/keywordstool?hintKeywords=...&showDetail=1
서명: HMAC-SHA256( "{timestamp}.{method}.{path}" , secret ) → base64, X-Signature 헤더.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request

BASE = "https://api.searchad.naver.com"
PATH = "/keywordstool"


def _creds() -> tuple[str, str, str] | None:
    k = os.environ.get("NAVER_AD_API_KEY")
    s = os.environ.get("NAVER_AD_SECRET_KEY")
    c = os.environ.get("NAVER_AD_CUSTOMER_ID")
    if k and s and c:
        return k, s, c
    return None


def _sign(secret: str, timestamp: str, method: str, path: str) -> str:
    msg = f"{timestamp}.{method}.{path}"
    digest = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _to_int(v) -> int:
    """'< 10' 같은 값도 안전하게 정수화."""
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).replace("<", "").replace(",", "").strip()
    try:
        return int(s)
    except ValueError:
        return 0


def keyword_stats(keyword: str, timeout: int = 10) -> dict | None:
    """키워드 → {pc, mobile, total, competition, avg_clicks}. 키 없거나 실패 시 None."""
    creds = _creds()
    if not creds:
        return None
    api_key, secret, customer_id = creds

    timestamp = str(int(time.time() * 1000))
    signature = _sign(secret, timestamp, "GET", PATH)
    # 검색광고 키워드도구는 공백 없는 대문자 키워드를 권장
    hint = keyword.replace(" ", "")
    query = urllib.parse.urlencode({"hintKeywords": hint, "showDetail": "1"})
    req = urllib.request.Request(
        f"{BASE}{PATH}?{query}",
        headers={
            "X-Timestamp": timestamp,
            "X-API-KEY": api_key,
            "X-Customer": str(customer_id),
            "X-Signature": signature,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except Exception:  # noqa: BLE001 - 네트워크/권한 실패 시 신호 생략
        return None

    rows = data.get("keywordList") or []
    if not rows:
        return None
    # 정확 매칭 우선, 없으면 첫 행
    exact = next((r for r in rows if r.get("relKeyword", "").replace(" ", "") == hint), rows[0])
    pc = _to_int(exact.get("monthlyPcQcCnt"))
    mo = _to_int(exact.get("monthlyMobileQcCnt"))
    return {
        "keyword": exact.get("relKeyword", keyword),
        "pc": pc,
        "mobile": mo,
        "total": pc + mo,
        "competition": exact.get("compIdx"),  # '높음'/'중간'/'낮음'
        "avg_clicks": _to_int(exact.get("monthlyAvePcClkCnt")) + _to_int(exact.get("monthlyAveMobileClkCnt")),
    }


def related_keywords(keyword: str, limit: int = 20, timeout: int = 10) -> list[dict]:
    """연관 키워드 + 검색량 목록(키워드 확장용). 키 없으면 빈 리스트."""
    creds = _creds()
    if not creds:
        return []
    api_key, secret, customer_id = creds
    timestamp = str(int(time.time() * 1000))
    signature = _sign(secret, timestamp, "GET", PATH)
    query = urllib.parse.urlencode({"hintKeywords": keyword.replace(" ", ""), "showDetail": "1"})
    req = urllib.request.Request(
        f"{BASE}{PATH}?{query}",
        headers={
            "X-Timestamp": timestamp, "X-API-KEY": api_key,
            "X-Customer": str(customer_id), "X-Signature": signature,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except Exception:  # noqa: BLE001
        return []
    out = []
    for r in (data.get("keywordList") or [])[:limit]:
        pc, mo = _to_int(r.get("monthlyPcQcCnt")), _to_int(r.get("monthlyMobileQcCnt"))
        out.append({"keyword": r.get("relKeyword"), "total": pc + mo, "competition": r.get("compIdx")})
    return out

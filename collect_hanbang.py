# -*- coding: utf-8 -*-
"""수도권 한방병원 수집 (HIRA, clCd=92 + 명칭 '한방병원' 필터)."""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

SEARCH_URL = "https://www.hira.or.kr/ra/hosp/selectHospSrchKndListAjax.do"
DETAIL_URL = "https://www.hira.or.kr/ra/hosp/hospAjax.do"
METRO_SIDO = {"서울", "경기", "인천"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://www.hira.or.kr/ra/hosp/getHealthMap.do?pgmid=HIRAA030002000000",
}


def post_json(session, url, payload):
    for attempt in range(4):
        try:
            resp = session.post(url, data=payload, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError):
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))


def fetch_detail(session, hospital):
    try:
        data = post_json(session, DETAIL_URL, {"ykiho": hospital["ykiho"]})
        info = data.get("data", {}).get("hospInfo") or {}
        url = (info.get("hospUrl") or "").strip()
        if url and not url.lower().startswith(("http://", "https://")):
            url = "http://" + url
        hospital["homepage"] = url
        if not hospital["phone"]:
            hospital["phone"] = (info.get("telNo") or "").strip()
    except Exception as exc:  # noqa: BLE001
        print(f"  상세 실패: {hospital['name']} ({exc})", flush=True)
    time.sleep(0.1)
    return hospital


def main():
    session = requests.Session()
    base = {"clCd": "92", "kindyadmNm": "한방병원", "isDown": "N"}

    first = post_json(session, SEARCH_URL, {**base, "pageIndex": 1})
    pagination = first["data"]["paginationInfo"]
    total_pages = pagination["totalPageCount"]
    print(f"전국 한방병원: {pagination['totalRecordCount']}건 ({total_pages}페이지)", flush=True)

    hospitals = {}
    page = 1
    while page <= total_pages:
        data = first if page == 1 else post_json(session, SEARCH_URL, {**base, "pageIndex": page})
        for item in data["data"]["hospList"]:
            if item.get("clCdNm") != "한방병원":
                continue
            sido = (item.get("sidoCdNm") or "").strip()
            if sido not in METRO_SIDO:
                continue
            region = " ".join(p for p in (sido, item.get("sgguCdNm")) if p).strip()
            ykiho = item.get("ykiho")
            hospitals[ykiho] = {
                "ykiho": ykiho,
                "name": (item.get("yadmNm") or "").strip(),
                "region": region,
                "phone": (item.get("yadmGdTelnoTxt") or "").strip(),
                "email": "",
                "fax": "",
                "homepage": "",
            }
        print(f"  목록 {page}/{total_pages} (수도권 누적 {len(hospitals)}건)", flush=True)
        page += 1
        time.sleep(0.25)

    rows = list(hospitals.values())
    done = 0
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(fetch_detail, session, h) for h in rows]
        for _ in as_completed(futures):
            done += 1
            if done % 50 == 0 or done == len(rows):
                print(f"  상세 {done}/{len(rows)}건", flush=True)

    for h in rows:
        h.pop("ykiho", None)
    rows.sort(key=lambda h: (h["region"], h["name"]))
    with open("/tmp/hanbang_metro.json", "w", encoding="utf-8") as fp:
        json.dump(rows, fp, ensure_ascii=False)
    print(f"저장 완료: /tmp/hanbang_metro.json ({len(rows)}건)", flush=True)


if __name__ == "__main__":
    main()

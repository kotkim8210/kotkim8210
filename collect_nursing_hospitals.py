# -*- coding: utf-8 -*-
"""전국 요양병원 정보 수집 스크립트.

건강보험심사평가원(HIRA) 병원·약국 찾기 서비스에서 요양병원(종별코드 28)
전체 목록을 수집하여 엑셀 파일로 저장한다.

출력 형식 (1행 머리글):
    A열: 병원명 / B열: 지역 / C열: 전화번호 / D열: 이메일

이메일은 HIRA 등 공공 데이터에 제공되지 않아 빈칸으로 둔다.
"""

import time

import requests
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

SEARCH_URL = "https://www.hira.or.kr/ra/hosp/selectHospSrchKndListAjax.do"
CL_CD_NURSING_HOSPITAL = "28"  # HIRA 종별코드: 요양병원
OUTPUT_FILE = "요양병원_목록.xlsx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://www.hira.or.kr/ra/hosp/getHealthMap.do?pgmid=HIRAA030002000000",
}


def fetch_page(session: requests.Session, page_index: int) -> dict:
    payload = {
        "pageIndex": page_index,
        "clCd": CL_CD_NURSING_HOSPITAL,
        "isDown": "N",
    }
    for attempt in range(4):
        try:
            resp = session.post(SEARCH_URL, data=payload, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError):
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError("unreachable")


def collect_all() -> list[dict]:
    session = requests.Session()
    hospitals: dict[str, dict] = {}

    first = fetch_page(session, 1)
    pagination = first["data"]["paginationInfo"]
    total_pages = pagination["totalPageCount"]
    total_count = pagination["totalRecordCount"]
    print(f"전체 요양병원 수: {total_count} ({total_pages}페이지)")

    page = 1
    while page <= total_pages:
        data = first if page == 1 else fetch_page(session, page)
        for item in data["data"]["hospList"]:
            ykiho = item.get("ykiho") or f"{item.get('yadmNm')}|{item.get('addr')}"
            region = " ".join(
                part for part in (item.get("sidoCdNm"), item.get("sgguCdNm")) if part
            )
            hospitals[ykiho] = {
                "name": (item.get("yadmNm") or "").strip(),
                "region": region.strip(),
                "phone": (item.get("yadmGdTelnoTxt") or "").strip(),
                "email": "",
            }
        print(f"  {page}/{total_pages} 페이지 수집 (누적 {len(hospitals)}건)")
        page += 1
        time.sleep(0.3)

    rows = sorted(hospitals.values(), key=lambda h: (h["region"], h["name"]))
    return rows


def write_excel(rows: list[dict]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "요양병원"

    columns = ["병원명", "지역", "전화번호", "이메일"]
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    for col, title in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col, value=title)
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row_idx, h in enumerate(rows, start=2):
        ws.cell(row=row_idx, column=1, value=h["name"])
        ws.cell(row=row_idx, column=2, value=h["region"])
        ws.cell(row=row_idx, column=3, value=h["phone"])
        ws.cell(row=row_idx, column=4, value=h["email"])

    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 25
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:D{len(rows) + 1}"

    wb.save(OUTPUT_FILE)
    print(f"저장 완료: {OUTPUT_FILE} ({len(rows)}건)")


if __name__ == "__main__":
    write_excel(collect_all())

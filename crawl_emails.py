# -*- coding: utf-8 -*-
"""수집된 기관 홈페이지를 방문해 이메일 주소를 추출한다.

메인 페이지에서 이메일(mailto 링크, 본문 텍스트)을 찾고, 없으면
문의/소개/개인정보처리방침 등 키워드 링크와 프레임 페이지를
최대 4개까지 추가 확인한다.
"""

import html as html_mod
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

import requests
import urllib3

urllib3.disable_warnings()

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
BAD_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js", ".ico", ".woff", ".ttf")
BAD_DOMAIN = ("sentry", "example.", "domain.", "test.com", "localhost", "wixpress", "schema.org", "w3.org", "2x.")
LINK_KEYWORDS = (
    "contact", "문의", "이메일", "e-mail", "email", "인사말", "소개", "오시는",
    "찾아오", "intro", "greet", "about", "개인정보", "privacy", "footer", "sub",
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5",
}


def fetch(session: requests.Session, url: str) -> str:
    resp = session.get(url, timeout=(7, 15), verify=False, headers=HEADERS, allow_redirects=True)
    if len(resp.content) > 3_000_000:
        return ""
    ctype = resp.headers.get("Content-Type", "")
    if ctype and "text" not in ctype and "html" not in ctype:
        return ""
    if not resp.encoding or resp.encoding.lower() in ("iso-8859-1", "ascii"):
        resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def extract_emails(text: str) -> set[str]:
    text = html_mod.unescape(text)
    found = set()
    for raw in EMAIL_RE.findall(text):
        email = raw.strip().strip(".").lower()
        if len(email) > 50 or email.endswith(BAD_EXT):
            continue
        domain = email.split("@", 1)[1]
        if any(bad in domain for bad in BAD_DOMAIN):
            continue
        found.add(email)
    return found


def candidate_links(base_url: str, page: str) -> list[str]:
    links = []
    for m in re.finditer(r"<(?:frame|iframe)[^>]+src=[\"']([^\"']+)[\"']", page, re.I):
        links.append(urljoin(base_url, m.group(1)))
    for m in re.finditer(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", page, re.I | re.S):
        href = m.group(1)
        label = re.sub(r"<[^>]+>", "", m.group(2))
        target = (href + " " + label).lower()
        if not any(k in target for k in LINK_KEYWORDS):
            continue
        url = urljoin(base_url, href)
        if url.lower().startswith(("javascript", "mailto", "tel")):
            continue
        if urlparse(url).netloc != urlparse(base_url).netloc:
            continue
        links.append(url)
    seen, ordered = set(), []
    for url in links:
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered[:4]


def crawl_site(url: str) -> dict:
    session = requests.Session()
    try:
        page = fetch(session, url)
    except Exception:
        return {"emails": [], "status": "접속실패"}
    if not page:
        return {"emails": [], "status": "본문없음"}
    emails = extract_emails(page)
    if not emails:
        for sub in candidate_links(url, page):
            try:
                emails |= extract_emails(fetch(session, sub))
            except Exception:
                continue
            if emails:
                break
    return {"emails": sorted(emails)[:2], "status": "ok"}


def crawl_file(path: str, skip_domains: tuple[str, ...] = ("daangn.com",)) -> dict:
    with open(path, encoding="utf-8") as fp:
        rows = json.load(fp)
    targets = [
        r for r in rows
        if r.get("homepage") and not r.get("email")
        and not any(d in r["homepage"] for d in skip_domains)
    ]
    print(f"{path}: 홈페이지 보유 {len(targets)}건 크롤링", flush=True)

    stats = {"ok": 0, "found": 0, "dead": 0}
    done = 0
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(crawl_site, r["homepage"]): r for r in targets}
        for future in as_completed(futures):
            row = futures[future]
            result = future.result()
            row["email"] = "; ".join(result["emails"])
            row["email_crawl_status"] = result["status"]
            if result["status"] == "ok":
                stats["ok"] += 1
            else:
                stats["dead"] += 1
            if result["emails"]:
                stats["found"] += 1
            done += 1
            if done % 50 == 0 or done == len(targets):
                print(f"  {done}/{len(targets)} (이메일 발견 {stats['found']})", flush=True)

    with open(path, "w", encoding="utf-8") as fp:
        json.dump(rows, fp, ensure_ascii=False)
    print(f"  완료 — 접속 성공 {stats['ok']}, 접속 불가 {stats['dead']}, 이메일 발견 {stats['found']}", flush=True)
    return stats


if __name__ == "__main__":
    for path in (
        "data/yoyang_hospitals_full.json",
        "data/hanbang_metro.json",
        "data/health_stores.json",
        "data/checkup_centers.json",
        "data/localfood_stores.json",
    ):
        crawl_file(path)

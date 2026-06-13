#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
북마클릿 빌더 — store_filler.js → store_filler.min.js + store_filler_install.html 임베드 갱신.

사용:  python3 bookmarklet/build.py

동작:
  1) store_filler.js 읽기 → 단순 minify (블록/라인 주석 제거, 공백 압축)
  2) 'javascript:' 접두 → store_filler.min.js 저장
  3) install.html의 `<a class="bm" href="javascript:...">🏪 ...</a>` 링크 본문 교체
     (가격 등 데이터가 바뀌면 둘 다 자동 반영)
"""
import os
import re
import html

HERE = os.path.dirname(os.path.abspath(__file__))


def minify(src: str) -> str:
    src = re.sub(r"/\*[\s\S]*?\*/", "", src)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.M)
    src = re.sub(r"\s+", " ", src).strip()
    return src


def main():
    js_path = os.path.join(HERE, "store_filler.js")
    min_path = os.path.join(HERE, "store_filler.min.js")
    html_path = os.path.join(HERE, "store_filler_install.html")

    with open(js_path, encoding="utf-8") as f:
        src = f.read()

    minified = minify(src)
    bookmarklet = "javascript:" + minified

    with open(min_path, "w", encoding="utf-8") as f:
        f.write(bookmarklet)
    print(f"wrote {min_path}  ({len(bookmarklet):,} bytes)")

    with open(html_path, encoding="utf-8") as f:
        page = f.read()

    href_value = html.escape(bookmarklet, quote=True)
    pattern = re.compile(
        r'(<a class="bm" href=")[^"]*(">🏪 당근스토어 자동채움</a>)'
    )
    new_page, n = pattern.subn(lambda m: m.group(1) + href_value + m.group(2), page)
    if n == 0:
        raise SystemExit("install.html 의 <a class=\"bm\" ...> 링크를 못 찾았습니다.")
    if new_page != page:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(new_page)
        print(f"updated {html_path}  (link embedded)")
    else:
        print(f"unchanged {html_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
collect.py — 수집 파이프라인 오케스트레이터 (메인 진입점)

두 가지 모드:
  1) 검색 모드: 해시태그로 CC 영상 검색 → 조회수순 정렬 → 상위 N개 메타+댓글 수집
  2) 시드 모드: 사용자가 준 URL들의 메타+댓글만 수집

결과를 output/에 JSON + 인수인계 마크다운으로 저장한다.
마크다운은 youtube-shorts-creator(큐레이션 스킬)의 Stage 0.5부터 바로 이어받는 형식.

사용:
    # 검색 모드
    python collect.py --query "#piano #shorts" --min-views 5000000 --top 8

    # 시드 모드 (URL 직접)
    python collect.py --urls "URL1" "URL2" "URL3"

    # 옵션
    --comments 15     인수인계에 넣을 상위 댓글 수 (기본 15)
    --out DIR         출력 폴더 (기본 ./output)
"""
import sys
import os
import json
import argparse
from datetime import datetime

# 같은 폴더의 모듈 임포트
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search_cc import search as cc_search           # noqa: E402
from fetch_meta import fetch_meta                    # noqa: E402
from fetch_comments import fetch_comments            # noqa: E402


def fmt_int(n):
    return f"{n:,}" if isinstance(n, int) else "미상"


def duration_str(sec):
    return f"{sec//60}:{sec%60:02d}" if isinstance(sec, int) else "미상"


def upload_str(yyyymmdd):
    if not yyyymmdd or len(str(yyyymmdd)) != 8:
        return "미상"
    s = str(yyyymmdd)
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def collect_one(url: str, n_comments: int):
    """한 영상의 메타 + 댓글 수집."""
    meta = fetch_meta(url)
    try:
        comments = fetch_comments(url, max_fetch=100)
    except Exception as e:
        comments = []
        meta["_comment_error"] = str(e)
    meta["top_comments"] = comments[:n_comments]
    return meta


def guess_genre_type(meta: dict) -> str:
    """카테고리/태그로 Type M/P 힌트. 확정은 사람이 한다."""
    cats = " ".join(meta.get("categories") or []).lower()
    tags = " ".join(meta.get("tags") or []).lower()
    blob = cats + " " + tags
    perf_kw = ["music", "piano", "guitar", "drum", "violin", "cover",
               "painting", "drawing", "art", "calligraphy", "performance"]
    if any(k in blob for k in perf_kw):
        return "P(퍼포먼스형 추정)"
    return "M(메시지형 추정)"


def build_handoff_md(items: list, query: str, mode: str) -> str:
    """큐레이션 스킬 Stage 0.5로 넘길 인수인계 마크다운."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []
    lines.append(f"# 🎬 수집 결과 인수인계 — {now}")
    lines.append("")
    lines.append(f"- 수집 모드: {mode}")
    if query:
        lines.append(f"- 검색어: `{query}` (CC 필터 적용)")
    lines.append(f"- 수집 영상 수: {len(items)}")
    lines.append("")
    lines.append("> 이 파일은 youtube-shorts-collector가 자동 생성했습니다.")
    lines.append("> youtube-shorts-creator(큐레이션 스킬)의 **Stage 0.5(장르 분기)부터** 이어받으세요.")
    lines.append("> V/S·조회수·CC·댓글이 이미 채워져 있어 Stage 0의 사용자 수집 단계가 필요 없습니다.")
    lines.append("")

    # CC 아닌 영상 경고
    non_cc = [m for m in items if not m.get("is_creative_commons")]
    if non_cc:
        lines.append("## ⚠️ CC 아님 — 제외 대상")
        for m in non_cc:
            lines.append(f"- {m.get('title')} — 라이선스: {m.get('license')}")
        lines.append("")

    cc_items = [m for m in items if m.get("is_creative_commons")]
    # 조회수순 정렬
    cc_items.sort(key=lambda m: (m.get("view_count") or 0), reverse=True)

    lines.append("## ✅ 후보 영상 (CC, 조회수순)")
    lines.append("")
    lines.append("| 순위 | 제목 | 채널(구독자) | 조회수 | V/S | 길이 | 업로드 | 유형힌트 | CC |")
    lines.append("|-----|------|----------|------|-----|-----|-------|--------|----|")
    for i, m in enumerate(cc_items, 1):
        lines.append(
            f"| {i} | {m.get('title')} | {m.get('channel')}"
            f"({fmt_int(m.get('channel_follower_count'))}) | {fmt_int(m.get('view_count'))} "
            f"| {m.get('vs_ratio')} | {duration_str(m.get('duration_sec'))} "
            f"| {upload_str(m.get('upload_date'))} | {guess_genre_type(m)} | ✅ |"
        )
    lines.append("")

    # 영상별 상세 + 댓글
    lines.append("## 📋 영상별 상세 + 인기 댓글")
    lines.append("")
    for i, m in enumerate(cc_items, 1):
        lines.append(f"### {i}. {m.get('title')}")
        lines.append(f"- URL: {m.get('url')}")
        lines.append(f"- 채널: {m.get('channel')} ({fmt_int(m.get('channel_follower_count'))} 구독자) — {m.get('channel_url')}")
        lines.append(f"- 조회수 {fmt_int(m.get('view_count'))} · 좋아요 {fmt_int(m.get('like_count'))} · V/S {m.get('vs_ratio')}")
        lines.append(f"- 길이 {duration_str(m.get('duration_sec'))} · 업로드 {upload_str(m.get('upload_date'))}")
        lines.append(f"- 라이선스: {m.get('license')}")
        lines.append(f"- 유형 힌트: Type {guess_genre_type(m)} (← Stage 0.5에서 확정)")
        desc = (m.get("description") or "").strip()
        if desc:
            lines.append(f"- 설명(원본, CC 크레딧 작성에 사용): {desc[:300].replace(chr(10), ' ')}")
        lines.append("")
        lines.append("**인기 댓글 (좋아요순) — Stage 3 주제 결정 재료:**")
        lines.append("")
        tcs = m.get("top_comments") or []
        if not tcs:
            err = m.get("_comment_error")
            lines.append(f"- (댓글 없음 또는 수집 실패{': ' + err if err else ''})")
        else:
            lines.append("| 👍 | 💬 | 댓글 |")
            lines.append("|----|----|------|")
            for c in tcs:
                text = (c.get("text") or "").replace("|", "/").replace(chr(10), " ")[:180]
                heart = "❤️" if c.get("is_favorited") else ""
                lines.append(f"| {fmt_int(c.get('like_count'))} {heart} | {c.get('reply_count')} | {text} |")
        lines.append("")

    # 다음 단계 안내
    lines.append("---")
    lines.append("")
    lines.append("## ▶️ 다음: 큐레이션 스킬로 이어가기")
    lines.append("")
    lines.append("1. 위 후보 중 1개 선택 (조회수·V/S·유형 보고)")
    lines.append("2. youtube-shorts-creator 스킬의 **Stage 0.5(장르 분기)** 확정")
    lines.append("3. Stage 1(성공요인) → Stage 3(위 댓글로 주제 결정) → Stage 4(대본) → ... 진행")
    lines.append("4. **CC BY 크레딧**: 각 영상 '설명(원본)'과 채널명을 Stage 7 크레딧 블록에 사용")
    lines.append("")
    lines.append("## ⚖️ 저작권 재확인 (수집기가 판단 못 하는 것)")
    lines.append("- 영상 안의 **배경음악**이 상업 음원이면 CC여도 재업로드 위험 → BGM 교체 필요")
    lines.append("- 음악 연주 영상: **연주 대상 곡**이 저작권 곡인지 확인 (클래식·자작곡 안전)")
    lines.append("- 영상 속 TV·영화·브랜드 로고가 크게 잡히면 주의")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="YouTube 쇼츠 수집 파이프라인")
    ap.add_argument("--query", help="검색 모드: 해시태그 검색어 (예: '#piano #shorts')")
    ap.add_argument("--urls", nargs="+", help="시드 모드: 영상 URL들")
    ap.add_argument("--min-views", type=int, default=0, help="검색 모드 최소 조회수 필터")
    ap.add_argument("--top", type=int, default=8, help="검색 모드: 상세 수집할 상위 N개 (기본 8)")
    ap.add_argument("--search-max", type=int, default=30, help="검색 모드: flat 후보 최대 (기본 30)")
    ap.add_argument("--comments", type=int, default=15, help="인수인계에 넣을 댓글 수 (기본 15)")
    ap.add_argument("--out", default="./output", help="출력 폴더 (기본 ./output)")
    args = ap.parse_args()

    if not args.query and not args.urls:
        ap.error("--query 또는 --urls 중 하나는 필요합니다.")

    os.makedirs(args.out, exist_ok=True)
    items = []

    if args.urls:
        mode = "시드 모드 (URL 직접)"
        print(f"[시드 모드] {len(args.urls)}개 URL 수집 시작...")
        for u in args.urls:
            print(f"  → {u}")
            try:
                items.append(collect_one(u, args.comments))
            except Exception as e:
                print(f"    [실패] {e}")
    else:
        mode = f"검색 모드 (CC 필터, min_views={args.min_views:,})"
        print(f"[검색 모드] '{args.query}' 검색 중...")
        candidates = cc_search(args.query, args.search_max)
        print(f"  후보 {len(candidates)}개 발견. 조회수 정렬 + 상위 {args.top}개 상세 수집...")
        # flat 결과 조회수로 정렬 (None은 뒤로)
        candidates.sort(key=lambda c: (c.get("view_count") or -1), reverse=True)
        picked = 0
        for c in candidates:
            if picked >= args.top:
                break
            # flat 근사 조회수로 선필터 — 기준 미달 영상의 비싼 상세+댓글 수집을 건너뜀
            # (근사값일 수 있으므로 정확한 재확인은 아래 상세 수집에서 한 번 더)
            fvc = c.get("view_count")
            if isinstance(fvc, int) and fvc < args.min_views:
                continue
            print(f"  → {c['url']}  ({c.get('title')})")
            try:
                m = collect_one(c["url"], args.comments)
            except Exception as e:
                print(f"    [실패] {e}")
                continue
            # 최소 조회수 필터 (상세에서 정확한 조회수로 재확인)
            if isinstance(m.get("view_count"), int) and m["view_count"] < args.min_views:
                print(f"    [스킵] 조회수 {m['view_count']:,} < 최소 {args.min_views:,}")
                continue
            items.append(m)
            picked += 1

    if not items:
        print("[결과 없음] 조건에 맞는 영상을 수집하지 못했습니다.")
        return

    # 초까지 포함 — 같은 분에 끝난 연속 실행이 서로 덮어쓰지 않도록
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(args.out, f"collected_{ts}.json")
    md_path = os.path.join(args.out, f"collected_{ts}.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(build_handoff_md(items, args.query or "", mode))

    cc_n = sum(1 for m in items if m.get("is_creative_commons"))
    print("\n[완료]")
    print(f"  수집 {len(items)}개 (CC {cc_n}개)")
    print(f"  JSON  : {json_path}")
    print(f"  인수인계 MD: {md_path}")
    print("\n→ 이제 youtube-shorts-creator 스킬 Stage 0.5부터 이어가세요.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""반자동 업로더 — 만든 숏츠를 '검수 후' YouTube 에 올린다(YouTube Data API v3, OAuth).

설계 철학(권리 안전): **완전 자동 공개 업로드는 일부러 안 한다.**
  1) 사람이 `--list` 로 결과를 훑고 → 2) 올릴 것을 콕 집어 업로드 → 3) 기본 공개범위는 'private'.
  공개(public)는 `--privacy public --confirm` 으로 '의도'를 명시해야만 된다.
  비-CC 소재(쇼츠→쇼츠)는 비공개가 아니면 추가로 `--confirm` 을 요구(잘못된 재업로드 방지).

자격증명(절대 커밋 금지 — output/ 는 *.json gitignore):
  - OAuth 클라이언트 시크릿: --client-secret  또는  env YT_OAUTH_CLIENT_SECRET_FILE
      (Google Cloud Console → 사용자 인증 정보 → 'OAuth 클라이언트 ID'(데스크톱 앱) JSON)
  - 토큰(자동 저장/갱신): --token  또는  env YT_OAUTH_TOKEN_FILE  (기본 output/youtube_token.json)
      CI(headless)에서는 로컬에서 한 번 만든 토큰 JSON 을 secret 으로 주입.

사용 예:
  python youtube-curator/upload.py --list                       # 검수: 안 올린 숏츠 목록
  python youtube-curator/upload.py --upload mukbang_xxx.mp4 --privacy unlisted
  python youtube-curator/upload.py --upload 0 --privacy public --confirm
  python youtube-curator/upload.py --all --privacy private       # 검수 후 남은 것 일괄(비공개)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "output"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def log(m: str) -> None:
    print(f"  {m}", flush=True)


def step(m: str) -> None:
    print(f"\n▶ {m}", flush=True)


# ── 매니페스트 ────────────────────────────────────────────────────────────────
def load_manifest(out_dir: Path) -> tuple[list[dict], Path]:
    path = out_dir / "manifest.json"
    if not path.exists():
        sys.exit(f"매니페스트가 없습니다: {path}  (먼저 큐레이션/쇼츠→쇼츠로 숏츠를 만드세요)")
    return json.loads(path.read_text(encoding="utf-8")), path


def is_cc(entry: dict) -> bool:
    lic = (entry.get("source", {}).get("license") or "").lower()
    return "creative commons" in lic or lic.strip().startswith("cc")


def title_of(entry: dict, out_dir: Path) -> str:
    t = entry.get("title") or entry.get("source", {}).get("title")
    if not t:
        t = Path(entry["short"]).stem.replace("_", " ")
    return t[:95]                       # 유튜브 제목 100자 제한 여유


def description_of(entry: dict, out_dir: Path) -> str:
    """설명란 = 만들 때 써둔 .txt(캡션 + CC/출처표기). 없으면 캡션만."""
    desc = entry.get("desc")
    if desc and (out_dir / desc).exists():
        return (out_dir / desc).read_text(encoding="utf-8").strip()
    return entry.get("caption", "")


def tags_of(entry: dict, out_dir: Path) -> list[str]:
    text = description_of(entry, out_dir) + " " + (entry.get("slug", ""))
    tags = list(dict.fromkeys(re.findall(r"#(\w+)", text)))   # 해시태그 → 태그(중복 제거)
    if entry.get("slug"):
        tags.append(entry["slug"])
    return tags[:15]


def pending(manifest: list[dict], out_dir: Path) -> list[tuple[int, dict]]:
    """아직 업로드 안 했고, 파일이 실제 존재하는 항목만(인덱스 보존)."""
    out = []
    for i, e in enumerate(manifest):
        if e.get("uploaded"):
            continue
        if not (out_dir / e.get("short", "")).exists():
            continue
        out.append((i, e))
    return out


# ── OAuth ─────────────────────────────────────────────────────────────────────
def get_service(client_secret: Path, token: Path, *, no_browser: bool):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        sys.exit("구글 라이브러리가 필요합니다: pip install -r youtube-curator/requirements.txt\n"
                 "(google-api-python-client google-auth-oauthlib google-auth-httplib2)")

    creds = None
    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())                       # 토큰 자동 갱신
        else:
            if not client_secret.exists():
                sys.exit(f"OAuth 클라이언트 시크릿이 없습니다: {client_secret}\n"
                         "Google Cloud Console → OAuth 클라이언트 ID(데스크톱 앱) JSON 을 받아 지정하세요\n"
                         "(--client-secret 또는 env YT_OAUTH_CLIENT_SECRET_FILE).")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            # 로컬은 브라우저로 동의 → 토큰 발급. headless 면 URL 을 출력해 수동 진행.
            creds = flow.run_local_server(port=0, open_browser=not no_browser)
        token.parent.mkdir(parents=True, exist_ok=True)
        token.write_text(creds.to_json(), encoding="utf-8")
        log(f"토큰 저장: {token}  (다음부터 자동 갱신, 커밋 금지)")
    return build("youtube", "v3", credentials=creds)


# ── 업로드 ────────────────────────────────────────────────────────────────────
def upload_one(svc, entry: dict, out_dir: Path, *, privacy: str, category_id: str,
               made_for_kids: bool) -> dict:
    from googleapiclient.http import MediaFileUpload
    video = out_dir / entry["short"]
    body = {
        "snippet": {
            "title": title_of(entry, out_dir),
            "description": description_of(entry, out_dir),
            "tags": tags_of(entry, out_dir),
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }
    media = MediaFileUpload(str(video), chunksize=-1, resumable=True, mimetype="video/mp4")
    req = svc.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            log(f"업로드 {int(status.progress() * 100)}%")
    vid = resp["id"]
    return {"video_id": vid, "url": f"https://youtu.be/{vid}", "privacy": privacy,
            "at": _dt.datetime.now().isoformat(timespec="seconds")}


def select(manifest: list[dict], target: str, out_dir: Path) -> "int | None":
    """--upload 인자(파일명/인덱스)로 매니페스트 항목 인덱스를 찾는다."""
    if target.isdigit():
        i = int(target)
        return i if 0 <= i < len(manifest) else None
    for i, e in enumerate(manifest):
        if e.get("short") == target or Path(e.get("short", "")).stem == target:
            return i
    return None


def main() -> None:
    p = argparse.ArgumentParser(description="만든 숏츠를 검수 후 YouTube 에 올리는 반자동 업로더")
    p.add_argument("--output", type=Path, default=DEFAULT_OUT)
    p.add_argument("--list", action="store_true", help="안 올린 숏츠 목록만 보여줌(검수)")
    p.add_argument("--upload", default="", help="올릴 숏츠(파일명 또는 --list 의 인덱스)")
    p.add_argument("--all", action="store_true", help="검수 후 남은 항목 일괄 업로드")
    p.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private",
                   help="공개범위(기본 private). public 은 --confirm 필수")
    p.add_argument("--confirm", action="store_true", help="공개/비-CC 공개 업로드 '의도' 명시")
    p.add_argument("--category-id", default="24", help="YouTube 카테고리ID(기본 24=엔터테인먼트)")
    p.add_argument("--made-for-kids", action="store_true", help="아동용 콘텐츠 신고")
    p.add_argument("--client-secret", type=Path,
                   default=Path(os.environ.get("YT_OAUTH_CLIENT_SECRET_FILE",
                                               str(DEFAULT_OUT / "client_secret.json"))))
    p.add_argument("--token", type=Path,
                   default=Path(os.environ.get("YT_OAUTH_TOKEN_FILE",
                                               str(DEFAULT_OUT / "youtube_token.json"))))
    p.add_argument("--no-browser", action="store_true", help="브라우저 자동열기 끔(headless)")
    args = p.parse_args()

    manifest, mpath = load_manifest(args.output)
    pend = pending(manifest, args.output)

    # ── 검수 목록 ──
    if args.list or (not args.upload and not args.all):
        step(f"검수 — 업로드 대기 {len(pend)}개 (총 {len(manifest)})")
        if not pend:
            log("대기 중인 숏츠가 없습니다.")
        for i, e in pend:
            badge = "✅CC" if is_cc(e) else "⚠️비-CC"
            log(f"[{i}] {badge}  {title_of(e, args.output)[:46]}")
            log(f"      파일={e['short']}  카테고리={e.get('category', '')}  "
                f"출처={e.get('source', {}).get('url', '')}")
        if not args.list and pend:
            print("\n  올리려면: --upload <인덱스/파일명> [--privacy unlisted] "
                  "(공개는 --privacy public --confirm)")
        return

    # ── 업로드 대상 확정 ──
    if args.all:
        targets = [i for i, _ in pend]
    else:
        idx = select(manifest, args.upload, args.output)
        if idx is None:
            sys.exit(f"해당 숏츠를 찾지 못함: {args.upload}  (--list 로 확인)")
        if manifest[idx].get("uploaded"):
            sys.exit(f"이미 업로드됨: {manifest[idx]['short']} → {manifest[idx]['uploaded']['url']}")
        if not (args.output / manifest[idx]["short"]).exists():
            sys.exit(f"파일이 없습니다: {manifest[idx]['short']}")
        targets = [idx]

    # ── 안전 게이트 ──
    if args.privacy == "public" and not args.confirm:
        sys.exit("공개(public) 업로드는 --confirm 이 필요합니다(검수 확인). 먼저 --privacy unlisted 권장.")
    non_cc = [i for i in targets if not is_cc(manifest[i])]
    if non_cc and args.privacy != "private" and not args.confirm:
        sys.exit(f"비-CC 소재 {len(non_cc)}개를 비공개가 아닌 상태로 올리려면 --confirm 필요"
                 "(원작자 표기·권리 확인 후 진행).")

    svc = get_service(args.client_secret, args.token, no_browser=args.no_browser)

    for i in targets:
        e = manifest[i]
        step(f"업로드 [{i}] {title_of(e, args.output)[:46]}  ({args.privacy})")
        if not is_cc(e):
            log("⚠️ 비-CC 소재 — 설명란 출처표기 포함, 권리/허락 재확인 필수.")
        try:
            info = upload_one(svc, e, args.output, privacy=args.privacy,
                              category_id=args.category_id, made_for_kids=args.made_for_kids)
            e["uploaded"] = info
            mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            log(f"✅ 업로드 완료: {info['url']}  ({args.privacy})")
        except Exception as ex:
            log(f"✖ 실패({e['short']}): {ex}")

    step("완료 — 검수 후 YouTube Studio 에서 최종 공개 전환을 권장합니다.")


if __name__ == "__main__":
    main()

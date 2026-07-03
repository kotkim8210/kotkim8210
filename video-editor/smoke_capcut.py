#!/usr/bin/env python3
"""pycapcut draft 생성 스모크 테스트 — 버전 업그레이드/CapCut 업데이트 전 실행.

3초 무음 테스트 영상을 만들어 draft 를 생성하고, draft_content.json 의 핵심
스키마(tracks·materials·duration)가 존재하는지 확인한다. 통과해도 "최신 CapCut
앱에서 열리는가"는 GUI 확인이 필요하므로, CapCut 메이저 업데이트 후엔 사람이
1회 열어보는 체크를 병행할 것.

실행: python video-editor/smoke_capcut.py   (성공 시 exit 0)
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="capcut_smoke_"))
    src = tmp / "test.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", "color=c=black:s=640x360:d=3:r=30",
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-t", "3", "-c:v", "libx264", "-c:a", "aac", str(src)],
        check=True)

    from export_capcut import export_draft
    draft = export_draft(
        src, draft_dir=tmp / "drafts", name="smoke",
        keeps=[(0.0, 1.2), (1.8, 3.0)],                      # 컷 2세그먼트
        cues=[{"start": 0.2, "end": 1.0, "text": "스모크 테스트 자막"}])

    content = json.loads((draft / "draft_content.json").read_text(encoding="utf-8"))
    tracks = content.get("tracks", [])
    kinds = {t.get("type"): len(t.get("segments", [])) for t in tracks}
    assert kinds.get("video") == 2, f"video 세그먼트 2개 기대, 실제 {kinds}"
    assert kinds.get("text") == 1, f"text 세그먼트 1개 기대, 실제 {kinds}"
    assert content.get("duration", 0) > 2_000_000, "duration(µs) 이상"
    assert "materials" in content, "materials 키 없음"
    assert (draft / "assets" / "test.mp4").exists(), "소재 복사 안 됨"
    print("✅ smoke OK — draft 스키마 정상 (tracks:", kinds, ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())

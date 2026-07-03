#!/usr/bin/env python3
"""무음 컷 + 자막을 'CapCut 프로젝트(draft)'로 내보낸다 — 사람 마무리용 (PyCapCut).

기존 edit_videos.py 가 ffmpeg 로 **최종 mp4 를 구워내는** 헤드리스 경로라면,
이 모듈은 같은 분석(무음 검출·자막 cue)을 **CapCut 초안(draft)** 으로 내보내
크리에이터가 CapCut 에서 컷 경계·자막 스타일·효과를 손질하게 한다.

  ffmpeg 경로  = 대량·무인 자동화 (결과 고정, GUI 불필요)
  CapCut 경로  = 사람 손맛 마무리 (컷이 '비파괴'라 draft 안에서 자유 수정)

비파괴 컷 원리: 조용한 구간을 잘라 붙이는 대신, 남길 구간마다
``VideoSegment(source_timerange=원본구간, target_timerange=타임라인위치)`` 를
연속 배치한다 → CapCut 타임라인에는 이미 컷이 적용돼 있고, 각 컷의
경계를 드래그로 늘리고 줄일 수 있다.

경로(중요):
  - **내 PC에서 실행**(권장, 튜토리얼 방식): ``--draft-dir`` 에 CapCut 초안 폴더를
    지정하면 CapCut 재시작 후 프로젝트 목록에 바로 나타난다.
      Windows: C:/Users/<이름>/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft
      macOS:   ~/Movies/CapCut/User Data/Projects/com.lveditor.draft
  - **서버/샌드박스에서 실행**: 아무 폴더에 draft 를 만들고 통째로 PC 의 위
    폴더로 복사한다. 소재 경로가 달라지므로 CapCut 이 '미디어 재연결(relink)'을
    물으면 draft 안 ``assets/`` 폴더를 지정하면 된다(소재를 draft 에 복사해 두는 이유).

자막: --srt(기존 SRT) 또는 --transcript(transcript.json)에서 가져온다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from edit_videos import (  # noqa: E402 — 무음 분석 재사용(단일 진실 공급원)
    detect_silences,
    ffprobe_duration,
    keep_segments_from_silences,
    log,
    step,
)


def _cues_from_transcript(transcript: dict, max_chars: int = 16) -> "list[dict]":
    """transcript.json(segments) → 자막 cue 목록(문장 비례 분할)."""
    sys.path.insert(0, str(HERE.parent / "content-engine"))
    from clip import _split_by_chars  # 검증된 분할 로직 재사용
    cues: "list[dict]" = []
    for seg in transcript.get("segments", []):
        cues.extend(_split_by_chars(seg.get("text", ""), seg["start"], seg["end"], max_chars))
    return cues


def _write_srt(cues: "list[dict]", path: Path) -> None:
    def ts(x: float) -> str:
        h = int(x // 3600); m = int((x % 3600) // 60)
        s = int(x % 60); ms = int(round((x - int(x)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    out = []
    for i, c in enumerate(cues, 1):
        out.append(f"{i}\n{ts(c['start'])} --> {ts(c['end'])}\n{c['text']}\n")
    path.write_text("\n".join(out), encoding="utf-8")


def _shift_cues_to_cut_timeline(cues: "list[dict]", keeps: "list[tuple[float, float]]") -> "list[dict]":
    """원본 타임코드 cue 를 '컷 적용 후' 타임라인으로 리매핑한다.

    남는 구간만 이어붙인 새 타임라인에서, cue 가 keep 구간과 겹치는 부분만 살린다.
    """
    out: "list[dict]" = []
    offset = 0.0  # 새 타임라인에서 현재 keep 구간이 시작하는 위치
    for a, b in keeps:
        for c in cues:
            s = max(c["start"], a); e = min(c["end"], b)
            if e - s > 0.05:
                out.append({"start": round(offset + (s - a), 3),
                            "end": round(offset + (e - a), 3),
                            "text": c["text"]})
        offset += b - a
    return out


def export_draft(src: Path, *, draft_dir: Path, name: str,
                 keeps: "list[tuple[float, float]]",
                 cues: "list[dict] | None" = None,
                 width: int = 1920, height: int = 1080, fps: int = 30,
                 font_size: float = 8.0, copy_media: bool = True) -> Path:
    """남길 구간(keeps)과 자막(cues)으로 CapCut draft 를 생성한다."""
    import pycapcut as cc

    draft_dir.mkdir(parents=True, exist_ok=True)
    folder = cc.DraftFolder(str(draft_dir))
    script = folder.create_draft(name, width, height, fps=fps, allow_replace=True)
    draft_path = draft_dir / name

    # 소재를 draft 안으로 복사 → draft 폴더만 옮기면 되는 자급자족 구조
    if copy_media:
        assets = draft_path / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        local = assets / src.name
        if not local.exists():
            shutil.copy2(src, local)
        media_path = local
    else:
        media_path = src

    material = cc.VideoMaterial(str(media_path))
    script.add_track(cc.TrackType.video, "video")

    cursor = 0  # 마이크로초
    for a, b in keeps:
        s_us = int(round(a * cc.SEC))
        e_us = min(int(round(b * cc.SEC)), material.duration)  # ffprobe/미디어인포 반올림 차 클램프
        dur = e_us - s_us
        if dur <= 0:
            continue
        seg = cc.VideoSegment(
            material,
            cc.Timerange(cursor, dur),                        # 타임라인 위치
            source_timerange=cc.Timerange(s_us, dur),         # 원본에서 가져올 구간(비파괴)
        )
        script.add_segment(seg, "video")
        cursor += dur

    if cues:
        script.add_track(cc.TrackType.text, "subs")
        style = cc.TextStyle(size=font_size, bold=True, align=1,       # 가운데 정렬
                             color=(1.0, 1.0, 1.0), auto_wrapping=True)
        border = cc.TextBorder(width=20.0)
        for c in cues:
            s = int(round(c["start"] * cc.SEC))
            d = int(round((c["end"] - c["start"]) * cc.SEC))
            if d <= 0:
                continue
            seg = cc.TextSegment(
                c["text"], cc.Timerange(s, d), style=style, border=border,
                clip_settings=cc.ClipSettings(transform_y=-0.75),      # 하단 배치
            )
            script.add_segment(seg, "subs")

    script.save()
    # 이식 안내 파일
    (draft_path / "README_이식방법.txt").write_text(
        "이 폴더는 CapCut 프로젝트(draft)입니다.\n"
        "1) 이 폴더를 통째로 CapCut 초안 폴더에 복사하세요.\n"
        "   Windows: C:/Users/<이름>/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft\n"
        "   macOS:   ~/Movies/CapCut/User Data/Projects/com.lveditor.draft\n"
        "2) CapCut 을 재시작하면 프로젝트 목록에 나타납니다.\n"
        "3) '미디어를 찾을 수 없음'이 뜨면 assets/ 폴더의 파일로 재연결하세요.\n",
        encoding="utf-8")
    return draft_path


def main() -> None:
    p = argparse.ArgumentParser(
        description="무음컷+자막 → CapCut draft (사람 마무리용, 비파괴 컷)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("src", type=Path, help="원본 영상")
    p.add_argument("--draft-dir", type=Path, required=True,
                   help="draft 를 만들 폴더(내 PC면 CapCut 초안 폴더 지정)")
    p.add_argument("--name", default=None, help="프로젝트 이름(기본: 파일명_cut)")
    # 무음 컷 파라미터 — edit_videos.py 와 동일 기본값
    p.add_argument("--noise", default="-30dB")
    p.add_argument("--min-silence", type=float, default=0.6)
    p.add_argument("--margin", type=float, default=0.20)
    p.add_argument("--min-speech", type=float, default=0.20)
    p.add_argument("--no-trim", action="store_true", help="무음컷 없이 통짜로 올린다")
    # 자막
    p.add_argument("--srt", type=Path, help="기존 SRT(원본 타임코드 기준)")
    p.add_argument("--transcript", type=Path, help="transcript.json(원본 타임코드)")
    p.add_argument("--max-chars", type=int, default=16)
    p.add_argument("--font-size", type=float, default=8.0)
    # 캔버스
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--fps", type=int, default=30)
    a = p.parse_args()

    name = a.name or f"{a.src.stem}_cut"
    duration = ffprobe_duration(a.src)

    step("1/3 무음 구간 분석")
    if a.no_trim:
        keeps = [(0.0, duration)]
    else:
        sil = detect_silences(a.src, a.noise, a.min_silence, normalize=True)
        keeps = keep_segments_from_silences(duration, sil, a.margin, a.min_speech)
        cut = duration - sum(b - x for x, b in keeps)
        log(f"남는 구간 {len(keeps)}개 · 잘린 시간 {cut:.1f}s / {duration:.1f}s")

    cues = None
    if a.srt or a.transcript:
        step("2/3 자막 cue 준비")
        if a.transcript:
            tr = json.loads(a.transcript.read_text(encoding="utf-8"))
            raw = _cues_from_transcript(tr, a.max_chars)
        else:
            # 최소 SRT 파서(간단): index/time/text 블록
            raw = []
            blocks = a.srt.read_text(encoding="utf-8").strip().split("\n\n")
            for blk in blocks:
                lines = blk.strip().splitlines()
                if len(lines) >= 2 and "-->" in lines[1]:
                    t1, t2 = [t.strip() for t in lines[1].split("-->")]
                    def sec(t):
                        h, m, rest = t.split(":")
                        s, ms = rest.split(",")
                        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
                    raw.append({"start": sec(t1), "end": sec(t2),
                                "text": " ".join(lines[2:])})
        cues = _shift_cues_to_cut_timeline(raw, keeps)
        log(f"자막 {len(raw)}개 → 컷 반영 후 {len(cues)}개")

    step("3/3 CapCut draft 생성")
    path = export_draft(a.src, draft_dir=a.draft_dir, name=name, keeps=keeps,
                        cues=cues, width=a.width, height=a.height, fps=a.fps,
                        font_size=a.font_size)
    print(f"\n✅ CapCut 프로젝트: {path}")
    print("   → CapCut 초안 폴더로 복사 후 CapCut 재시작 (README_이식방법.txt 참고)")


if __name__ == "__main__":
    main()

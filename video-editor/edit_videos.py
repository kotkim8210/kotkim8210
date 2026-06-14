#!/usr/bin/env python3
"""여러 영상을 자동 편집해 하나로 합치는 파이프라인.

동작 순서
  1) input 폴더의 영상들을 파일 이름 순서로 읽는다.
  2) 각 영상에서 말 없는(조용한) 구간을 자동으로 잘라낸다.   (silencedetect)
  3) 모든 클립을 동일한 규격으로 정규화한 뒤 이름 순서대로 이어 붙인다. (concat)
  4) 합쳐진 영상의 음성을 한국어로 자동 전사한다.            (faster-whisper)
  5) 한국어 자막(.srt)을 영상 위에 입혀 output 폴더에 저장한다. (libass burn-in)

기본 사용법 (저장소 루트에서):
    python video-editor/edit_videos.py

준비물은 video-editor/setup.sh 로 한 번에 설치할 수 있다.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ── 경로 기본값 ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent          # .../video-editor
REPO_ROOT = SCRIPT_DIR.parent                          # 저장소 루트
DEFAULT_INPUT = REPO_ROOT / "input"
DEFAULT_OUTPUT = REPO_ROOT / "output"

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv", ".wmv", ".mpg", ".mpeg", ".ts"}


# ── 작은 유틸 ─────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def step(msg: str) -> None:
    print(f"\n▶ {msg}", flush=True)


def die(msg: str) -> None:
    print(f"\n✖ 오류: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def run(cmd: list[str], *, capture: bool = False, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """명령을 실행한다. capture=True 면 stdout/stderr 를 잡아 반환한다."""
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE,                # stderr 는 항상 잡아서 오류 메시지에 쓴다
        text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-15:]
        raise RuntimeError("명령 실패: " + " ".join(cmd) + "\n" + "\n".join(tail))
    return proc


# ── ffprobe 헬퍼 ──────────────────────────────────────────────────────────────
def ffprobe_duration(path: Path) -> float:
    proc = run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture=True,
    )
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return 0.0


def has_audio_stream(path: Path) -> bool:
    proc = run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
        capture=True,
    )
    return bool(proc.stdout.strip())


# ── 1) 무음 구간 검출 ─────────────────────────────────────────────────────────
_SIL_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SIL_END = re.compile(r"silence_end:\s*(-?[\d.]+)")


def detect_silences(path: Path, noise: str, min_silence: float) -> list[tuple[float, float]]:
    """ffmpeg silencedetect 로 (start, end) 무음 구간 목록을 얻는다."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-af", f"silencedetect=noise={noise}:d={min_silence}", "-f", "null", "-"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    text = proc.stderr or ""
    silences: list[tuple[float, float]] = []
    cur_start: float | None = None
    for line in text.splitlines():
        m = _SIL_START.search(line)
        if m:
            cur_start = float(m.group(1))
            continue
        m = _SIL_END.search(line)
        if m and cur_start is not None:
            silences.append((max(0.0, cur_start), float(m.group(1))))
            cur_start = None
    # 파일 끝까지 이어진 무음(닫히지 않은 구간)
    if cur_start is not None:
        silences.append((max(0.0, cur_start), ffprobe_duration(path)))
    return silences


def keep_segments_from_silences(
    duration: float,
    silences: list[tuple[float, float]],
    margin: float,
    min_speech: float,
) -> list[tuple[float, float]]:
    """무음 구간의 여집합(=말하는 구간)을 구하고 margin 만큼 여유를 둔 뒤 병합한다."""
    if duration <= 0:
        return []
    # 무음의 여집합 = 보존할 구간
    keep: list[tuple[float, float]] = []
    cursor = 0.0
    for s, e in sorted(silences):
        s = max(0.0, min(s, duration))
        e = max(0.0, min(e, duration))
        if s > cursor:
            keep.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < duration:
        keep.append((cursor, duration))

    # 말이 끊기지 않도록 앞뒤에 여유(margin)를 붙인다.
    padded = [(max(0.0, a - margin), min(duration, b + margin)) for a, b in keep]

    # 겹치거나 맞닿는 구간 병합
    merged: list[tuple[float, float]] = []
    for a, b in sorted(padded):
        if merged and a <= merged[-1][1] + 1e-3:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))

    # 너무 짧은 조각(잡음 한 번 튄 것 등) 제거
    return [(a, b) for a, b in merged if (b - a) >= min_speech]


# ── 2) 클립 정규화(+ 무음 컷) ─────────────────────────────────────────────────
def select_expr(segments: list[tuple[float, float]]) -> str:
    return "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in segments)


def process_clip(
    src: Path,
    dst: Path,
    segments: list[tuple[float, float]] | None,
    *,
    width: int,
    height: int,
    fps: int,
) -> None:
    """한 번의 ffmpeg 패스로 (무음 컷 +) 규격 통일을 수행한다.

    segments=None 이면 컷 없이 전체를 정규화한다(오디오가 없는 영상 등).
    """
    audio = has_audio_stream(src)

    vf_chain = []
    af_chain = []
    if segments is not None and segments:
        expr = select_expr(segments)
        vf_chain.append(f"select='{expr}'")
        vf_chain.append("setpts=N/FRAME_RATE/TB")
        if audio:
            af_chain.append(f"aselect='{expr}'")
            af_chain.append("asetpts=N/SR/TB")

    # 비디오 규격 통일: fps 고정 → 비율 유지 축소 → 레터박스 패딩 → SAR/픽셀포맷 고정
    vf_chain += [
        f"fps={fps}",
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
        "setsar=1",
        "format=yuv420p",
    ]

    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(src)]

    if not audio:
        # 오디오가 없으면 무음 트랙을 합성해 규격을 맞춘다(concat 호환성).
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]

    cmd += ["-vf", ",".join(vf_chain)]
    if audio:
        if af_chain:
            cmd += ["-af", ",".join(af_chain + ["aresample=48000:async=1:first_pts=0"])]
        else:
            cmd += ["-af", "aresample=48000:async=1:first_pts=0"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a", "-shortest"]

    cmd += [
        "-r", str(fps),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        str(dst),
    ]
    run(cmd)


# ── 3) 이어 붙이기 ────────────────────────────────────────────────────────────
def concat_clips(clips: list[Path], dst: Path, work: Path) -> None:
    listfile = work / "concat.txt"
    listfile.write_text(
        "".join(f"file '{c.resolve().as_posix()}'\n" for c in clips), encoding="utf-8"
    )
    run([
        "ffmpeg", "-hide_banner", "-y", "-f", "concat", "-safe", "0",
        "-i", str(listfile), "-c", "copy", "-movflags", "+faststart", str(dst),
    ])


# ── 4) 한국어 전사 → SRT ──────────────────────────────────────────────────────
def _srt_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    td = _dt.timedelta(seconds=seconds)
    total_ms = int(round(td.total_seconds() * 1000))
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe_to_srt(
    media: Path,
    srt_path: Path,
    *,
    model_name: str,
    language: str,
    compute_type: str,
) -> int:
    """faster-whisper 로 음성을 전사해 SRT 파일을 만든다. 자막 개수를 반환."""
    from faster_whisper import WhisperModel  # 지연 임포트(설치 안내를 위해)

    log(f"모델 로딩: {model_name} (compute_type={compute_type}) — 최초 1회 다운로드가 있을 수 있음")
    model = WhisperModel(model_name, device="cpu", compute_type=compute_type)

    segments, info = model.transcribe(
        str(media),
        language=language,
        vad_filter=True,                       # 음성 구간 감지로 환청(hallucination) 감소
        vad_parameters={"min_silence_duration_ms": 500},
        beam_size=5,
    )
    log(f"감지 언어: {info.language} (확률 {info.language_probability:.2f})")

    count = 0
    lines: list[str] = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        count += 1
        lines.append(str(count))
        lines.append(f"{_srt_time(seg.start)} --> {_srt_time(seg.end)}")
        lines.append(text)
        lines.append("")
        log(f"[{_srt_time(seg.start)}] {text}")

    srt_path.write_text("\n".join(lines), encoding="utf-8")
    return count


# ── 5) 자막 입히기(번인) ──────────────────────────────────────────────────────
def burn_subtitles(video: Path, srt: Path, dst: Path, *, font: str, font_size: int) -> None:
    """libass(subtitles 필터)로 SRT 를 영상에 태운다. SRT 는 작업 폴더 기준 상대경로로 참조."""
    style = (
        f"FontName={font},FontSize={font_size},"
        "PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,BackColour=&H80000000&,"
        "BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=40"
    )
    # subtitles 필터는 경로의 특수문자에 민감하므로, 작업 폴더에서 파일명만 참조한다.
    run(
        [
            "ffmpeg", "-hide_banner", "-y", "-i", str(video.resolve()),
            "-vf", f"subtitles={srt.name}:force_style='{style}'",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "copy", "-movflags", "+faststart",
            str(dst.resolve()),
        ],
        cwd=srt.parent,
    )


def mux_soft_subtitles(video: Path, srt: Path, dst: Path) -> None:
    """자막을 태우지 않고 소프트 자막 트랙(mov_text)으로 넣는다(--soft-subs)."""
    run([
        "ffmpeg", "-hide_banner", "-y", "-i", str(video), "-i", str(srt),
        "-c", "copy", "-c:s", "mov_text", "-metadata:s:s:0", "language=kor",
        "-movflags", "+faststart", str(dst),
    ])


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main() -> None:
    p = argparse.ArgumentParser(
        description="여러 영상의 무음 구간을 자동으로 잘라 이어 붙이고 한국어 자막을 입힌다.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="원본 영상 폴더")
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="결과물 폴더")
    p.add_argument("--name", default=None, help="결과 파일 이름(미지정 시 시간으로 자동 생성)")
    # 무음 컷 옵션
    p.add_argument("--noise", default="-30dB", help="이보다 작은 소리는 무음으로 간주")
    p.add_argument("--min-silence", type=float, default=0.6, help="이 길이(초) 이상 조용해야 컷 대상")
    p.add_argument("--margin", type=float, default=0.20, help="말 구간 앞뒤로 남길 여유(초)")
    p.add_argument("--min-speech", type=float, default=0.20, help="이보다 짧은 조각은 버림(초)")
    p.add_argument("--no-trim", action="store_true", help="무음 컷을 끄고 합치기만 한다")
    # 규격
    p.add_argument("--width", type=int, default=1920, help="결과 가로 해상도")
    p.add_argument("--height", type=int, default=1080, help="결과 세로 해상도")
    p.add_argument("--fps", type=int, default=30, help="결과 프레임레이트")
    # 자막 옵션
    p.add_argument("--model", default="small",
                   help="faster-whisper 모델: tiny/base/small/medium/large-v3 (클수록 정확·느림)")
    p.add_argument("--language", default="ko", help="전사 언어 코드")
    p.add_argument("--compute-type", default="int8", help="ctranslate2 연산 타입 (int8 권장)")
    p.add_argument("--font", default="NanumGothic", help="자막 폰트 이름(한글 지원 폰트)")
    p.add_argument("--font-size", type=int, default=22, help="자막 글자 크기")
    p.add_argument("--no-subs", action="store_true", help="자막 단계를 건너뛴다")
    p.add_argument("--soft-subs", action="store_true", help="자막을 태우지 않고 트랙으로만 넣는다")
    p.add_argument("--keep-work", action="store_true", help="중간 산출물(작업 폴더)을 지우지 않는다")
    args = p.parse_args()

    # 의존성 점검
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            die(f"{tool} 가 필요합니다. 먼저 'bash video-editor/setup.sh' 를 실행하세요.")

    args.input.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)

    videos = sorted(
        [f for f in args.input.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXTS],
        key=lambda f: f.name.lower(),
    )
    if not videos:
        die(f"입력 영상이 없습니다. '{args.input}' 폴더에 영상을 넣어주세요.")

    step(f"입력 영상 {len(videos)}개 (이름 순서)")
    for v in videos:
        log(v.name)

    work = Path(tempfile.mkdtemp(prefix="videoedit_", dir=str(args.output)))
    try:
        # ── 클립별: 무음 컷 + 정규화 ──
        processed: list[Path] = []
        for idx, v in enumerate(videos, 1):
            step(f"[{idx}/{len(videos)}] 처리: {v.name}")
            dur = ffprobe_duration(v)
            segments: list[tuple[float, float]] | None
            if args.no_trim or not has_audio_stream(v):
                segments = None
                if not args.no_trim:
                    log("오디오 없음 → 무음 컷 생략, 전체 사용")
            else:
                silences = detect_silences(v, args.noise, args.min_silence)
                segments = keep_segments_from_silences(dur, silences, args.margin, args.min_speech)
                kept = sum(b - a for a, b in segments)
                log(f"무음 {len(silences)}곳 검출 → {dur:.1f}s 중 {kept:.1f}s 유지 "
                    f"({(1 - kept / dur) * 100:.0f}% 컷)" if dur else "구간 분석 완료")
                if not segments:
                    log("말하는 구간이 없어 이 영상은 건너뜁니다.")
                    continue

            out_clip = work / f"clip_{idx:03d}.mp4"
            process_clip(v, out_clip, segments, width=args.width, height=args.height, fps=args.fps)
            processed.append(out_clip)

        if not processed:
            die("편집 후 남은 영상이 없습니다. --noise/--min-silence 값을 조정해 보세요.")

        # ── 이어 붙이기 ──
        step(f"{len(processed)}개 클립 이어 붙이기")
        merged = work / "merged.mp4"
        if len(processed) == 1:
            shutil.copy(processed[0], merged)
        else:
            concat_clips(processed, merged, work)
        log(f"합본 길이: {ffprobe_duration(merged):.1f}s")

        # ── 결과 파일명 ──
        stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        base = args.name or f"edited_{stamp}"
        final = args.output / f"{base}.mp4"

        # ── 자막 ──
        if args.no_subs:
            step("자막 단계 생략 → 합본 저장")
            shutil.copy(merged, final)
        else:
            step("한국어 자막 자동 생성")
            srt = work / "subtitles.srt"
            n = transcribe_to_srt(
                merged, srt,
                model_name=args.model, language=args.language, compute_type=args.compute_type,
            )
            # SRT 도 결과 폴더에 보관
            srt_out = args.output / f"{base}.srt"
            shutil.copy(srt, srt_out)
            log(f"자막 {n}개 생성 → {srt_out.name}")

            if n == 0:
                log("전사된 음성이 없어 자막 없이 저장합니다.")
                shutil.copy(merged, final)
            elif args.soft_subs:
                step("소프트 자막 트랙으로 합치기")
                final = args.output / f"{base}.mp4"
                mux_soft_subtitles(merged, srt, final)
            else:
                step("영상에 자막 입히기(번인)")
                burn_subtitles(merged, srt, final, font=args.font, font_size=args.font_size)

        step("완료 🎬")
        log(f"결과물: {final}")
        print(flush=True)

    finally:
        if args.keep_work:
            log(f"작업 폴더 보존: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        die(str(e))
    except KeyboardInterrupt:
        die("사용자 중단")

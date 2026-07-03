#!/usr/bin/env bash
# 영상 자동 편집기에 필요한 준비물 설치 스크립트
#   - ffmpeg / ffprobe   (영상 처리)
#   - 한글 폰트(나눔고딕) (자막 번인)
#   - faster-whisper      (한국어 음성 → 자막)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "▶ 시스템 의존성 설치 (ffmpeg + 한글 폰트)"
if command -v apt-get >/dev/null 2>&1; then
  SUDO=""
  [ "$(id -u)" -ne 0 ] && SUDO="sudo"
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq ffmpeg fonts-nanum
elif command -v brew >/dev/null 2>&1; then
  brew install ffmpeg
  # macOS 에는 'Apple SD Gothic Neo' 한글 폰트가 기본 내장되어 있다.
  # 자막이 깨지면 실행 시 --font "AppleSDGothicNeo-Regular" 를 넣어보세요.
  echo "  (macOS: 한글 폰트는 시스템 기본 폰트를 사용합니다)"
elif command -v dnf >/dev/null 2>&1; then
  SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
  $SUDO dnf install -y ffmpeg google-noto-sans-cjk-fonts || true
else
  echo "  ⚠ 패키지 관리자를 찾지 못했습니다. ffmpeg 와 한글 폰트를 직접 설치하세요."
fi

echo "▶ 파이썬 패키지 설치 (faster-whisper)"
python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
python3 -m pip install -r "$HERE/requirements.txt"

echo
echo "✅ 설치 완료. 사용법:"
echo "   1) input 폴더에 영상을 넣는다"
echo "   2) python video-editor/edit_videos.py"
echo "   3) output 폴더에서 결과물을 확인한다"

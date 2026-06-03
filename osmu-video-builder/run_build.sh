#!/usr/bin/env bash
# n8n Execute Command 용 래퍼: 자산 준비 후 영상 조립까지.
# 사용: bash run_build.sh <config.json> [era]
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="${1:?config.json 경로 필요}"
ERA="${2:-17c}"
cd "$DIR"
python3 auto.py "$CONFIG" --era "$ERA" --build

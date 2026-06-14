#!/usr/bin/env bash
# n8n Execute Command 용 래퍼: 준비 단계(고증→TTS교정→프롬프트) + 현황판.
# 사용: bash run_prep.sh <config.json> [era]
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="${1:?config.json 경로 필요}"
ERA="${2:-17c}"
cd "$DIR"
python3 auto.py "$CONFIG" --era "$ERA"

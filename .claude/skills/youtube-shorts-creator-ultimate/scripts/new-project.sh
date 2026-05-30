#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: bash scripts/new-project.sh project-name"
  exit 1
fi

NAME="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_DIR="$ROOT/assets/templates"
PROJECT_DIR="$ROOT/projects/$NAME"

if [ -e "$PROJECT_DIR" ]; then
  echo "Project already exists: $PROJECT_DIR" >&2
  exit 1
fi

mkdir -p "$PROJECT_DIR"
cp -R "$TEMPLATE_DIR"/. "$PROJECT_DIR"/
echo "Created project: $PROJECT_DIR"

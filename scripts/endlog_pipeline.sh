#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_SLUG="staffprobot"
AI_ASSISTANT_DIR="${AI_ASSISTANT_DIR:-/home/sa/projects/ai-assistant}"
ITIMPULSE_DIR="${ITIMPULSE_DIR:-/home/sa/projects/itimpulse}"

echo "[endlog] project=$PROJECT_SLUG root=$ROOT"

required_docs=(
  "doc/changelog-entries.md"
  "doc/engineering-log.md"
  "doc/changelog-public.ru.md"
  "doc/changelog-public.en.md"
  "doc/portfolio-engineering.ru.md"
  "doc/portfolio-engineering.en.md"
  "doc/product-overview.ru.md"
  "doc/product-overview.en.md"
  "doc/system-map.md"
  "project-manifest.yaml"
)

missing=0
for rel in "${required_docs[@]}"; do
  if [[ ! -f "$ROOT/$rel" ]]; then
    echo "[endlog][error] missing: $rel" >&2
    missing=1
  fi
done
if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

# Regenerate engineering log if generator is present.
if [[ -x "$ROOT/scripts/build_engineering_log.sh" ]]; then
  bash "$ROOT/scripts/build_engineering_log.sh"
fi

if [[ -f "$ROOT/scripts/build_engineering_log.php" ]]; then
  php "$ROOT/scripts/build_engineering_log.php"
fi

# AI knowledge extraction hook (phase 2+).
if [[ -f "$AI_ASSISTANT_DIR/scripts/extract_knowledge.sh" ]]; then
  bash "$AI_ASSISTANT_DIR/scripts/extract_knowledge.sh" "$PROJECT_SLUG" "$ROOT"
fi

# Portfolio sync hook (phase 2+).
if [[ -f "$ITIMPULSE_DIR/scripts/sync_projects_docs.php" ]]; then
  php "$ITIMPULSE_DIR/scripts/sync_projects_docs.php" --project "$PROJECT_SLUG"
fi

echo "[endlog] done"

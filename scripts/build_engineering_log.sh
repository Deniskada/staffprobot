#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/doc/changelog-entries.md"
DST="$ROOT/doc/engineering-log.md"
[[ -r "$SRC" ]] || { echo "Missing: $SRC" >&2; exit 1; }
python3 "$ROOT/scripts/build_engineering_log.py" "$SRC" "$DST"

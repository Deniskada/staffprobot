#!/usr/bin/env python3
"""Собирает engineering-log.md из changelog-entries.md."""
import re
import sys

src_path = sys.argv[1]
dst_path = sys.argv[2]

with open(src_path, encoding="utf-8") as f:
    raw = f.read()

chunks = re.split(r"\n---\s*\n", raw.strip())
entries = []
for block in chunks:
    block = block.strip()
    if not block:
        continue
    m = re.search(r"^##\s+(\d{4})\s+[—\-]\s+(.+)$", block, re.MULTILINE)
    if m:
        entries.append((int(m.group(1)), m.group(2).strip(), block))

entries.sort(key=lambda e: (-e[0], e[1].lower()))

out = """# Engineering log

Generated from `doc/changelog-entries.md`.
Run: `python3 scripts/build_engineering_log.py doc/changelog-entries.md doc/engineering-log.md`

---

"""

for _, _, block in entries:
    out += block + "\n\n---\n\n"

with open(dst_path, "w", encoding="utf-8") as f:
    f.write(out)

print(f"Written: {dst_path} - {len(entries)} entries")

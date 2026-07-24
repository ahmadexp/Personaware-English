#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repository_root"

python3 -m py_compile scripts/*.py

python3 - <<'PY'
from pathlib import Path

image = Path("dist/Personaware-English.img")
expected_size = 4 * 1024 * 1024

if image.stat().st_size != expected_size:
    raise SystemExit(
        f"{image}: expected {expected_size} bytes, found {image.stat().st_size}"
    )

with image.open("rb") as stream:
    stream.seek(510)
    signature = stream.read(2)

if signature != b"\x55\xaa":
    raise SystemExit(f"{image}: missing MBR signature")

table = Path("resources/name-translations.tsv")
rows = table.read_text(encoding="utf-8").splitlines()
if len(rows) != 425:
    raise SystemExit(f"{table}: expected 425 translation pairs, found {len(rows)}")

for number, row in enumerate(rows, 1):
    fields = row.split("\t")
    if len(fields) != 2 or not all(fields):
        raise SystemExit(f"{table}:{number}: expected two non-empty TSV fields")
    fields[1].encode("ascii")

print(f"Verified {image} ({expected_size} bytes, valid MBR signature)")
print(f"Verified {table} ({len(rows)} reviewed source-name translations)")
PY

(
  cd dist
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c SHA256SUMS.txt
  else
    shasum -a 256 -c SHA256SUMS.txt
  fi
)

echo "Release verification passed."

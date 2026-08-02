#!/bin/sh
set -eu

repository_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repository_root"

./scripts/build_dos.sh
python3 scripts/build_cf_installer.py

python3 - <<'PY'
import hashlib
from pathlib import Path

directory = Path("dist")
names = (
    "Personaware-English.img",
    "PersonaWare-English-CF-Installer.zip",
)
lines = []
for name in names:
    digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
    lines.append(f"{digest}  {name}")
(directory / "SHA256SUMS.txt").write_text(
    "\n".join(lines) + "\n", encoding="ascii"
)
PY

./scripts/verify_release.sh

#!/bin/sh
set -eu

repository_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repository_root"

./scripts/build_dos.sh
python3 scripts/build_enhanced_image.py
python3 scripts/build_cf_installer.py
python3 scripts/build_screenshot_archive.py

python3 - <<'PY'
import hashlib
from pathlib import Path

directory = Path("dist")
names = (
    "Personaware-English-2.0.img",
    "PersonaWare-English-2.0.1-CF-Installer.zip",
    "PersonaWare-English-2.0-Screenshots.zip",
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

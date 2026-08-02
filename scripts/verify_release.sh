#!/bin/sh
set -eu

repository_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repository_root"

for command in python3 nasm mcopy mtype mdir; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Missing required command: $command" >&2
    exit 1
  fi
done
if ! command -v magick >/dev/null 2>&1 && ! command -v convert >/dev/null 2>&1; then
  echo "Missing required command: ImageMagick (magick or convert)" >&2
  exit 1
fi

python3 -m py_compile scripts/*.py tests/*.py tools/*.py
./scripts/build_dos.sh
python3 scripts/build_cf_installer.py
python3 scripts/build_screenshot_archive.py
python3 -m unittest discover -s tests -v

python3 - <<'PY'
from pathlib import Path
import zipfile

from scripts.audit_japanese import iter_findings

image = Path("dist/Personaware-English-2.0.img")
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

package = Path("build/cf-installer-v2/PWMINST")
payload = package / "PAYLOAD"
findings = [
    finding
    for local in sorted((payload / "PW" / "DATA").iterdir())
    if local.is_file()
    for finding in iter_findings(local, local.name, 2, True)
]
if findings:
    raise SystemExit(
        f"structured PersonaWare data still contains Japanese: {findings[0]}"
    )
if (payload / "PW" / "SYSTEM" / "IBMZIPC2.ZB").exists():
    raise SystemExit("Japanese-only postal database is present in the CF payload")

config = (payload / "CONFIG.SYS").read_bytes()
autoexec = (payload / "AUTOEXEC.BAT").read_bytes()
ias = (payload / "DOS" / "$IAS.SUB").read_bytes()
if (
    b"COUNTRY=001,437" not in config
    or b"REM DEVICEHIGH=C:\\DOS\\$FONT.SYS" in config
    or b"REM DEVICEHIGH=C:\\DOS\\$DISP.SYS" not in config
    or b"REM DEVICEHIGH=C:\\DOS\\$IAS.SYS" not in config
    or b"REM INSTALL=C:\\DOS\\IBMMKKV.EXE" not in config
):
    raise SystemExit("CF payload is missing the active English DOS configuration")
if b"PATH C:\\;C:\\DOS" not in autoexec or b"PWMODERN" in autoexec:
    raise SystemExit("CF payload has an unexpected internal-disk startup path")
if (
    b"Specify /G=1 for $IAS.SYS. [Enter]" not in ias
    or b"IME Control   Setup   Add Word" not in ias
):
    raise SystemExit("CF payload lacks the translated DOS/V status resource")

installer = Path("dist/PersonaWare-English-2.0-CF-Installer.zip")
with zipfile.ZipFile(installer) as archive:
    names = set(archive.namelist())
for required_name in (
    "PWMINST/INSTALL.BAT",
    "PWMINST/RESTORE.BAT",
    "PWMINST/FORCERST.BAT",
    "PWMINST/RESTDATA.BAT",
    "PWMINST/STARTPW.BAT",
    "PWMINST/PWIMAGE.COM",
    "PWMINST/PWCOPY.COM",
    "PWMINST/STATE.OK",
    "PWMINST/PAYLOAD/PW/PWPHOTO.COM",
    "PWMINST/PAYLOAD/PW/PWPHOTO.TXT",
    "PWMINST/PAYLOAD/PW/PHOTO/STOCK1.BMP",
    "PWMINST/PAYLOAD/PW/PHOTO/STOCK5.BMP",
):
    if required_name not in names:
        raise SystemExit(f"CF installer is missing {required_name}")
if any("MODERN" in name.upper() for name in names):
    raise SystemExit("English installer unexpectedly contains Modern files")

screenshot_archive = Path("dist/PersonaWare-English-2.0-Screenshots.zip")
with zipfile.ZipFile(screenshot_archive) as archive:
    screenshot_names = set(archive.namelist())
for screenshot in (
    "launcher.png",
    "photo-manager-launcher.png",
    "photo-manager-menu.png",
    "address-book-warning.png",
    "address-book-help.png",
    "email-help.png",
    "fax-help.png",
    "dos-command.png",
    "personaware-english-cf-installer.png",
    "personaware-english-cf-restore.png",
):
    expected = f"PersonaWare-English-2.0-Screenshots/{screenshot}"
    if expected not in screenshot_names:
        raise SystemExit(f"screenshot archive is missing {screenshot}")

for screenshot in (
    "personaware-english-cf-installer.png",
    "personaware-english-cf-restore.png",
    "photo-manager-launcher.png",
    "photo-manager-menu.png",
):
    if not (Path("docs/images") / screenshot).is_file():
        raise SystemExit(f"missing runtime screenshot: {screenshot}")

print("Verified the English 2.0 image, Photo Manager, and CF installer")
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

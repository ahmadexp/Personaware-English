#!/usr/bin/env python3
"""Add the DOS photo manager to a PersonaWare English image."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "resources" / "base" / "Personaware-English-1.0.img"
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / "Personaware-English-2.0.img"
PARTITION_OFFSET = 16384

PHOTO_SLOTS = (
    "P_KI01.BMP",
    "P_YAMA01.BMP",
    "P_HANA02.BMP",
    "P_KO01.BMP",
    "P_HANA03.BMP",
)


def run(command: list[str], *, allow_failure: bool = False) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode and not allow_failure:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"{' '.join(command)} failed: {detail}")
    return result


def image_spec(image: Path) -> str:
    return f"{image.resolve()}@@{PARTITION_OFFSET}"


def copy_from_image(image: Path, dos_path: str, destination: Path) -> None:
    run(["mcopy", "-i", image_spec(image), f"::{dos_path}", str(destination)])


def copy_to_image(image: Path, source: Path, dos_path: str) -> None:
    run(["mcopy", "-o", "-i", image_spec(image), str(source), f"::{dos_path}"])


def add_notebook_help(data: bytes) -> bytes:
    if b"11. DOS Photo Manager" in data:
        return data
    marker = b"\x1a" if data.endswith(b"\x1a") else b""
    body = data[: -len(marker)] if marker else data
    if body and not body.endswith(b"\r\n"):
        body += b"\r\n"
    row = (
        b',,"11. DOS Photo Manager",README,"Open DOS from the launcher and '
        b'type PWPHOTO. Import a prepared 190x250, 16-color BMP, then assign '
        b'it to one of the five launcher picture slots. Remove deletes only a '
        b'gallery copy. Restore recovers the original pictures."\r\n'
    )
    return body + row + marker


def disable_inactive_dosv_driver(data: bytes) -> bytes:
    """Disable $DISP.SYS, which rejects the active English code page."""
    active = b"DEVICEHIGH=C:\\DOS\\$DISP.SYS /MSG=OFF"
    inactive = b"REM " + active
    if inactive in data:
        return data
    if data.count(active) != 1:
        raise ValueError("CONFIG.SYS is missing the expected $DISP.SYS line")
    return data.replace(active, inactive, 1)


def photo_help() -> bytes:
    text = """PERSONAWARE DOS PHOTO MANAGER 2.0
==================================

Open DOS from the PersonaWare launcher, then type PWPHOTO and press Enter. The
five native launcher picture slots are shared by the applications. User
pictures are kept in C:\\PW\\PHOTO as USR1.BMP through USR9.BMP.

IMPORT
  Copy a prepared BMP to a DOS drive, run PWPHOTO, and choose Import.
  The file must be an uncompressed 190 by 250 pixel, 16-color Windows BMP.
  Use tools/personaware_photos.py on a modern computer to prepare an ordinary
  PNG, JPEG, GIF, TIFF, or BMP automatically.

ASSIGN
  Assign a gallery number to one of the five active launcher picture slots.
  Restart PersonaWare after assigning or restoring a picture.

REMOVE AND RESTORE
  Remove deletes only the selected USR file. It does not change a currently
  active picture. Restore recovers any or all of the five original pictures.

SAFETY
  STOCK1.BMP through STOCK5.BMP are original-picture backups. Do not delete
  them. Close PersonaWare and keep a disk-image backup before editing an image
  from a modern computer.
"""
    return text.replace("\n", "\r\n").encode("ascii") + b"\x1a"


def build_photo_utility() -> Path:
    source = PROJECT_ROOT / "utilities" / "dos" / "pwphoto.asm"
    output = PROJECT_ROOT / "utilities" / "bin" / "PWPHOTO.COM"
    output.parent.mkdir(parents=True, exist_ok=True)
    run(["nasm", "-f", "bin", str(source), "-o", str(output)])
    return output


def validate_source_image(image: Path) -> None:
    if not image.is_file():
        raise FileNotFoundError(image)
    with image.open("rb") as stream:
        stream.seek(510)
        if stream.read(2) != b"\x55\xaa":
            raise ValueError(f"{image} does not have an MBR signature")
    for name in PHOTO_SLOTS:
        result = run(
            ["mdir", "-i", image_spec(image), f"::/PW/SYSTEM/{name}"],
            allow_failure=True,
        )
        if result.returncode:
            raise ValueError(f"{image} is missing PW/SYSTEM/{name}")


def build_enhanced_image(source: Path, output: Path) -> Path:
    source = source.resolve()
    output = output.resolve()
    validate_source_image(source)
    if source == output:
        raise ValueError("source and output images must be different")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    utility = build_photo_utility()

    run(
        ["mmd", "-i", image_spec(output), "::/PW/PHOTO"],
        allow_failure=True,
    )
    with tempfile.TemporaryDirectory(prefix="pwphoto-image-") as temporary:
        temporary_root = Path(temporary)
        for index, name in enumerate(PHOTO_SLOTS, 1):
            stock = temporary_root / f"STOCK{index}.BMP"
            copy_from_image(output, f"/PW/SYSTEM/{name}", stock)
            copy_to_image(output, stock, f"/PW/PHOTO/STOCK{index}.BMP")

        notebook = temporary_root / "DEFAULT.NTD"
        copy_from_image(output, "/PW/DATA/DEFAULT.NTD", notebook)
        notebook.write_bytes(add_notebook_help(notebook.read_bytes()))
        copy_to_image(output, notebook, "/PW/DATA/DEFAULT.NTD")

        config = temporary_root / "CONFIG.SYS"
        copy_from_image(output, "/CONFIG.SYS", config)
        config.write_bytes(disable_inactive_dosv_driver(config.read_bytes()))
        copy_to_image(output, config, "/CONFIG.SYS")

        help_file = temporary_root / "PWPHOTO.TXT"
        help_file.write_bytes(photo_help())
        copy_to_image(output, help_file, "/PWPHOTO.TXT")

    copy_to_image(output, utility, "/PWPHOTO.COM")
    validate_enhanced_image(output)
    return output


def validate_enhanced_image(image: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="pwphoto-check-") as temporary:
        root = Path(temporary)
        for index in range(1, 6):
            stock = root / f"STOCK{index}.BMP"
            copy_from_image(image, f"/PW/PHOTO/STOCK{index}.BMP", stock)
            data = stock.read_bytes()
            if (
                len(data) != 24118
                or data[:2] != b"BM"
                or int.from_bytes(data[18:22], "little") != 190
                or int.from_bytes(data[22:26], "little") != 250
                or int.from_bytes(data[28:30], "little") != 4
            ):
                raise ValueError(f"invalid STOCK{index}.BMP in {image}")
        utility = root / "PWPHOTO.COM"
        copy_from_image(image, "/PWPHOTO.COM", utility)
        if b"PersonaWare DOS Photo Manager 2.0" not in utility.read_bytes():
            raise ValueError("installed PWPHOTO.COM failed its identity check")
        launcher = root / "MDLAUNCH.CTL"
        copy_from_image(image, "/PW/DATA/MDLAUNCH.CTL", launcher)
        launcher_data = launcher.read_bytes()
        if b"PWPHOTO.COM" in launcher_data or b"Power MGT" not in launcher_data:
            raise ValueError("original Power Management launcher entry was not preserved")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    built = build_enhanced_image(args.source, args.output)
    print(f"Built {built}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

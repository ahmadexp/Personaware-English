#!/usr/bin/env python3
"""Prepare and manage PersonaWare launcher pictures in a disk image."""

from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

WIDTH = 190
HEIGHT = 250
PARTITION_OFFSET = 16384
SLOT_FILES = (
    "P_KI01.BMP",
    "P_YAMA01.BMP",
    "P_HANA02.BMP",
    "P_KO01.BMP",
    "P_HANA03.BMP",
)


def run(
    command: list[str], *, allow_failure: bool = False
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode and not allow_failure:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"{' '.join(command)} failed: {detail}")
    return result


def image_spec(image: Path) -> str:
    return f"{image.resolve()}@@{PARTITION_OFFSET}"


def validate_disk_image(image: Path) -> None:
    if not image.is_file():
        raise FileNotFoundError(image)
    with image.open("rb") as stream:
        stream.seek(510)
        if stream.read(2) != b"\x55\xaa":
            raise ValueError(f"{image} does not have an MBR signature")
    result = run(
        ["mdir", "-i", image_spec(image), "::/PW/PW.BAT"], allow_failure=True
    )
    if result.returncode:
        raise ValueError(f"{image} does not contain PersonaWare at C:\\PW")


def validate_photo_bytes(data: bytes) -> None:
    expected_row_stride = (((WIDTH + 1) // 2) + 3) & ~3
    expected_size = 14 + 40 + 64 + expected_row_stride * HEIGHT
    if len(data) != expected_size:
        raise ValueError(f"expected {expected_size} bytes, found {len(data)}")
    if data[:2] != b"BM":
        raise ValueError("missing BMP signature")
    if struct.unpack_from("<I", data, 2)[0] != len(data):
        raise ValueError("BMP file-size field is incorrect")
    if struct.unpack_from("<I", data, 10)[0] != 118:
        raise ValueError("BMP pixel offset is not 118")
    width, height = struct.unpack_from("<ii", data, 18)
    if (width, height) != (WIDTH, HEIGHT):
        raise ValueError(f"expected {WIDTH}x{HEIGHT}, found {width}x{height}")
    if struct.unpack_from("<H", data, 26)[0] != 1:
        raise ValueError("BMP must use one color plane")
    if struct.unpack_from("<H", data, 28)[0] != 4:
        raise ValueError("BMP must use 4 bits per pixel")
    if struct.unpack_from("<I", data, 30)[0] != 0:
        raise ValueError("BMP must be uncompressed")


def normalize_indexed_bmp(data: bytes) -> bytes:
    """Normalize ImageMagick's 1/4/8-bit BMP to PersonaWare's fixed 4-bit form."""
    if len(data) < 54 or data[:2] != b"BM":
        raise ValueError("ImageMagick did not produce a Windows BMP")
    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    dib_size = struct.unpack_from("<I", data, 14)[0]
    width, signed_height = struct.unpack_from("<ii", data, 18)
    planes, bits_per_pixel = struct.unpack_from("<HH", data, 26)
    compression = struct.unpack_from("<I", data, 30)[0]
    colors_used = struct.unpack_from("<I", data, 46)[0]
    if (width, abs(signed_height), planes, compression) != (WIDTH, HEIGHT, 1, 0):
        raise ValueError("ImageMagick produced an incompatible BMP layout")
    if bits_per_pixel not in (1, 4, 8):
        raise ValueError(f"unsupported indexed BMP depth: {bits_per_pixel}")
    palette_count = colors_used or (1 << bits_per_pixel)
    if not 1 <= palette_count <= 16:
        raise ValueError(f"expected at most 16 palette entries, found {palette_count}")
    palette_start = 14 + dib_size
    palette_end = palette_start + palette_count * 4
    if palette_end > pixel_offset or pixel_offset > len(data):
        raise ValueError("BMP palette or pixel offset is invalid")
    palette = bytearray(data[palette_start:palette_end])
    palette.extend(b"\0" * (64 - len(palette)))

    source_stride = ((WIDTH * bits_per_pixel + 31) // 32) * 4
    target_stride = (((WIDTH + 1) // 2) + 3) & ~3
    source_rows = []
    for row_number in range(HEIGHT):
        start = pixel_offset + row_number * source_stride
        row = data[start : start + source_stride]
        if len(row) != source_stride:
            raise ValueError("BMP pixel data is truncated")
        indices = []
        for x in range(WIDTH):
            if bits_per_pixel == 1:
                index = (row[x // 8] >> (7 - (x % 8))) & 1
            elif bits_per_pixel == 4:
                value = row[x // 2]
                index = (value >> 4) & 0x0F if x % 2 == 0 else value & 0x0F
            else:
                index = row[x]
            if index >= palette_count:
                raise ValueError("BMP pixel references an unavailable palette entry")
            indices.append(index)
        source_rows.append(indices)
    if signed_height < 0:
        source_rows.reverse()

    target_rows = bytearray()
    for indices in source_rows:
        row = bytearray(
            (indices[x] << 4) | indices[x + 1] for x in range(0, WIDTH, 2)
        )
        row.extend(b"\0" * (target_stride - len(row)))
        target_rows.extend(row)

    target_offset = 14 + 40 + 64
    file_size = target_offset + len(target_rows)
    header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, target_offset)
    info = struct.pack(
        "<IiiHHIIiiII",
        40,
        WIDTH,
        HEIGHT,
        1,
        4,
        0,
        len(target_rows),
        2835,
        2835,
        16,
        16,
    )
    return header + info + bytes(palette) + bytes(target_rows)


def prepare_photo(source: Path, destination: Path, fit: str = "crop") -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    magick = shutil.which("magick") or shutil.which("convert")
    if not magick:
        raise RuntimeError("ImageMagick is required to prepare launcher pictures")
    destination.parent.mkdir(parents=True, exist_ok=True)
    geometry = f"{WIDTH}x{HEIGHT}^" if fit == "crop" else f"{WIDTH}x{HEIGHT}"
    with tempfile.TemporaryDirectory(prefix="pwphoto-convert-") as temporary:
        converted = Path(temporary) / "prepared.bmp"
        run(
            [
                magick,
                str(source),
                "-auto-orient",
                "-resize",
                geometry,
                "-gravity",
                "center",
                "-background",
                "black",
                "-extent",
                f"{WIDTH}x{HEIGHT}",
                "-dither",
                "FloydSteinberg",
                "-colors",
                "16",
                "-type",
                "Palette",
                "-compress",
                "none",
                f"BMP3:{converted}",
            ]
        )
        normalized = normalize_indexed_bmp(converted.read_bytes())
        validate_photo_bytes(normalized)
        destination.write_bytes(normalized)
    return destination


def dos_file_exists(image: Path, dos_path: str) -> bool:
    return (
        run(
            ["mdir", "-i", image_spec(image), f"::{dos_path}"],
            allow_failure=True,
        ).returncode
        == 0
    )


def ensure_photo_manager(image: Path) -> None:
    if not dos_file_exists(image, "/PWPHOTO.COM"):
        raise ValueError(
            "this image does not contain Photo Manager; build the 2.0 image first"
        )


def copy_from_image(image: Path, dos_path: str, destination: Path) -> None:
    run(["mcopy", "-i", image_spec(image), f"::{dos_path}", str(destination)])


def copy_to_image(image: Path, source: Path, dos_path: str) -> None:
    run(["mcopy", "-o", "-i", image_spec(image), str(source), f"::{dos_path}"])


def find_free_gallery_number(image: Path) -> int:
    for number in range(1, 10):
        if not dos_file_exists(image, f"/PW/PHOTO/USR{number}.BMP"):
            return number
    raise ValueError("the nine-picture user gallery is full")


def list_gallery(image: Path) -> list[int]:
    return [
        number
        for number in range(1, 10)
        if dos_file_exists(image, f"/PW/PHOTO/USR{number}.BMP")
    ]


def copy_inside_image(image: Path, source: str, destination: str) -> None:
    with tempfile.TemporaryDirectory(prefix="pwphoto-copy-") as temporary:
        local = Path(temporary) / Path(source).name
        copy_from_image(image, source, local)
        copy_to_image(image, local, destination)


def add_photo(
    image: Path, source: Path, fit: str = "crop", slot: int | None = None
) -> int:
    number = find_free_gallery_number(image)
    with tempfile.TemporaryDirectory(prefix="pwphoto-add-") as temporary:
        prepared = prepare_photo(source, Path(temporary) / f"USR{number}.BMP", fit)
        copy_to_image(image, prepared, f"/PW/PHOTO/USR{number}.BMP")
    if slot is not None:
        assign_photo(image, number, slot)
    return number


def remove_photo(image: Path, number: int) -> None:
    path = f"/PW/PHOTO/USR{number}.BMP"
    if not dos_file_exists(image, path):
        raise ValueError(f"gallery picture {number} is not installed")
    run(["mdel", "-i", image_spec(image), f"::{path}"])


def assign_photo(image: Path, number: int, slot: int) -> None:
    source = f"/PW/PHOTO/USR{number}.BMP"
    if not dos_file_exists(image, source):
        raise ValueError(f"gallery picture {number} is not installed")
    copy_inside_image(image, source, f"/PW/SYSTEM/{SLOT_FILES[slot - 1]}")


def restore_photo(image: Path, slot: int | None) -> None:
    slots = range(1, 6) if slot is None else (slot,)
    for number in slots:
        source = f"/PW/PHOTO/STOCK{number}.BMP"
        if not dos_file_exists(image, source):
            raise ValueError(f"original picture backup STOCK{number}.BMP is missing")
        copy_inside_image(image, source, f"/PW/SYSTEM/{SLOT_FILES[number - 1]}")


def create_backup(image: Path, backup: Path | None) -> Path:
    destination = backup or image.with_name(f"{image.name}.before-photo-change")
    if destination.exists():
        raise FileExistsError(
            f"refusing to overwrite existing backup: {destination}"
        )
    shutil.copy2(image, destination)
    return destination


def bounded_number(text: str, minimum: int, maximum: int) -> int:
    value = int(text)
    if not minimum <= value <= maximum:
        raise argparse.ArgumentTypeError(
            f"number must be between {minimum} and {maximum}"
        )
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="convert an image to native BMP")
    prepare.add_argument("source", type=Path)
    prepare.add_argument("output", type=Path)
    prepare.add_argument("--fit", choices=("crop", "contain"), default="crop")

    for name in ("list", "add", "remove", "assign", "restore"):
        command = subparsers.add_parser(name)
        command.add_argument("image", type=Path)
        if name != "list":
            command.add_argument(
                "--backup",
                type=Path,
                metavar="IMAGE",
                help="make a full image backup before changing it",
            )
        if name == "add":
            command.add_argument("source", type=Path)
            command.add_argument("--fit", choices=("crop", "contain"), default="crop")
            command.add_argument("--slot", type=lambda value: bounded_number(value, 1, 5))
        elif name == "remove":
            command.add_argument("number", type=lambda value: bounded_number(value, 1, 9))
        elif name == "assign":
            command.add_argument("number", type=lambda value: bounded_number(value, 1, 9))
            command.add_argument("slot", type=lambda value: bounded_number(value, 1, 5))
        elif name == "restore":
            command.add_argument("--slot", type=lambda value: bounded_number(value, 1, 5))

    args = parser.parse_args()
    if args.command == "prepare":
        built = prepare_photo(args.source, args.output, args.fit)
        print(f"Prepared {built} ({WIDTH}x{HEIGHT}, 16 colors, uncompressed BMP)")
        return 0

    image = args.image.resolve()
    validate_disk_image(image)
    ensure_photo_manager(image)
    if args.command == "list":
        installed = list_gallery(image)
        print("Installed gallery pictures: " + (", ".join(map(str, installed)) or "none"))
        return 0

    if getattr(args, "backup", None) is not None:
        backup = create_backup(image, args.backup)
        print(f"Backup: {backup}")
    if args.command == "add":
        number = add_photo(image, args.source, args.fit, args.slot)
        print(f"Added gallery picture {number}")
    elif args.command == "remove":
        remove_photo(image, args.number)
        print(f"Removed gallery picture {args.number}")
    elif args.command == "assign":
        assign_photo(image, args.number, args.slot)
        print(f"Assigned gallery picture {args.number} to launcher slot {args.slot}")
    elif args.command == "restore":
        restore_photo(image, args.slot)
        print("Restored all original launcher pictures" if args.slot is None else f"Restored launcher slot {args.slot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

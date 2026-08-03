#!/usr/bin/env python3
"""Build a physical-PC110 installer from that machine's verified D: backup."""

from __future__ import annotations

import argparse
import math
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

try:
    from scripts.build_cf_installer import (
        ACTIVE_BOOT_FILES,
        PROJECT_ROOT,
        dos_text,
        extract_file,
        extract_tree,
        run,
        write_checksums,
        write_deterministic_zip,
    )
    from scripts.build_hardware_installer import build_hardware_installer
except ModuleNotFoundError:
    from build_cf_installer import (  # type: ignore[no-redef]
        ACTIVE_BOOT_FILES,
        PROJECT_ROOT,
        dos_text,
        extract_file,
        extract_tree,
        run,
        write_checksums,
        write_deterministic_zip,
    )
    from build_hardware_installer import (  # type: ignore[no-redef]
        build_hardware_installer,
    )

SECTOR_SIZE = 512
MANIFEST_MAGIC = b"PWIMG001"
MANIFEST_FORMAT = "<8sHHII"
MANIFEST_SIZE = struct.calcsize(MANIFEST_FORMAT)
DEFAULT_RELEASE_IMAGE = PROJECT_ROOT / "dist" / "Personaware-English-2.0.img"


def parse_recovery(backup: Path, manifest_path: Path) -> tuple[bytes, int, int]:
    volume = backup.read_bytes()
    manifest = manifest_path.read_bytes()
    if len(manifest) != MANIFEST_SIZE:
        raise ValueError(f"recovery manifest must be {MANIFEST_SIZE} bytes")
    magic, sectors, bps, serial, expected_crc = struct.unpack(
        MANIFEST_FORMAT, manifest
    )
    if magic != MANIFEST_MAGIC:
        raise ValueError("recovery manifest magic is invalid")
    if bps != SECTOR_SIZE or len(volume) != sectors * bps:
        raise ValueError("recovery image length does not match its manifest")
    actual_crc = zlib.crc32(volume) & 0xFFFFFFFF
    if actual_crc != expected_crc:
        raise ValueError(
            f"recovery CRC mismatch: {actual_crc:08X} != {expected_crc:08X}"
        )
    if volume[510:512] != b"\x55\xaa":
        raise ValueError("recovery volume boot signature is missing")
    if struct.unpack_from("<H", volume, 11)[0] != bps:
        raise ValueError("recovery BPB sector size does not match its manifest")
    if struct.unpack_from("<H", volume, 19)[0] != sectors:
        raise ValueError("recovery BPB sector count does not match its manifest")
    if struct.unpack_from("<I", volume, 39)[0] != serial:
        raise ValueError("recovery BPB serial does not match its manifest")
    return volume, sectors, serial


def mtools_output(command: list[str]) -> bytes:
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"{' '.join(command)} failed: {detail}")
    return result.stdout


def apply_payload_to_capture(
    backup: Path, release_image: Path, destination: Path
) -> bytes:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, destination)
    original_boot = backup.read_bytes()[:SECTOR_SIZE]

    with tempfile.TemporaryDirectory(prefix="pwenglish-physical-") as temporary:
        root = Path(temporary)
        source_pw = extract_tree(release_image, "PW", root / "release-pw")
        payload = root / "payload"
        shutil.copytree(source_pw, payload / "PW")
        for name in ACTIVE_BOOT_FILES:
            extract_file(release_image, name, payload / Path(name))

        subprocess.run(
            [
                "mdel",
                "-i",
                str(destination),
                "::/PW/SYSTEM/IBMZIPC2.ZB",
            ],
            capture_output=True,
            check=False,
        )
        run(["mcopy", "-s", "-o", "-i", str(destination), str(payload / "PW"), "::/"])
        for name in ACTIVE_BOOT_FILES:
            run(
                [
                    "mcopy",
                    "-o",
                    "-i",
                    str(destination),
                    str(payload / Path(name)),
                    f"::/{name}",
                ]
            )

        installed = root / "installed"
        installed_pw = installed / "PW"
        installed_pw.parent.mkdir(parents=True, exist_ok=True)
        run(["mcopy", "-s", "-i", str(destination), "::/PW", str(installed)])
        for source in sorted(path for path in (payload / "PW").rglob("*") if path.is_file()):
            relative = source.relative_to(payload / "PW")
            target = installed_pw / relative
            if not target.is_file() or target.read_bytes() != source.read_bytes():
                raise ValueError(f"installed payload did not verify: PW/{relative}")
        for name in ACTIVE_BOOT_FILES:
            target = installed / Path(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            run(["mcopy", "-i", str(destination), f"::/{name}", str(target)])
            if target.read_bytes() != (payload / Path(name)).read_bytes():
                raise ValueError(f"installed payload did not verify: {name}")

    patched = destination.read_bytes()
    if patched[:SECTOR_SIZE] != original_boot:
        raise ValueError("physical PC110 boot sector changed while applying payload")
    return patched


def fat12_length(
    total_sectors: int,
    reserved: int,
    fats: int,
    root_sectors: int,
    cluster_sectors: int,
) -> int:
    """Return a self-consistent FAT12 length for the requested cluster size."""
    fat_sectors = 1
    while True:
        data_sectors = total_sectors - reserved - root_sectors - fats * fat_sectors
        clusters = data_sectors // cluster_sectors
        required = math.ceil(math.ceil((clusters + 2) * 3 / 2) / SECTOR_SIZE)
        if required == fat_sectors:
            return required
        fat_sectors = required


def volume_files(image: Path, destination: Path) -> dict[str, bytes]:
    destination.mkdir(parents=True, exist_ok=True)
    run(["mcopy", "-s", "-m", "-i", str(image), "::*", str(destination)])
    return {
        path.relative_to(destination).as_posix().upper(): path.read_bytes()
        for path in destination.rglob("*")
        if path.is_file()
    }


def volume_attributes(image: Path) -> dict[str, str]:
    listing = mtools_output(["mdir", "-a", "-b", "-s", "-i", str(image), "::*"])
    attributes: dict[str, str] = {}
    for raw_path in listing.decode("utf-8", "replace").splitlines():
        dos_path = raw_path.rstrip("/")
        if not dos_path.startswith("::/"):
            continue
        detail = mtools_output(["mattrib", "-i", str(image), dos_path]).decode(
            "utf-8", "replace"
        )
        marker = detail.find("::/")
        if marker < 0:
            raise ValueError(f"could not read DOS attributes for {dos_path}")
        prefix = detail[:marker].upper()
        attributes[dos_path.upper()] = "".join(
            flag for flag in "AHRS" if flag in prefix
        )
    return attributes


def restore_volume_attributes(image: Path, attributes: dict[str, str]) -> None:
    for dos_path, flags in attributes.items():
        command = [
            "mattrib",
            "-i",
            str(image),
            "-a",
            "-h",
            "-r",
            "-s",
            *[f"+{flag.lower()}" for flag in flags],
            dos_path,
        ]
        run(command)


def contiguous_chain(image: Path, name: str) -> tuple[int, int]:
    output = mtools_output(["mshowfat", "-i", str(image), f"::/{name}"])
    text = output.decode("ascii", "replace").strip()
    prefix = f"::/{name} <"
    if not text.startswith(prefix) or not text.endswith(">") or "> <" in text:
        raise ValueError(f"DOS system file is fragmented: {name}: {text}")
    span = text[len(prefix) : -1]
    if "-" in span:
        first, last = span.split("-", 1)
    else:
        first = last = span
    return int(first), int(last)


def factory_boot_sector(pqi: Path, reference: bytes, sectors: int) -> bytes:
    """Locate the original PC DOS FAT12 VBR embedded in a PowerQuest image."""
    archive = pqi.read_bytes()
    marker = b"\xeb\x3c\x90IBM  7.0"
    matches: list[bytes] = []
    offset = 0
    while True:
        offset = archive.find(marker, offset)
        if offset < 0:
            break
        candidate = archive[offset : offset + SECTOR_SIZE]
        offset += 1
        if len(candidate) != SECTOR_SIZE or candidate[510:512] != b"\x55\xaa":
            continue
        if struct.unpack_from("<H", candidate, 11)[0] != SECTOR_SIZE:
            continue
        if struct.unpack_from("<H", candidate, 19)[0] != sectors:
            continue
        if candidate[13] != reference[13]:
            continue
        if candidate[16] != reference[16]:
            continue
        if struct.unpack_from("<H", candidate, 17)[0] != struct.unpack_from(
            "<H", reference, 17
        )[0]:
            continue
        if struct.unpack_from("<H", candidate, 24)[0] != struct.unpack_from(
            "<H", reference, 24
        )[0]:
            continue
        if struct.unpack_from("<H", candidate, 26)[0] != struct.unpack_from(
            "<H", reference, 26
        )[0]:
            continue
        if struct.unpack_from("<I", candidate, 28)[0] != struct.unpack_from(
            "<I", reference, 28
        )[0]:
            continue
        matches.append(candidate)
    if len(matches) != 1:
        raise ValueError(
            f"expected one matching PC DOS FAT12 boot sector in {pqi}, found {len(matches)}"
        )
    return matches[0]


def rebuild_bootable_volume(
    patched_capture: Path,
    release_image: Path,
    destination: Path,
    sectors: int,
    serial: int,
    boot_drive: int,
    factory_pqi: Path | None = None,
) -> bytes:
    """Repack the capture in the proven PC DOS layout required by its boot code."""
    source = patched_capture.read_bytes()
    reserved = struct.unpack_from("<H", source, 14)[0]
    fats = source[16]
    root_entries = struct.unpack_from("<H", source, 17)[0]
    media = source[21]
    sectors_per_track = struct.unpack_from("<H", source, 24)[0]
    heads = struct.unpack_from("<H", source, 26)[0]
    hidden = struct.unpack_from("<I", source, 28)[0]
    cluster_sectors = source[13]
    if not 0x80 <= boot_drive <= 0xFF:
        raise ValueError("boot drive must be a hard-disk BIOS number")
    root_sectors = math.ceil(root_entries * 32 / SECTOR_SIZE)
    fat_sectors = fat12_length(
        sectors, reserved, fats, root_sectors, cluster_sectors
    )

    if factory_pqi is not None:
        boot_template = factory_boot_sector(factory_pqi, source, sectors)
    else:
        release = release_image.read_bytes()
        if len(release) < SECTOR_SIZE or release[510:512] != b"\x55\xaa":
            raise ValueError("release image does not contain a valid MBR")
        release_partition = struct.unpack_from("<I", release, 446 + 8)[0]
        boot_offset = release_partition * SECTOR_SIZE
        boot_template = release[boot_offset : boot_offset + SECTOR_SIZE]
    if len(boot_template) != SECTOR_SIZE or boot_template[510:512] != b"\x55\xaa":
        raise ValueError("release image does not contain a valid PC DOS boot sector")
    if boot_template[62:510] != source[62:510]:
        raise ValueError("captured volume does not use the expected PC DOS boot code")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pwenglish-pcdos-repack-") as temporary:
        root = Path(temporary)
        extracted = root / "source"
        expected_files = volume_files(patched_capture, extracted)
        expected_attributes = volume_attributes(patched_capture)
        template_path = root / "PCDOS.VBR"
        template_path.write_bytes(boot_template)

        run(
            [
                "mformat",
                "-C",
                "-T",
                str(sectors),
                "-h",
                str(heads),
                "-s",
                str(sectors_per_track),
                "-H",
                str(hidden),
                "-c",
                str(cluster_sectors),
                "-r",
                str(root_sectors),
                "-L",
                str(fat_sectors),
                "-N",
                f"0x{serial:08X}",
                "-m",
                f"0x{media:02x}",
                "-b",
                f"0x{boot_drive:02x}",
                "-B",
                str(template_path),
                "-i",
                str(destination),
                "::",
            ]
        )

        top_level = {path.name.upper(): path for path in extracted.iterdir()}
        system_names = ("IBMBIO.COM", "IBMDOS.COM", "COMMAND.COM")
        for name in system_names:
            if name not in top_level or not top_level[name].is_file():
                raise ValueError(f"captured volume is missing {name}")
            run(["mcopy", "-i", str(destination), str(top_level[name]), f"::/{name}"])

        remaining = [
            str(path)
            for key, path in sorted(top_level.items())
            if key not in system_names
        ]
        if remaining:
            run(["mcopy", "-s", "-m", "-i", str(destination), *remaining, "::/"])

        restore_volume_attributes(destination, expected_attributes)
        for special in ("_RESTORE", "RECYCLED"):
            subprocess.run(
                ["mattrib", "-i", str(destination), "+s", "+h", f"::/{special}"],
                capture_output=True,
                check=False,
            )

        actual_files = volume_files(destination, root / "verified")
        if actual_files != expected_files:
            missing = sorted(expected_files.keys() - actual_files.keys())
            extra = sorted(actual_files.keys() - expected_files.keys())
            changed = sorted(
                key
                for key in expected_files.keys() & actual_files.keys()
                if expected_files[key] != actual_files[key]
            )
            raise ValueError(
                f"repacked volume verification failed; missing={missing}, "
                f"extra={extra}, changed={changed}"
            )

    rebuilt = destination.read_bytes()
    if len(rebuilt) != sectors * SECTOR_SIZE:
        raise ValueError("repacked volume has the wrong byte length")
    if rebuilt[13] != cluster_sectors:
        raise ValueError("repacked volume changed the captured cluster size")
    root_start = (reserved + fats * fat_sectors) * SECTOR_SIZE
    if rebuilt[root_start : root_start + 11] != b"IBMBIO  COM":
        raise ValueError("IBMBIO.COM is not the first root-directory entry")
    if rebuilt[root_start + 32 : root_start + 43] != b"IBMDOS  COM":
        raise ValueError("IBMDOS.COM is not the second root-directory entry")
    bio_first, bio_last = contiguous_chain(destination, "IBMBIO.COM")
    dos_first, _ = contiguous_chain(destination, "IBMDOS.COM")
    if bio_first != 2 or dos_first != bio_last + 1:
        raise ValueError("DOS system files are not contiguous from cluster 2")
    return rebuilt


def physical_readme(
    sectors: int,
    serial: int,
    sectors_per_cluster: int,
    boot_drive: int,
    used_factory_pqi: bool,
) -> bytes:
    return dos_text(
        [
            "PERSONAWARE ENGLISH - MACHINE-SPECIFIC PC110 INSTALLER",
            "=======================================================",
            "",
            "This package was built from this PC110's verified D-ORIG.IMG.",
            f"Target volume: {sectors:,} sectors, serial {serial >> 16:04X}-{serial & 0xffff:04X}.",
            f"Filesystem allocation unit: {sectors_per_cluster * SECTOR_SIZE:,} bytes.",
            f"Boot-time BIOS drive: {boot_drive:02X}h.",
            "",
            "PW-EN.IMG preserves the supplied physical flash capacity, CHS",
            "geometry, serial number, factory utilities, and media-specific files.",
            "It rebuilds FAT12 in the proven PC DOS boot layout: IBMBIO.COM and",
            "IBMDOS.COM are the first root entries and contiguous from cluster 2.",
            "The latest PersonaWare English payload was applied offline and every",
            "installed file was verified byte for byte.",
            *(
                ["The volume boot sector was taken from the original PowerQuest image."]
                if used_factory_pqi
                else []
            ),
            "",
            "INSTALL",
            "  1. Boot the DOS CF as C: with the internal flash volume as D:.",
            "  2. Run C:\\PWMINST\\INSTALL.BAT.",
            "  3. The supplied D-ORIG.IMG is checked without being overwritten.",
            "  4. Type INSTALL only at the final confirmation prompt.",
            "  5. Wait for complete sector read-back verification.",
            "  6. Remove the CF and restart immediately when instructed.",
            "     With the installer CF removed, the internal disk boots as 80h.",
            "",
            "Do not access D: after installation before restarting. DOS still",
            "has the old FAT and directory state cached in memory.",
            "",
            "RECOVERY",
            "  RESTORE.BAT returns D: to the exact supplied D-ORIG.IMG.",
            "  Keep D-ORIG.IMG and D-ORIG.CRC on the CF permanently.",
        ]
    )


def build_from_backup(
    backup: Path,
    recovery_manifest: Path,
    release_image: Path,
    output: Path,
    zip_path: Path,
    boot_drive: int = 0x80,
    factory_pqi: Path | None = None,
) -> Path:
    _, sectors, serial = parse_recovery(backup, recovery_manifest)
    with tempfile.TemporaryDirectory(prefix="pwenglish-physical-build-") as temporary:
        patched_capture = Path(temporary) / "PATCHED.IMG"
        apply_payload_to_capture(backup, release_image, patched_capture)
        rebuilt_path = Path(temporary) / "PW-EN.IMG"
        rebuilt = rebuild_bootable_volume(
            patched_capture,
            release_image,
            rebuilt_path,
            sectors,
            serial,
            boot_drive,
            factory_pqi,
        )
        rebuilt_crc = zlib.crc32(rebuilt) & 0xFFFFFFFF
        patched_manifest = struct.pack(
            MANIFEST_FORMAT, MANIFEST_MAGIC, sectors, SECTOR_SIZE, serial, rebuilt_crc
        )

        package = build_hardware_installer(release_image, output, zip_path)
        (package / "PW-EN.IMG").write_bytes(rebuilt)
        (package / "PW-EN.CRC").write_bytes(patched_manifest)
        (package / "README.TXT").write_bytes(
            physical_readme(
                sectors, serial, rebuilt[13], boot_drive, factory_pqi is not None
            )
        )
        write_checksums(package)
        write_deterministic_zip(package, zip_path)
    return package


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--release-image", type=Path, default=DEFAULT_RELEASE_IMAGE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--zip", dest="zip_path", type=Path, required=True)
    parser.add_argument(
        "--boot-drive",
        type=lambda value: int(value, 0),
        default=0x80,
        help="boot-time BIOS drive number after removing the installer CF (default: 0x80)",
    )
    parser.add_argument(
        "--factory-pqi",
        type=Path,
        help="original PowerQuest image containing the factory PC DOS FAT12 boot sector",
    )
    args = parser.parse_args()
    package = build_from_backup(
        args.backup,
        args.manifest,
        args.release_image,
        args.output,
        args.zip_path,
        args.boot_drive,
        args.factory_pqi,
    )
    print(f"Built {args.zip_path} with {sum(p.is_file() for p in package.iterdir())} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

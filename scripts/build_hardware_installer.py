#!/usr/bin/env python3
"""Build the full-volume installer for a physical IBM Palm Top PC 110."""

from __future__ import annotations

import argparse
import shutil
import struct
import zlib
from pathlib import Path

try:
    from scripts.build_cf_installer import (
        PROJECT_ROOT,
        STATE_MARKER,
        STATE_MARKER_CRC,
        USER_DATABASES,
        build_dos_utilities,
        dos_text,
        force_restore_batch,
        legal_notice,
        restore_batch,
        restore_data_batch,
        start_batch,
        write_checksums,
        write_deterministic_zip,
    )
except ModuleNotFoundError:
    from build_cf_installer import (  # type: ignore[no-redef]
        PROJECT_ROOT,
        STATE_MARKER,
        STATE_MARKER_CRC,
        USER_DATABASES,
        build_dos_utilities,
        dos_text,
        force_restore_batch,
        legal_notice,
        restore_batch,
        restore_data_batch,
        start_batch,
        write_checksums,
        write_deterministic_zip,
    )

DEFAULT_IMAGE = PROJECT_ROOT / "dist" / "Personaware-English-2.0.img"
DEFAULT_OUTPUT = PROJECT_ROOT / "build" / "pc110-hardware-installer-v2"
DEFAULT_ZIP = (
    PROJECT_ROOT
    / "dist"
    / "PersonaWare-English-2.0.2-PC110-Hardware-Installer.zip"
)
OUTPUT_MARKER = ".personaware-hardware-installer-output"
PARTITION_OFFSET = 32 * 512
SECTOR_SIZE = 512
MANIFEST_MAGIC = b"PWIMG001"


def install_batch() -> bytes:
    lines = [
        "@ECHO OFF",
        "CLS",
        "ECHO ==============================================",
        "ECHO  PersonaWare English PC110 Hardware Installer",
        "ECHO ==============================================",
        "ECHO.",
        "C:",
        "IF NOT EXIST C:\\PWMINST\\PWIMAGE.COM GOTO WRONGCF",
        "IF NOT EXIST C:\\PWMINST\\PWCOPY.COM GOTO WRONGCF",
        "IF NOT EXIST C:\\PWMINST\\PW-EN.IMG GOTO WRONGCF",
        "IF NOT EXIST C:\\PWMINST\\PW-EN.CRC GOTO WRONGCF",
        "IF EXIST C:\\PWMINST\\D-ORIG.IMG GOTO VERIFYBACKUP",
        "IF EXIST C:\\PWMINST\\D-ORIG.CRC GOTO INCOMPLETE",
        "IF NOT EXIST D:\\IBMBIO.COM GOTO NOTARGET",
        "IF NOT EXIST D:\\IBMDOS.COM GOTO NOTARGET",
        "ECHO Step 1 of 3: Saving the complete physical PC110 D: volume.",
        "ECHO This can take several minutes. Do not turn the computer off.",
        "C:\\PWMINST\\PWIMAGE.COM /B",
        "IF ERRORLEVEL 1 GOTO BACKUPFAIL",
        "GOTO HAVEIMAGE",
        ":VERIFYBACKUP",
        "IF NOT EXIST C:\\PWMINST\\D-ORIG.CRC GOTO INCOMPLETE",
        "ECHO Checking the existing recovery image before installation.",
        "C:\\PWMINST\\PWIMAGE.COM /Q",
        "IF ERRORLEVEL 1 GOTO INVALIDBACKUP",
        "ECHO The original hardware image is valid and will not be replaced.",
        ":HAVEIMAGE",
        "ECHO.",
        "ECHO Step 2 of 3: Saving the current PersonaWare databases.",
        "IF NOT EXIST C:\\PWMINST\\USERDATA\\COMPLETE.OK GOTO NEWDATA",
        (
            f"C:\\PWMINST\\PWCOPY.COM /C "
            f"C:\\PWMINST\\USERDATA\\COMPLETE.OK {STATE_MARKER_CRC:08X}"
        ),
        "IF ERRORLEVEL 1 GOTO DATAMARKER",
        "GOTO DATAREADY",
        ":NEWDATA",
        "IF NOT EXIST C:\\PWMINST\\USERDATA\\NUL MD C:\\PWMINST\\USERDATA",
        "IF ERRORLEVEL 1 GOTO DATAFAIL",
    ]
    for name in USER_DATABASES:
        label = name.rsplit(".", 1)[1]
        lines.extend(
            [
                f"IF NOT EXIST C:\\PWMINST\\USERDATA\\{name} GOTO COPY{label}",
                f"C:\\PWMINST\\PWCOPY.COM /D C:\\PWMINST\\USERDATA\\{name}",
                "IF ERRORLEVEL 1 GOTO DATAFAIL",
                f":COPY{label}",
                f"IF NOT EXIST D:\\PW\\DATA\\{name} GOTO SKIP{label}",
                (
                    f"C:\\PWMINST\\PWCOPY.COM D:\\PW\\DATA\\{name} "
                    f"C:\\PWMINST\\USERDATA\\{name} -"
                ),
                "IF ERRORLEVEL 1 GOTO DATAFAIL",
                f":SKIP{label}",
            ]
        )
    lines.extend(
        [
            (
                f"C:\\PWMINST\\PWCOPY.COM C:\\PWMINST\\STATE.OK "
                f"C:\\PWMINST\\USERDATA\\COMPLETE.OK {STATE_MARKER_CRC:08X}"
            ),
            "IF ERRORLEVEL 1 GOTO DATAFAIL",
            ":DATAREADY",
            "ECHO.",
            "ECHO Step 3 of 3: Writing the known PC110 English volume to D:.",
            "ECHO The complete image, FAT, root directory, and boot sector",
            "ECHO will be written and then read back for verification.",
            "C:\\PWMINST\\PWIMAGE.COM /I",
            "IF ERRORLEVEL 1 GOTO INSTALLFAIL",
            "ECHO.",
            "ECHO Installation completed. D: is locked until restart.",
            "ECHO Remove the CF and restart the PC110 now.",
            ":WAIT",
            "GOTO WAIT",
            ":WRONGCF",
            "ECHO Required installer files were not found in C:\\PWMINST.",
            "ECHO Nothing was changed.",
            "GOTO ERROR",
            ":NOTARGET",
            "ECHO The original PC110 DOS system files were not found on D:.",
            "ECHO Nothing was changed. Confirm that the internal disk is D:.",
            "GOTO ERROR",
            ":INCOMPLETE",
            "ECHO The CF contains an incomplete recovery-image pair.",
            "ECHO Nothing was changed. Preserve the CF and recovery files.",
            "GOTO ERROR",
            ":INVALIDBACKUP",
            "ECHO The existing recovery image did not pass verification.",
            "ECHO Nothing was changed. Do not delete the recovery files.",
            "GOTO ERROR",
            ":BACKUPFAIL",
            "ECHO The complete D: recovery image could not be created.",
            "ECHO The English image was not installed.",
            "GOTO ERROR",
            ":DATAFAIL",
            "ECHO The optional user-data copy failed.",
            "ECHO The English image was not installed.",
            "GOTO ERROR",
            ":DATAMARKER",
            "ECHO The USERDATA completion marker is damaged.",
            "ECHO The English image was not installed.",
            "GOTO ERROR",
            ":INSTALLFAIL",
            "ECHO Full-volume installation or read-back verification failed.",
            "ECHO Keep this CF. Restart and run RESTORE.BAT before retrying.",
            ":ERROR",
            "ECHO.",
            "ECHO No recovery image was overwritten.",
            ":END",
        ]
    )
    return dos_text(lines)


def readme() -> bytes:
    return dos_text(
        [
            "PERSONAWARE ENGLISH - PHYSICAL PC110 INSTALLER",
            "================================================",
            "",
            "This package is for an actual IBM Palm Top PC 110. It does not",
            "use MiSTer VHD geometry or file-by-file replacement on D:.",
            "PW-EN.IMG is the complete known PC110 logical volume, including",
            "its boot sector, FATs, root directory, DOS system files, and the",
            "latest PersonaWare English 2.0 files.",
            "",
            "REQUIREMENTS",
            "  * Boot DOS from the CF so the CF is C: and internal disk is D:.",
            "  * D: must be the original 8,160-sector PC110 logical volume.",
            "  * Keep reliable external power connected.",
            "  * Keep at least 8 MB free on the CF for the recovery image.",
            "",
            "INSTALL",
            "  1. Run C:\\PWMINST\\INSTALL.BAT.",
            "  2. The installer verifies or creates D-ORIG.IMG first.",
            "  3. At the final warning, type INSTALL and press Enter.",
            "  4. Wait for the complete D: read-back verification.",
            "  5. When told, remove the CF and restart the PC110.",
            "",
            "The installer deliberately stops in a loop after writing D:.",
            "Do not run DIR D:, start PersonaWare, or access D: before restart.",
            "DOS still has the old filesystem cached until the reboot.",
            "",
            "RECOVERY",
            "  D-ORIG.IMG is an exact pre-install copy of the physical D: volume.",
            "  Run RESTORE.BAT from this CF and type YES to restore it.",
            "  FORCERST.BAT is only for a damaged D: boot sector.",
            "  Both paths write the boot sector last and verify every sector.",
            "",
            "USER DATA",
            "  The four default databases are also saved under USERDATA.",
            "  After a successful restart, RESTDATA.BAT may restore them.",
            "  This is optional because they may contain Japanese user text.",
        ]
    )


def extract_volume(image: Path) -> tuple[bytes, bytes]:
    disk = image.read_bytes()
    if len(disk) != 4 * 1024 * 1024:
        raise ValueError(f"expected a 4 MiB PC110 disk image, found {len(disk)} bytes")
    volume = disk[PARTITION_OFFSET:]
    if len(volume) % SECTOR_SIZE:
        raise ValueError("PC110 volume length is not sector aligned")
    if volume[510:512] != b"\x55\xaa":
        raise ValueError("PC110 volume boot signature is missing")
    if struct.unpack_from("<H", volume, 11)[0] != SECTOR_SIZE:
        raise ValueError("PC110 volume does not use 512-byte sectors")
    sectors = len(volume) // SECTOR_SIZE
    bpb_sectors = struct.unpack_from("<H", volume, 19)[0]
    if bpb_sectors != sectors:
        raise ValueError(f"BPB has {bpb_sectors} sectors, expected {sectors}")
    serial = struct.unpack_from("<I", volume, 39)[0]
    crc = zlib.crc32(volume) & 0xFFFFFFFF
    manifest = struct.pack(
        "<8sHHII", MANIFEST_MAGIC, sectors, SECTOR_SIZE, serial, crc
    )
    return volume, manifest


def build_hardware_installer(image: Path, output: Path, zip_path: Path) -> Path:
    if not image.is_file():
        raise FileNotFoundError(image)
    build_dos_utilities()
    volume, manifest = extract_volume(image)

    output = output.resolve()
    forbidden = {Path("/").resolve(), Path.home().resolve(), PROJECT_ROOT.resolve()}
    if output in forbidden:
        raise ValueError(f"refusing unsafe output directory: {output}")
    marker = output / OUTPUT_MARKER
    package = output / "PWMINST"
    if output.exists():
        if not marker.is_file() or marker.read_text(encoding="ascii") != "PWHW1\n":
            raise ValueError(f"refusing to replace unrecognized output: {output}")
        shutil.rmtree(output)
    package.mkdir(parents=True)
    marker.write_text("PWHW1\n", encoding="ascii")

    for name in ("PWCOPY.COM", "PWIMAGE.COM"):
        shutil.copy2(PROJECT_ROOT / "installer" / "bin" / name, package / name)
    (package / "PW-EN.IMG").write_bytes(volume)
    (package / "PW-EN.CRC").write_bytes(manifest)
    (package / "STATE.OK").write_bytes(STATE_MARKER)
    (package / "INSTALL.BAT").write_bytes(install_batch())
    (package / "RESTORE.BAT").write_bytes(restore_batch())
    (package / "FORCERST.BAT").write_bytes(force_restore_batch())
    (package / "RESTDATA.BAT").write_bytes(restore_data_batch())
    (package / "STARTPW.BAT").write_bytes(start_batch())
    (package / "README.TXT").write_bytes(readme())
    (package / "NOTICE.TXT").write_bytes(legal_notice())
    write_checksums(package)
    write_deterministic_zip(package, zip_path)
    return package


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--zip", dest="zip_path", type=Path, default=DEFAULT_ZIP)
    args = parser.parse_args()
    package = build_hardware_installer(args.image, args.output, args.zip_path)
    print(f"Built {args.zip_path} with {sum(p.is_file() for p in package.rglob('*'))} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

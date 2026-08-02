#!/usr/bin/env python3
"""Build the self-contained DOS CF installer and recovery package."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import tempfile
import zipfile
import zlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE = PROJECT_ROOT / "dist" / "Personaware-English-2.0.img"
DEFAULT_OUTPUT = PROJECT_ROOT / "build" / "cf-installer-v2"
DEFAULT_ZIP = PROJECT_ROOT / "dist" / "PersonaWare-English-2.0-CF-Installer.zip"
OUTPUT_MARKER = ".personaware-cf-installer-output"
DOS_NEWLINE = "\r\n"
USER_DATABASES = ("DEFAULT.ADD", "DEFAULT.NTD", "DEFAULT.SCD", "DEFAULT.TDD")
ACTIVE_BOOT_FILES = ("AUTOEXEC.BAT", "CONFIG.SYS", "DOS/$IAS.SUB")
STATE_MARKER = b"PWCF STATE MARKER 1\r\n"
STATE_MARKER_CRC = zlib.crc32(STATE_MARKER) & 0xFFFFFFFF


def dos_text(lines: list[str]) -> bytes:
    return (DOS_NEWLINE.join(lines) + DOS_NEWLINE).encode("ascii")


def run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"{' '.join(command)} failed: {detail}")


def build_dos_utilities() -> None:
    output = PROJECT_ROOT / "installer" / "bin"
    output.mkdir(parents=True, exist_ok=True)
    for source_name, binary_name in (
        ("pwcopy.asm", "PWCOPY.COM"),
        ("pwimage.asm", "PWIMAGE.COM"),
    ):
        run(
            [
                "nasm",
                "-f",
                "bin",
                str(PROJECT_ROOT / "installer" / "dos" / source_name),
                "-o",
                str(output / binary_name),
            ]
        )


def extract_tree(image: Path, name: str, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    run(
        [
            "mcopy",
            "-s",
            "-i",
            f"{image.resolve()}@@16384",
            f"::{name}",
            str(destination),
        ]
    )
    extracted = destination / name
    if not extracted.is_dir():
        raise RuntimeError(f"unable to extract {name} from {image}")
    return extracted


def extract_file(image: Path, name: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "mcopy",
            "-i",
            f"{image.resolve()}@@16384",
            f"::{name}",
            str(destination),
        ]
    )
    if not destination.is_file():
        raise RuntimeError(f"unable to extract {name} from {image}")


def relative_dos_path(path: Path, root: Path) -> str:
    return "\\".join(path.relative_to(root).parts).upper()


def build_file_script(package: Path) -> bytes:
    payload = package / "PAYLOAD"
    directories = sorted(
        (path for path in payload.rglob("*") if path.is_dir()),
        key=lambda path: (len(path.relative_to(payload).parts), str(path)),
    )
    files = sorted(
        (path for path in payload.rglob("*") if path.is_file()),
        key=lambda path: (
            relative_dos_path(path, payload) in {"AUTOEXEC.BAT", "CONFIG.SYS"},
            relative_dos_path(path, payload),
        ),
    )

    lines = ["@ECHO OFF", "SET PWERR=0"]
    for directory in directories:
        target = relative_dos_path(directory, payload)
        lines.extend(
            [
                f"IF NOT EXIST D:\\{target}\\NUL MD D:\\{target}",
                "IF ERRORLEVEL 1 GOTO FAILED",
            ]
        )
    for source in files:
        relative = relative_dos_path(source, package)
        target = relative_dos_path(source, payload)
        expected_crc = zlib.crc32(source.read_bytes()) & 0xFFFFFFFF
        lines.extend(
            [
                (
                    f"C:\\PWMINST\\PWCOPY.COM C:\\PWMINST\\{relative} "
                    f"D:\\{target} {expected_crc:08X}"
                ),
                "IF ERRORLEVEL 1 GOTO FAILED",
            ]
        )
    lines.extend(
        [
            "IF NOT EXIST D:\\PW\\SYSTEM\\IBMZIPC2.ZB GOTO NOZIPDB",
            "C:\\PWMINST\\PWCOPY.COM /D D:\\PW\\SYSTEM\\IBMZIPC2.ZB",
            "IF ERRORLEVEL 1 GOTO FAILED",
            ":NOZIPDB",
            (
                f"C:\\PWMINST\\PWCOPY.COM C:\\PWMINST\\STATE.OK "
                f"C:\\PWMINST\\COPY.OK {STATE_MARKER_CRC:08X}"
            ),
            "IF ERRORLEVEL 1 GOTO FAILED",
            "GOTO DONE",
            ":FAILED",
            "C:\\PWMINST\\PWCOPY.COM /D C:\\PWMINST\\COPY.OK",
            "SET PWERR=1",
            ":DONE",
        ]
    )
    return dos_text(lines)


def install_batch() -> bytes:
    lines = [
        "@ECHO OFF",
        "CLS",
        "ECHO ==============================================",
        "ECHO  PersonaWare English CF Installer",
        "ECHO ==============================================",
        "ECHO.",
        "C:",
        "IF NOT EXIST C:\\PWMINST\\PWIMAGE.COM GOTO WRONGCF",
        "IF NOT EXIST C:\\PWMINST\\PWCOPY.COM GOTO WRONGCF",
        "IF NOT EXIST C:\\PWMINST\\PAYLOAD\\PW\\PW.BAT GOTO WRONGCF",
        "IF EXIST C:\\PWMINST\\D-ORIG.IMG GOTO VERIFYBACKUP",
        "IF EXIST C:\\PWMINST\\D-ORIG.CRC GOTO INCOMPLETE",
        "IF NOT EXIST D:\\PW\\PW.BAT GOTO NOTARGET",
        "ECHO Step 1 of 3: Creating an exact image of the D: volume.",
        "ECHO This can take several minutes. Do not turn the computer off.",
        "C:\\PWMINST\\PWIMAGE.COM /B",
        "IF ERRORLEVEL 1 GOTO BACKUPFAIL",
        "GOTO HAVEIMAGE",
        ":VERIFYBACKUP",
        "IF NOT EXIST C:\\PWMINST\\D-ORIG.CRC GOTO INCOMPLETE",
        "ECHO Checking the existing recovery image before resuming.",
        "C:\\PWMINST\\PWIMAGE.COM /V",
        "IF ERRORLEVEL 1 GOTO INVALIDBACKUP",
        "IF NOT EXIST C:\\PWMINST\\INSTALL.OK GOTO RESUMING",
        f"C:\\PWMINST\\PWCOPY.COM /C C:\\PWMINST\\INSTALL.OK {STATE_MARKER_CRC:08X}",
        "IF ERRORLEVEL 1 GOTO RESUMING",
        "GOTO ALREADY",
        ":RESUMING",
        "ECHO The recovery image is valid. Resuming the installation.",
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
            "ECHO Step 3 of 3: Installing English PersonaWare on D:.",
            "C:\\PWMINST\\PWCOPY.COM /D C:\\PWMINST\\COPY.OK",
            "IF ERRORLEVEL 1 GOTO INSTALLFAIL",
            "CALL C:\\PWMINST\\FILES.BAT",
            'IF "%PWERR%"=="1" GOTO INSTALLFAIL',
            "IF NOT EXIST C:\\PWMINST\\COPY.OK GOTO INSTALLFAIL",
            f"C:\\PWMINST\\PWCOPY.COM /C C:\\PWMINST\\COPY.OK {STATE_MARKER_CRC:08X}",
            "IF ERRORLEVEL 1 GOTO INSTALLFAIL",
            (
                f"C:\\PWMINST\\PWCOPY.COM C:\\PWMINST\\STATE.OK "
                f"C:\\PWMINST\\INSTALL.OK {STATE_MARKER_CRC:08X}"
            ),
            "IF ERRORLEVEL 1 GOTO INSTALLFAIL",
            "ECHO.",
            "ECHO Installation completed and every copied file was verified.",
            "ECHO Start PersonaWare with C:\\PWMINST\\STARTPW.BAT",
            "ECHO Keep this CF safe. It contains your original D: image.",
            "GOTO END",
            ":WRONGCF",
            "ECHO Installer files were not found in C:\\PWMINST.",
            "ECHO Boot DOS from the prepared CF and run this file again.",
            "GOTO ERROR",
            ":NOTARGET",
            "ECHO PersonaWare was not found at D:\\PW\\PW.BAT.",
            "ECHO Nothing was changed. Check the DOS drive letters.",
            "GOTO ERROR",
            ":INCOMPLETE",
            "ECHO The CF contains an incomplete recovery-image pair.",
            "ECHO Nothing was changed. Keep this CF and read README.TXT.",
            "GOTO ERROR",
            ":INVALIDBACKUP",
            "ECHO The existing recovery image did not pass verification.",
            "ECHO Nothing was changed. Do not delete the recovery files.",
            "GOTO ERROR",
            ":ALREADY",
            "ECHO This CF records a completed PersonaWare English install.",
            "ECHO The recovery image remains available in D-ORIG.IMG.",
            "GOTO ERROR",
            ":BACKUPFAIL",
            "ECHO The full D: image could not be created.",
            "ECHO Nothing was installed.",
            "GOTO ERROR",
            ":DATAFAIL",
            "ECHO The optional user-data copy failed.",
            "ECHO Nothing was installed. The full image is still safe.",
            "GOTO ERROR",
            ":DATAMARKER",
            "ECHO The USERDATA completion marker is damaged.",
            "ECHO The full image is safe. Use RESTORE.BAT before retrying.",
            "GOTO ERROR",
            ":INSTALLFAIL",
            "ECHO Installation stopped because a file did not verify.",
            "ECHO The original image is safe. Run RESTORE.BAT if needed.",
            ":ERROR",
            "ECHO.",
            "ECHO No recovery image was overwritten.",
            ":END",
        ]
    )
    return dos_text(lines)


def restore_batch() -> bytes:
    return dos_text(
        [
            "@ECHO OFF",
            "CLS",
            "ECHO ==============================================",
            "ECHO  Restore the Original PersonaWare D: Volume",
            "ECHO ==============================================",
            "ECHO.",
            "C:",
            "IF NOT EXIST C:\\PWMINST\\PWIMAGE.COM GOTO MISSING",
            "IF NOT EXIST C:\\PWMINST\\D-ORIG.IMG GOTO MISSING",
            "IF NOT EXIST C:\\PWMINST\\D-ORIG.CRC GOTO MISSING",
            "C:\\PWMINST\\PWIMAGE.COM /R",
            "IF ERRORLEVEL 1 GOTO FAILED",
            "GOTO WAIT",
            ":MISSING",
            "ECHO The original image and checksum were not found on this CF.",
            "GOTO END",
            ":FAILED",
            "ECHO Restore did not complete. Keep the CF and restart safely.",
            "ECHO DOS access is intentionally locked until restart.",
            ":WAIT",
            "GOTO WAIT",
            ":END",
        ]
    )


def force_restore_batch() -> bytes:
    return dos_text(
        [
            "@ECHO OFF",
            "CLS",
            "ECHO ==============================================",
            "ECHO  Emergency PersonaWare D: Volume Recovery",
            "ECHO ==============================================",
            "ECHO.",
            "C:",
            "ECHO Use this only when RESTORE.BAT reports that D: is invalid.",
            "ECHO The normal size and serial check cannot run in this mode.",
            "ECHO The saved image is still fully verified before any write.",
            "ECHO.",
            "IF NOT EXIST C:\\PWMINST\\PWIMAGE.COM GOTO MISSING",
            "IF NOT EXIST C:\\PWMINST\\D-ORIG.IMG GOTO MISSING",
            "IF NOT EXIST C:\\PWMINST\\D-ORIG.CRC GOTO MISSING",
            "C:\\PWMINST\\PWIMAGE.COM /F",
            "IF ERRORLEVEL 1 GOTO FAILED",
            "GOTO WAIT",
            ":MISSING",
            "ECHO The original image and checksum were not found on this CF.",
            "GOTO END",
            ":FAILED",
            "ECHO Emergency recovery did not complete.",
            "ECHO Keep the CF and restart safely before retrying.",
            "ECHO DOS access is intentionally locked until restart.",
            ":WAIT",
            "GOTO WAIT",
            ":END",
        ]
    )


def restore_data_batch() -> bytes:
    lines = [
        "@ECHO OFF",
        "CLS",
        "ECHO Restoring the four pre-install PersonaWare database files.",
        "ECHO This may restore Japanese user content. PersonaWare must be closed.",
        "IF NOT EXIST D:\\PW\\PW.BAT GOTO FAILED",
    ]
    for name in USER_DATABASES:
        label = name.rsplit(".", 1)[1]
        lines.extend(
            [
                f"IF NOT EXIST C:\\PWMINST\\USERDATA\\{name} GOTO NEXT{label}",
                (
                    f"C:\\PWMINST\\PWCOPY.COM C:\\PWMINST\\USERDATA\\{name} "
                    f"D:\\PW\\DATA\\{name} -"
                ),
                "IF ERRORLEVEL 1 GOTO FAILED",
                f":NEXT{label}",
            ]
        )
    lines.extend(
        [
            "ECHO User databases restored and verified.",
            "GOTO END",
            ":FAILED",
            "ECHO User database restore failed.",
            ":END",
        ]
    )
    return dos_text(lines)


def start_batch() -> bytes:
    return dos_text(
        [
            "@ECHO OFF",
            "SET oPATH=%PATH%",
            "SET METDIR=D:\\PW",
            "SET METDATA=%METDIR%\\DATA",
            "SET PERSONAWARE=1234567",
            "SET PATH=%METDIR%;%PATH%",
            "D:",
            "CD %METDIR%",
            "MET",
            "SET PATH=%oPATH%",
            "SET PERSONAWARE=",
            "SET METDATA=",
            "SET METDIR=",
            "SET oPATH=",
            "C:",
        ]
    )


def readme() -> bytes:
    return dos_text(
        [
            "PERSONAWARE ENGLISH - CF INSTALLER",
            "==================================",
            "",
            "PURPOSE",
            "  INSTALL.BAT installs the fully translated PersonaWare English",
            "  payload on the DOS D: volume after making a complete raw image.",
            "  RESTORE.BAT verifies that image and writes the original volume",
            "  back sector for sector.",
            "",
            "REQUIREMENTS",
            "  * Boot DOS from the CF so the CF is C: and PersonaWare is D:.",
            "  * D:\\PW\\PW.BAT must exist.",
            "  * Use a 386 or newer processor.",
            "  * D: must be FAT12/16, up to 65535 512-byte sectors.",
            "  * The CF must have at least the full size of D: free, plus 3 MB.",
            "  * Connect reliable power. Do not remove media during an operation.",
            "",
            "INSTALL",
            "  1. At the DOS prompt, type C:\\PWMINST\\INSTALL and press Enter.",
            "  2. Wait for all three steps to complete.",
            "  3. Type C:\\PWMINST\\STARTPW to launch PersonaWare from D:.",
            "  4. With the CF removed, the upgraded disk boots normally as C:.",
            "  A valid existing image is verified and can resume an install.",
            "  An incomplete or invalid image pair is preserved and blocks it.",
            "",
            "RESTORE THE COMPLETE ORIGINAL D: VOLUME",
            "  1. Boot DOS from the same CF.",
            "  2. Type C:\\PWMINST\\RESTORE and press Enter.",
            "  3. After validation, type YES only if the displayed target is D:.",
            "  4. Restart immediately when restore completes. Do not access D:.",
            "  If RESTORE says D: is invalid after an interrupted recovery,",
            "  read the guide, use FORCERST.BAT, and type FORCE. This emergency",
            "  mode bypasses target identity, so confirm that the target is D:.",
            "",
            "WHAT IS SAVED",
            "  D-ORIG.IMG is an exact image of the logical DOS D: volume.",
            "  D-ORIG.CRC records its size, volume serial, and CRC-32 checksum.",
            "  The physical disk partition table and MBR are outside that DOS",
            "  volume and are not included. The installer never overwrites an",
            "  existing D-ORIG.IMG.",
            "",
            "USER DATA",
            "  English starter databases are installed to ensure a clean English",
            "  experience. The prior DEFAULT.ADD, .NTD, .SCD, and .TDD files are",
            "  also copied to USERDATA. RESTDATA.BAT can restore only those files.",
            "  Existing user-entered Japanese text is data, so it is preserved but",
            "  is not automatically translated.",
            "  Active English DOS locale files are also installed on D:.",
            "",
            "SAFETY",
            "  Payload CRCs are checked before copying. Copies are read back and",
            "  compared. The volume boot sector is restored last. The full image",
            "  is checked",
            "  before restore, and the restored D: volume is read back and checked.",
            "  If any check fails, keep the CF and restart before retrying.",
        ]
    )


def legal_notice() -> bytes:
    text = (PROJECT_ROOT / "NOTICE.md").read_text(encoding="ascii")
    return dos_text(text.replace("\r\n", "\n").rstrip("\n").split("\n"))


def write_checksums(package: Path) -> None:
    lines = []
    for path in sorted(p for p in package.rglob("*") if p.is_file()):
        if path.name == "SHA256.TXT":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        relative = path.relative_to(package).as_posix().upper()
        lines.append(f"{digest}  {relative}")
    (package / "SHA256.TXT").write_bytes(dos_text(lines))


def write_deterministic_zip(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    timestamp = (2026, 8, 1, 0, 0, 0)
    with zipfile.ZipFile(
        destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
            name = path.relative_to(source.parent).as_posix()
            info = zipfile.ZipInfo(name, timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def build_cf_installer(image: Path, output: Path, zip_path: Path) -> Path:
    if not image.is_file():
        raise FileNotFoundError(image)
    build_dos_utilities()

    output = output.resolve()
    forbidden = {Path("/").resolve(), Path.home().resolve(), PROJECT_ROOT.resolve()}
    if output in forbidden:
        raise ValueError(f"refusing unsafe output directory: {output}")
    marker = output / OUTPUT_MARKER
    package = output / "PWMINST"
    if output.exists():
        if not marker.is_file() or marker.read_text(encoding="ascii") != "PWCF1\n":
            raise ValueError(f"refusing to replace unrecognized output: {output}")
        shutil.rmtree(output)
    package.mkdir(parents=True)
    marker.write_text("PWCF1\n", encoding="ascii")

    with tempfile.TemporaryDirectory(prefix="pwenglish-cf-") as temporary:
        temporary_root = Path(temporary)
        extracted_pw = extract_tree(image, "PW", temporary_root / "pw")
        payload = package / "PAYLOAD"
        shutil.copytree(extracted_pw, payload / "PW")
        for name in ACTIVE_BOOT_FILES:
            extract_file(image, name, payload / Path(name))
    for name in ("PWCOPY.COM", "PWIMAGE.COM"):
        shutil.copy2(PROJECT_ROOT / "installer" / "bin" / name, package / name)
    (package / "STATE.OK").write_bytes(STATE_MARKER)

    (package / "FILES.BAT").write_bytes(build_file_script(package))
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
    package = build_cf_installer(args.image, args.output, args.zip_path)
    file_count = sum(1 for path in package.rglob("*") if path.is_file())
    print(f"Built {args.zip_path} with {file_count} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

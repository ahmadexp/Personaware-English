#!/usr/bin/env python3
"""Build the deterministic PersonaWare English screenshot archive."""

from __future__ import annotations

import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "docs" / "images"
OUTPUT = PROJECT_ROOT / "dist" / "PersonaWare-English-2.0-Screenshots.zip"
ARCHIVE_ROOT = "PersonaWare-English-2.0-Screenshots"
TIMESTAMP = (2026, 8, 2, 0, 0, 0)

CAPTIONS = {
    "launcher.png": "English PersonaWare launcher with Power Management",
    "photo-manager-menu.png": "Photo Manager add, remove, assign, and restore menu",
    "address-book-warning.png": "Translated Address Book warning",
    "address-book-help.png": "English Address Book help",
    "email-help.png": "English E-Mail help and setup guidance",
    "fax-help.png": "English FAX help",
    "dos-command.png": "English DOS command environment",
    "personaware-english-cf-installer.png": "Backup-first CF installer",
    "personaware-english-cf-restore.png": "CF recovery workflow",
}


def archive_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(f"{ARCHIVE_ROOT}/{name}", TIMESTAMP)
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def build_archive(output: Path = OUTPUT) -> Path:
    missing = [name for name in CAPTIONS if not (SOURCE / name).is_file()]
    if missing:
        raise FileNotFoundError(f"missing screenshots: {', '.join(missing)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    index = [
        "PERSONAWARE ENGLISH 2.0 SCREENSHOTS",
        "====================================",
        "",
    ]
    index.extend(f"{name}: {caption}" for name, caption in CAPTIONS.items())
    index.extend(
        (
            "",
            "The images document the translated launcher, application help,",
            "Photo Manager, DOS environment, and safe CF install and recovery.",
            "",
        )
    )
    with zipfile.ZipFile(output, "w", strict_timestamps=True) as archive:
        archive.writestr(archive_info("INDEX.txt"), "\r\n".join(index).encode("ascii"))
        for name in CAPTIONS:
            archive.writestr(archive_info(name), (SOURCE / name).read_bytes())
    print(f"Built {output} with {len(CAPTIONS)} screenshots")
    return output


if __name__ == "__main__":
    build_archive()

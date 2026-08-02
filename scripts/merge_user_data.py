#!/usr/bin/env python3
"""Merge PersonaWare user databases into a fresh English release image."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

if __package__:
    from .build_enhanced_image import PARTITION_OFFSET, add_notebook_help
else:
    from build_enhanced_image import PARTITION_OFFSET, add_notebook_help


DATABASE_EXTENSIONS = {".ADD", ".NTD", ".SCD", ".TDD"}


def run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"{' '.join(command)} failed: {detail}")


def image_spec(image: Path) -> str:
    return f"{image.resolve()}@@{PARTITION_OFFSET}"


def validate_image(image: Path) -> None:
    if not image.is_file():
        raise FileNotFoundError(image)
    with image.open("rb") as stream:
        stream.seek(510)
        if stream.read(2) != b"\x55\xaa":
            raise ValueError(f"{image} is missing its MBR signature")
    run(["mdir", "-i", image_spec(image), "::/PW/DATA/DEFAULT.NTD"])


def merge_user_data(
    existing: Path,
    release: Path,
    output: Path,
    *,
    fresh_defaults: bool = False,
) -> list[str]:
    existing = existing.resolve()
    release = release.resolve()
    output = output.resolve()
    validate_image(existing)
    validate_image(release)
    if output in {existing, release}:
        raise ValueError("output must be different from both input images")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(release, output)

    copied: list[str] = []
    with tempfile.TemporaryDirectory(prefix="pwenglish-userdata-") as temporary:
        root = Path(temporary)
        run(
            [
                "mcopy",
                "-s",
                "-i",
                image_spec(existing),
                "::/PW/DATA",
                str(root),
            ]
        )
        data_root = root / "DATA"
        for source in sorted(path for path in data_root.iterdir() if path.is_file()):
            if source.suffix.upper() not in DATABASE_EXTENSIONS:
                continue
            if fresh_defaults and source.name.upper().startswith("DEFAULT."):
                continue
            if source.name.upper() == "DEFAULT.NTD":
                source.write_bytes(add_notebook_help(source.read_bytes()))
            run(
                [
                    "mcopy",
                    "-o",
                    "-i",
                    image_spec(output),
                    str(source),
                    f"::/PW/DATA/{source.name.upper()}",
                ]
            )
            copied.append(source.name.upper())
    validate_image(output)
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("existing", type=Path, help="current PersonaWare image")
    parser.add_argument("release", type=Path, help="fresh English release image")
    parser.add_argument("output", type=Path, help="new host-specific image")
    parser.add_argument(
        "--fresh-defaults",
        action="store_true",
        help="replace untouched stock DEFAULT databases with the English release",
    )
    args = parser.parse_args()
    copied = merge_user_data(
        args.existing,
        args.release,
        args.output,
        fresh_defaults=args.fresh_defaults,
    )
    print(f"Built {args.output} with {len(copied)} preserved database files")
    for name in copied:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

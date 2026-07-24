#!/usr/bin/env python3
"""Switch the PC110 boot environment to English and patch DOS/V status text."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil


def replace_once(data: bytes, source: bytes, target: bytes, name: str) -> bytes:
    count = data.count(source)
    if count != 1:
        raise ValueError(f"{name}: expected one occurrence, found {count}: {source!r}")
    return data.replace(source, target)


def patch_config(source: Path, destination: Path) -> None:
    data = source.read_bytes()
    data = replace_once(
        data,
        b"COUNTRY=081,932,\\DOS\\COUNTRY.SYS\r\n",
        b"COUNTRY=001,437,\\DOS\\COUNTRY.SYS\r\n",
        source.name,
    )
    data = replace_once(
        data,
        b"DEVICEHIGH=C:\\DOS\\$IAS.SYS\r\n",
        b"REM DEVICEHIGH=C:\\DOS\\$IAS.SYS\r\n",
        source.name,
    )
    install_start = b"INSTALL=C:\\DOS\\IBMMKKV.EXE "
    lines = data.splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if line.startswith(install_start)]
    if len(matches) != 1:
        raise ValueError(
            f"{source.name}: expected one IBMMKKV install line, found {len(matches)}"
        )
    index = matches[0]
    lines[index] = b"REM " + lines[index]
    destination.write_bytes(b"".join(lines))


def patch_autoexec(source: Path, destination: Path) -> None:
    data = replace_once(
        source.read_bytes(),
        b"LH C:\\DOS\\KEYB.COM JP,932,C:\\DOS\\KEYBOARD.SYS\r\n",
        b"LH C:\\DOS\\KEYB.COM JP\r\n",
        source.name,
    )
    destination.write_bytes(data)


def fixed_patch(
    data: bytearray,
    offset: int,
    source: str,
    target: str,
    *,
    encoding: str = "cp932",
) -> None:
    original = source.encode(encoding)
    replacement = target.encode("ascii")
    if len(replacement) > len(original):
        raise ValueError(
            f"replacement at 0x{offset:x} is {len(replacement)} bytes "
            f"for a {len(original)}-byte slot"
        )
    if data[offset : offset + len(original)] != original:
        found = bytes(data[offset : offset + len(original)])
        raise ValueError(
            f"unexpected bytes at 0x{offset:x}: {found!r}; expected {original!r}"
        )
    data[offset : offset + len(original)] = replacement + b"\0" * (
        len(original) - len(replacement)
    )


def patch_ias_sub(source: Path, destination: Path) -> None:
    data = bytearray(source.read_bytes())

    fixed_patch(
        data,
        0x982C,
        "$IAS.SYS にオプション /G=1 を指定して下さい。[改行]",
        "Specify /G=1 for $IAS.SYS. [Enter]",
    )
    fixed_patch(
        data,
        0x9860,
        "「語句」が入力されていません。[改行]",
        "No word was entered. [Enter]",
    )
    fixed_patch(
        data,
        0x9886,
        "「読み」が入力されていません。[改行]",
        "No reading was entered. [Enter]",
    )

    for offset in (0x98C2, 0x98F8):
        fixed_patch(data, offset, "英数", "A/N ")
    for offset in (0x98C7, 0x98FD):
        fixed_patch(data, offset, "カナ", "KANA")
    for offset in (0x98CC, 0x9902):
        fixed_patch(data, offset, "かな", "kana")
    for offset in (0x98D1, 0x9907):
        fixed_patch(data, offset, "全角", "Full")
    for offset in (0x98D6, 0x990C):
        fixed_patch(data, offset, "半角", "Half")

    for offset in (0x992E, 0x9964):
        fixed_patch(data, offset, "英", "A ")
    for offset in (0x9933, 0x9969):
        fixed_patch(data, offset, "カ", "K ")
    for offset in (0x9938, 0x996E):
        fixed_patch(data, offset, "か", "k ")
    for offset in (0x993D, 0x9973):
        fixed_patch(data, offset, "全", "F ")
    for offset in (0x9942, 0x9978):
        fixed_patch(data, offset, "半", "H ")
    for offset in (0x9947, 0x997D):
        fixed_patch(data, offset, "Ｒ", "R ")

    fixed_patch(
        data,
        0x99A8,
        "かな漢字制御　　設定　単語登録",
        "IME Control   Setup   Add Word",
    )
    fixed_patch(data, 0x99C7, "　単語登録　", " Add Word  ")
    fixed_patch(data, 0x99E1, "語句　", "Word  ")
    fixed_patch(data, 0x99E8, "読み　", "Read  ")

    destination.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()

    if args.output_root.exists():
        shutil.rmtree(args.output_root)
    (args.output_root / "DOS").mkdir(parents=True)

    patch_config(
        args.source_root / "CONFIG.SYS",
        args.output_root / "CONFIG.SYS",
    )
    patch_autoexec(
        args.source_root / "AUTOEXEC.BAT",
        args.output_root / "AUTOEXEC.BAT",
    )
    patch_ias_sub(
        args.source_root / "DOS" / "$IAS.SUB",
        args.output_root / "DOS" / "$IAS.SUB",
    )
    print(f"English boot files written to {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

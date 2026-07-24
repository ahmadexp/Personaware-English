#!/usr/bin/env python3
"""Find likely user-facing Japanese strings in PersonaWare files.

PersonaWare stores text as CP932 (Shift-JIS) inside DOS executables and data
files.  This scanner walks printable CP932 runs instead of relying on the host
`strings` command, which cannot decode the double-byte text.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Iterator


JAPANESE_RE = re.compile(
    r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]"
)
KANA_RE = re.compile(r"[\u3040-\u30ff]")
HIRAGANA_RE = re.compile(r"[\u3040-\u309f]")
COMMON_JAPANESE_RE = re.compile(
    r"(です|ます|ません|ください|します|しました|できます|"
    r"ファイル|データ|メモリー|パスワード|プリンター|"
    r"ヘルプ|エラー|モード|設定|入力|選択|削除|保存|保管|"
    r"読み込み|書き込み|終了|表示|実行|登録|移動|"
    r"よろしい|ありません|できません)"
)


@dataclass(frozen=True)
class Finding:
    path: str
    offset: int
    byte_length: int
    japanese_characters: int
    text: str


def cp932_unit_length(data: bytes, offset: int) -> int:
    """Return the length of a printable CP932 unit, or zero if invalid."""
    first = data[offset]
    if first in (0x09, 0x0A, 0x0D) or 0x20 <= first <= 0x7E:
        return 1
    if 0xA1 <= first <= 0xDF:
        return 1
    if not (0x81 <= first <= 0x9F or 0xE0 <= first <= 0xFC):
        return 0
    if offset + 1 >= len(data):
        return 0
    second = data[offset + 1]
    if not (0x40 <= second <= 0x7E or 0x80 <= second <= 0xFC):
        return 0
    try:
        data[offset : offset + 2].decode("cp932")
    except UnicodeDecodeError:
        return 0
    return 2


def iter_findings(
    path: Path,
    display_path: str,
    minimum_japanese: int,
    natural_only: bool,
) -> Iterator[Finding]:
    data = path.read_bytes()
    offset = 0
    while offset < len(data):
        unit_length = cp932_unit_length(data, offset)
        if not unit_length:
            offset += 1
            continue

        start = offset
        while offset < len(data):
            unit_length = cp932_unit_length(data, offset)
            if not unit_length:
                break
            offset += unit_length

        raw = data[start:offset]
        try:
            text = raw.decode("cp932")
        except UnicodeDecodeError:
            continue
        text = text.strip()
        japanese_count = len(JAPANESE_RE.findall(text))
        if japanese_count < minimum_japanese:
            continue
        if natural_only and not looks_like_natural_japanese(text):
            continue
        yield Finding(
            path=display_path,
            offset=start,
            byte_length=len(raw),
            japanese_characters=japanese_count,
            text=text,
        )


def looks_like_natural_japanese(text: str) -> bool:
    """Reject CP932-looking machine code while keeping UI labels/messages."""
    japanese_count = len(JAPANESE_RE.findall(text))
    kana_count = len(KANA_RE.findall(text))
    hiragana_count = len(HIRAGANA_RE.findall(text))
    if COMMON_JAPANESE_RE.search(text):
        return True
    if any(mark in text for mark in "。、。「」【】（）"):
        return True
    if hiragana_count >= 2 or kana_count >= 3:
        return True

    # Keep short, clean labels made primarily from Japanese characters.
    allowed_ascii = set(
        " \t\r\n0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz%:;,.!?()[]{}+-_/\\~*'\""
    )
    suspicious = sum(
        1
        for char in text
        if not JAPANESE_RE.match(char)
        and char not in allowed_ascii
        and not (0xFF01 <= ord(char) <= 0xFF60)
    )
    return (
        japanese_count >= 2
        and len(text) <= 32
        and suspicious == 0
        and japanese_count / max(len(text), 1) >= 0.45
    )


def input_files(inputs: list[Path]) -> Iterator[tuple[Path, str]]:
    for input_path in inputs:
        if input_path.is_file():
            yield input_path, input_path.as_posix()
            continue
        for path in sorted(p for p in input_path.rglob("*") if p.is_file()):
            yield path, path.relative_to(input_path).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument(
        "--minimum-japanese",
        type=int,
        default=2,
        help="minimum Japanese characters per printable run (default: 2)",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--natural-only",
        action="store_true",
        help="suppress CP932-looking machine code and binary data",
    )
    args = parser.parse_args()

    findings = [
        finding
        for path, display_path in input_files(args.paths)
        for finding in iter_findings(
            path,
            display_path,
            args.minimum_japanese,
            args.natural_only,
        )
    ]

    if args.json:
        print(
            json.dumps(
                [asdict(finding) for finding in findings],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for finding in findings:
            escaped = finding.text.replace("\r", "\\r").replace("\n", "\\n")
            print(
                f"{finding.path}:0x{finding.offset:08x}:"
                f"{finding.byte_length}: {escaped}"
            )
        print(f"\n{len(findings)} likely Japanese strings")

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

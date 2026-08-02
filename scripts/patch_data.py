#!/usr/bin/env python3
"""Translate PersonaWare's bundled data, help, and launcher metadata."""

from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path
import re
import shutil


LAUNCHER_TITLES = [
    (0x00F, 10, "Schedule"),
    (0x088, 9, "ToDo List"),
    (0x0FF, 10, "Notebook"),
    (0x176, 11, "Address"),
    (0x1ED, 16, "E-Mail"),
    (0x262, 19, "FAX"),
    (0x2E0, 7, "Phone"),
    (0x359, 12, "IR Connect"),
    (0x3D2, 9, "Clock"),
    (0x449, 12, "Calculator"),
    (0x4BD, 16, "Editor"),
    (0x538, 13, "Draw Memo"),
    (0x5AB, 14, "Game"),
    (0x627, 12, "Personal"),
    (0x69A, 20, "DOS Command"),
    (0x718, 13, "Power MGT"),
]

ERA_NAMES = [
    (0x006, "Meiji"),
    (0x016, "Taisho"),
    (0x026, "Showa"),
    (0x036, "Heisei"),
]

HOLIDAY_NAMES = [
    "New Year's Day",
    "Coming-of-Age Day",
    "Foundation Day",
    "Greenery Day",
    "Constitution Day",
    "Public Holiday",
    "Children's Day",
    "Marine Day",
    "Respect Aged Day",
    "Sports Day",
    "Culture Day",
    "Labor Thanks Day",
    "Emperor Bday",
]


def load_name_translations(path: Path) -> dict[str, str]:
    translations: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            source, target = line.split("\t", 1)
        except ValueError as error:
            raise ValueError(f"{path}:{number}: expected a tab-separated pair") from error
        target.encode("ascii")
        translations[source] = target
    return translations


def translate_city_file(
    source: Path, destination: Path, translations: dict[str, str]
) -> None:
    output: list[bytes] = []
    pattern = re.compile(
        r"(.*?)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(\d+)"
    )
    for raw_line in source.read_bytes().split(b"\r\n"):
        if not raw_line:
            continue
        match = pattern.fullmatch(raw_line.decode("cp932"))
        if not match:
            raise ValueError(f"Cannot parse city row: {raw_line!r}")
        source_name, longitude, latitude, zone, flags = match.groups()
        english = translations[source_name.strip()]
        if len(english) > 28:
            english = english[:28].rstrip()
        row = (
            english.ljust(28)
            + f"{longitude:>7}"
            + f"{latitude:>7}"
            + f"{zone:>7}"
            + f"{flags:>7}"
        )
        encoded = row.encode("ascii")
        if len(encoded) != 56:
            raise AssertionError(f"City row is {len(encoded)} bytes: {row!r}")
        output.append(encoded)
    destination.write_bytes(b"\r\n".join(output) + b"\r\n")


def translate_dial_directory(
    source: Path, destination: Path, translations: dict[str, str]
) -> None:
    output: list[bytes] = []
    for raw_line in source.read_bytes().split(b"\r\n"):
        if not raw_line or raw_line == b"\x1a":
            continue
        if len(raw_line) != 54:
            raise ValueError(f"Unexpected dial-directory row: {raw_line!r}")
        field = raw_line[13:31].decode("cp932").strip()
        parts = re.split(r"\s+(?=\d+\s+bps|ROAD2)", field, maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"Cannot parse dial-directory label: {field!r}")
        source_name, connection = parts
        label = f"{translations[source_name.strip()]} {connection.strip()}"
        label = label[:18].rstrip().ljust(18)
        output.append(raw_line[:13] + label.encode("ascii") + raw_line[31:])
    destination.write_bytes(b"\r\n".join(output) + b"\r\n\x1a")


def patch_launcher_file(path: Path) -> None:
    data = bytearray(path.read_bytes())
    for offset, length, title in LAUNCHER_TITLES:
        replacement = title.encode("ascii")
        if len(replacement) > length:
            raise ValueError(f"Launcher title is too long: {title}")
        data[offset : offset + length] = replacement + b" " * (
            length - len(replacement)
        )
    path.write_bytes(data)


def patch_common_data(path: Path) -> None:
    data = bytearray(path.read_bytes())
    for offset, name in ERA_NAMES:
        encoded = name.encode("ascii")
        data[offset : offset + 9] = encoded + b"\0" * (9 - len(encoded))
    for index, name in enumerate(HOLIDAY_NAMES):
        encoded = name.encode("ascii")
        if len(encoded) > 18:
            raise ValueError(f"Holiday name is too long: {name}")
        offset = 0x08A + index * 0x16
        data[offset : offset + 18] = encoded + b"\0" * (18 - len(encoded))
    # The original file includes a second display copy of Emperor's Birthday.
    data[0x1A9 : 0x1A9 + 18] = b"Emperor Bday" + b"\0" * 6
    path.write_bytes(data)


def csv_bytes(rows: list[list[str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\r\n")
    writer.writerows(rows)
    return stream.getvalue().encode("ascii") + b"\x1a"


def replace_address_book(path: Path) -> None:
    header = [
        "yomi",
        "name",
        "category",
        "home tel number",
        "home fax number",
        "home zip",
        "home address",
        "birth day",
        "office",
        "station",
        "post",
        "office tel number",
        "office fax number",
        "office zip",
        "office address",
        "email",
        "photo file name",
        "voice file name",
        "note1",
        "note2",
        "note3",
    ]
    personaware = [
        "personaware",
        "Personaware",
        "Software",
        "",
        "",
        "",
        "",
        "",
        "IBM",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "Original sample contacts were removed because their 1995 phone numbers "
        "and service details are obsolete.",
        "",
        "",
    ]
    path.write_bytes(csv_bytes([header, personaware]))


def replace_notebook_readme(path: Path) -> None:
    header = ["date", "time", "subject", "category", "note"]
    notes = [
        [
            "",
            "",
            "01. General",
            "README",
            "BACKUPS\r\n\r\n"
            "Back up every file in the DATA subdirectory. If you save data in "
            "another directory, back up that directory too. Restore by copying "
            "the files back to the same locations while PersonaWare is closed.",
        ],
        [
            "",
            "",
            "02. Launcher",
            "README",
            "DOS programs must be on PATH and may use EXE, COM, or BAT. "
            "PersonaWare applications use EXM files in METDIR. Icons belong in "
            "SYSTEM and use the OS/2-compatible 40x40 ICO format.",
        ],
        [
            "",
            "",
            "03. Alarms",
            "README",
            "Schedule and World Clock can set alarms. An alarm may be delayed "
            "while a DOS program, communications task, long operation, or modal "
            "dialog is active. Return to the launcher to resume alarm handling.",
        ],
        [
            "",
            "",
            "04. Schedule",
            "README",
            "A schedule data file holds up to 500 records. Use F11 and File to "
            "switch data files. Subjects beginning with * are treated as dated "
            "holidays. Printing can delay alarms until printing finishes.",
        ],
        [
            "",
            "",
            "05. ToDo List",
            "README",
            "A ToDo data file holds up to 500 records. Use F11 and File to "
            "switch data files. Printing can delay alarms until printing ends.",
        ],
        [
            "",
            "",
            "06. Notebook",
            "README",
            "A Notebook data file holds up to 200 records. Use F11 and File to "
            "switch data files. Printing can delay alarms until printing ends.",
        ],
        [
            "",
            "",
            "07. Address Book",
            "README",
            "An address data file holds up to 500 records. Address images should "
            "be 150x150, 16-color BMP files stored in DATA. Select an image from "
            "the address edit screen with F11.",
        ],
        [
            "",
            "",
            "08. Email and Fax",
            "README",
            "The bundled dial-up service numbers are historical and may no "
            "longer work. Review METPML.INI and the dial directory before using "
            "a modem. Never assume an old access number is still valid.",
        ],
        [
            "",
            "",
            "09. Editor",
            "README",
            "Press F1 in Editor for the complete English key reference. Save "
            "important work before launching another DOS program or powering "
            "off the machine.",
        ],
        [
            "",
            "",
            "10. Safe Shutdown",
            "README",
            "Use PersonaWare's normal exit and power-off command. Changes may "
            "be lost after Ctrl+Alt+Del, a forced power-off, or an emulator "
            "reset.",
        ],
        [
            "",
            "",
            "11. Launcher Photos",
            "README",
            "Open Photo Manager from the launcher. Use F8 or Page Down if an "
            "item is beyond the first page. Import a prepared 190x250, "
            "16-color BMP, then assign it to one of the five launcher picture "
            "slots. Remove deletes only a gallery copy. Restore recovers the "
            "original pictures.",
        ],
    ]
    path.write_bytes(csv_bytes([header, *notes]))


def replace_editor_help(path: Path) -> None:
    text = """<< FUNCTION KEYS >>

F1  (Alt+H)  Show this help.
F2  (Alt+O)  Open a file.
F3  (Alt+Q)  Discard the file being edited.
F4  (Alt+C)  Save and close the current file.
F5  (Ctrl+S) Find or replace text.
F7  (PgUp)   Previous page.
F8  (PgDn)   Next page.
F9           Increase font size.
F10 (Ctrl+N) Edit the next file.
F11          Display settings.
F12 (Alt+X)  Save all changed files and exit.

<< OTHER KEYS >>

Alt+S              Save and continue editing.
Shift+F9           Decrease font size.
Ctrl+F9            Change font.
Ctrl+L             Toggle line numbers.
Alt+F10 (Ctrl+P)   Edit the previous file.
Shift+Arrow        Select text.
Ctrl+Ins (Ctrl+C)  Copy text.
Shift+Ins (Ctrl+V) Paste text.
Shift+Del (Ctrl+X) Cut text.
Ctrl+F (Alt+F8)    Repeat search toward the end.
Ctrl+B (Alt+F7)    Repeat search toward the beginning.
"""
    path.write_bytes(text.replace("\n", "\r\n").encode("ascii") + b"\x1a")


def replace_game_scores(path: Path) -> None:
    text = """ [HiScore]
 PLAYER1   1000  95/03/03    1    2
 PLAYER2    300  95/10/20   10    3
 PLAYER3    119  99/03/27    0   34
 PLAYER3    105  99/03/27    0   46
 PLAYER4    100  94/01/21   20    4
 [Option]
      Beep =        off
     Magic =          3
 [Bitmap]
       Pai =     U_PAI.BMP
       Pet =     U_DOG.BMP
"""
    path.write_bytes(text.replace("\n", "\r\n").encode("ascii"))


def translate_ini_files(directory: Path) -> None:
    pml = directory / "METPML.INI"
    text = pml.read_bytes().decode("cp932")
    replacements = {
        "東京\u3000  2400 bps": "Tokyo    2400 bps",
        "トーン": "Tone",
        "なし": "None",
        "はい": "Yes",
        "いいえ": "No",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    pml.write_bytes(text.encode("ascii"))

    schedule = directory / "METSCHD.INI"
    text = schedule.read_bytes().rstrip(b"\x1a").decode("ascii")
    if "Rokuyo=" not in text:
        text = text.rstrip("\r\n") + "\r\nRokuyo=OFF\r\n"
    schedule.write_bytes(text.encode("ascii") + b"\x1a")


def translate_schedule(path: Path) -> None:
    text = path.read_bytes().decode("cp932")
    text = text.replace("*春分の日(振替)", "*Vernal Equinox (Observed)")
    text = text.replace("*春分の日", "*Vernal Equinox")
    text = text.replace("*秋分の日", "*Autumnal Equinox")
    path.write_bytes(text.encode("ascii"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_data", type=Path)
    parser.add_argument("source_system", type=Path)
    parser.add_argument("name_translations", type=Path)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()

    if args.output_root.exists():
        shutil.rmtree(args.output_root)
    data_dir = args.output_root / "DATA"
    system_dir = args.output_root / "SYSTEM"
    shutil.copytree(args.source_data, data_dir)
    system_dir.mkdir(parents=True)
    shutil.copy2(args.source_system / "MDLAUNCH.MAL", system_dir)

    names = load_name_translations(args.name_translations)
    translate_city_file(
        args.source_data / "CITY1S.TXT", data_dir / "CITY1S.TXT", names
    )
    translate_dial_directory(
        args.source_data / "METPML.ADR", data_dir / "METPML.ADR", names
    )
    patch_common_data(data_dir / "COMMON.DAT")
    patch_launcher_file(data_dir / "MDLAUNCH.CTL")
    patch_launcher_file(system_dir / "MDLAUNCH.MAL")
    replace_address_book(data_dir / "DEFAULT.ADD")
    replace_notebook_readme(data_dir / "DEFAULT.NTD")
    translate_schedule(data_dir / "DEFAULT.SCD")
    replace_editor_help(data_dir / "METEDIT.HLP")
    replace_game_scores(data_dir / "METGAME.INI")
    translate_ini_files(data_dir)
    print(f"Translated data written to {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

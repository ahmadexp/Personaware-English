#!/usr/bin/env python3
"""Apply the complete English PersonaWare binary translation.

The historical English modules translated the main screens but left a number
of dialogs, warnings, and F1 help panels in Japanese.  The executables are
patched after PKLITE decompression.  Every replacement stays inside the
original byte slot so code and relocation offsets remain unchanged.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import shutil


@dataclass(frozen=True)
class Patch:
    offset: int
    length: int
    text: str
    pad: bytes = b"\0"
    validate_japanese: bool = True


def p(
    offset: int,
    length: int,
    text: str,
    pad: bytes = b"\0",
    validate_japanese: bool = True,
) -> Patch:
    return Patch(offset, length, text, pad, validate_japanese)


COMMON_HOLIDAYS = [
    ("NY", 4),
    ("Adult", 8),
    ("Found. Day", 12),
    ("Green Day", 10),
    ("Const Day", 10),
    ("Holiday", 10),
    ("Kids Day", 10),
    ("Sea", 6),
    ("Aged Day", 8),
    ("Sports", 8),
    ("Culture", 8),
    ("Labor Day", 12),
    ("Empr Bday", 10),
]


PATCHES: dict[str, list[Patch]] = {
    "METADDR.EXE": [
        p(0x1D420, 89, "Save Data?\nFile write failed. Choose Cancel to discard unsaved changes."),
        p(0x1D4C8, 4, "Name"),
        p(0x1D4CD, 4, "Name"),
        p(0x1D4D2, 8, "Jump:"),
        p(0x1D4DB, 13, "Address Jump"),
        p(
            0x1D4E9,
            337,
            "Type a name reading in the list to jump to a matching record.\n"
            "A reading must be saved with the name. Romanized input is accepted. "
            "Use '-' for a long vowel and 'xtsu' for small tsu.",
        ),
        p(0x1D66B, 71, "Paste\nClipboard data is too large to paste."),
        p(0x1D6C1, 11, "Addr List"),
        p(
            0x1D6CD,
            505,
            "PgUp/PgDn : Previous/next page\n"
            "Del        : Delete record\n"
            "Enter      : Edit record\n"
            "Arrow keys : Move cursor\n"
            "Ctrl+Left/Right: Resize a column\n"
            "Shift+Left/Right: Resize a column\n"
            "Esc        : Exit Address Book\n"
            "Ctrl+S     : Toggle secret mode\n\n"
            "COPY AND PASTE\n"
            "Select a record, press Ctrl+Ins or Ctrl+C to copy, then press "
            "Shift+Ins or Ctrl+V to paste it.",
        ),
        p(0x1D922, 36, "Print Category?\nPrint category \"%s\"?"),
        p(0x1D947, 69, "Printing all records in this category. Press Esc to stop."),
        p(0x1D98D, 4, "Prnt"),
        p(0x1D992, 63, "Printer Error\nPrinter is not ready. Retry or cancel."),
        p(0x1D9D2, 50, "Secret Mode?\nTurn secret mode off?"),
        p(0x1DA05, 40, "Incorrect Password.\nWrong password."),
        p(0x1DA2E, 32, "Turn secret mode on?"),
        p(0x1DA7C, 93, "Name", b" "),
        p(0x1DADA, 93, "Name", b" "),
        p(0x1DF98, 6, "(none)"),
        p(0x1DFA0, 10, "City"),
        p(0x1E27E, 34, "Enter a name and reading."),
        p(0x1E345, 6, "(none)"),
        p(0x1E35B, 11, "Edit Addr"),
        p(
            0x1E367,
            334,
            "Tab/Shift+Tab : Next/previous field\n"
            "Shift+Arrows  : Select text\n"
            "Ctrl+Ins      : Copy text\n"
            "Shift+Ins     : Paste text\n"
            "Shift+Del     : Cut text\n"
            "Space         : Toggle check box\n"
            "Esc           : Exit without saving",
        ),
        p(
            0x1E507,
            93,
            "Address List\nUse Up/Down and Enter to select, or type a reading.",
        ),
        p(0x1E619, 70, "Address List\nUse Up/Down and Enter to select."),
        p(0x1E735, 28, "No phone number is saved."),
        p(0x1E760, 27, "No fax number is saved."),
        p(0x1E77C, 33, "No email address is saved."),
        p(0x1E7A0, 4, "Mei"),
        p(0x1E7A5, 4, "Tai"),
        p(0x1E7AA, 4, "Sho"),
        p(0x1E7AF, 4, "Hei"),
        p(0x1E7B4, 2, "Y"),
        p(0x1E7B9, 2, "M"),
        p(0x1E7BE, 2, "D"),
        p(0x1E7CD, 4, "Mei"),
        p(0x1E7D7, 4, "Tai"),
        p(0x1E7E1, 4, "Sho"),
        p(0x1E7EB, 4, "Hei"),
        p(0x1E7FC, 4, "Mei"),
        p(0x1E80C, 4, "Tai"),
        p(0x1E81C, 4, "Sho"),
        p(0x1E82C, 4, "Hei"),
        p(0x1E885, 6, "Y/M/D"),
        p(0x1E88C, 4, "Next"),
        *[
            p(offset, length, text)
            for offset, (text, length) in zip(
                range(0x1E8BC, 0x1E9C5, 0x16), COMMON_HOLIDAYS
            )
        ],
        p(0x1EB7F, 2, "Y"),
        p(0x1EB84, 2, "M"),
        p(0x1EB89, 3, "D"),
        p(0x1EC6B, 70, "Record limit reached; some records were not added."),
        p(0x1F99E, 43, "ZIP Address\nSelect an address below."),
        p(0x1FFC0, 17, "Choose Address"),
        p(
            0x1FFD2,
            238,
            "Postal-code lookup is unavailable in this English build because "
            "the bundled lookup database contains Japanese-only addresses. "
            "Enter an address manually.",
        ),
        p(0x200CC, 10, "(no class)"),
        p(0x200D7, 17, "Choose Category"),
        p(
            0x200E9,
            138,
            "Filter the list by the Category entered while editing. Select a "
            "category with the arrow keys or mouse.",
        ),
        p(0x20174, 31, "Choose Address Image"),
        p(0x20194, 56, "Choose the image shown in Personal mode."),
        p(0x201CD, 11, "Addr Setup"),
        p(
            0x201D9,
            266,
            "File (F)       : Open, save, or delete data files\n"
            "Secret (S)     : Toggle secret mode\n"
            "Print (P)      : Print records\n"
            "Print Setup (R): Select a printer\n"
            "List Setup (O) : Choose columns shown in the list",
        ),
        p(0x202E4, 18, "Address Columns"),
        p(
            0x202F7,
            537,
            "Choose the fields shown in the list.\n"
            "Add (A): Select an item under Hidden and choose Add.\n"
            "Delete (D): Select an item under Shown and choose Delete.\n"
            "Move Up/Down (U/L): Select a shown item and move it to set the "
            "display order.",
        ),
        p(0x20530, 27, "Start Communications"),
        p(
            0x2054C,
            223,
            "Start Telephone or Fax using the selected address. Select a phone "
            "or fax number and press Enter (OK); the chosen application opens "
            "with that number entered.",
        ),
        p(0x2062C, 24, "(SJW3) No number found."),
        p(0x20646, 2, "Y"),
        p(0x2064B, 2, "M"),
        p(0x20650, 2, "D"),
        p(0x20656, 4, "Read"),
        p(0x2065B, 4, "Cat"),
        p(0x20660, 4, "Tel"),
        p(0x2066F, 4, "Addr"),
        p(0x20674, 6, "Birth"),
        p(0x2067B, 4, "Work"),
        p(0x20680, 4, "Dept"),
        p(0x20685, 4, "Role"),
        p(0x2068A, 4, "Tel"),
        p(0x20699, 4, "Addr"),
        p(0x206A4, 4, "Note"),
        p(0x2084C, 10, "Printer"),
        p(0x20857, 67, "Select your printer type, then choose OK."),
        p(0x2089B, 30, "The printer reported an error."),
        p(0x20AC0, 18, "Open File"),
        p(0x20AD3, 8, "Open"),
        p(0x20AE2, 60, "Could not save the current data."),
        p(0x20B1F, 36, "Create a new data file."),
        p(0x20B44, 34, "Invalid file format."),
        p(0x20B67, 34, "Could not read the file."),
        p(0x20B8A, 38, "Too many records. Maximum: %d."),
        p(0x20BB1, 4, "Save"),
        p(0x20BB6, 4, "Save"),
        p(0x20BBD, 22, "Incorrect password."),
        p(0x20BD6, 42, "File exists. Overwrite it?"),
        p(0x20C01, 34, "Could not write the file."),
        p(0x20C24, 56, "Use the file just saved as the active data file?"),
        p(0x20C5D, 4, "Del"),
        p(0x20C62, 4, "Del"),
        p(0x20C6E, 12, "File Tasks"),
        p(
            0x20C7B,
            691,
            "OPEN: The current data is saved automatically, then the selected "
            "data file is opened.\n\n"
            "SAVE: Save the current data under a chosen name. Choose Yes to "
            "make the saved file active. Choose No when making only a backup.\n\n"
            "DELETE: Delete the selected data file. All records in that file "
            "will be permanently removed.",
        ),
        p(0x2101E, 12, "Find Text"),
        p(
            0x2102B,
            467,
            "Enter text and choose Find. Enable Match Case to distinguish "
            "uppercase and lowercase.\n\n"
            "In the list, the search starts at the current record and moves to "
            "the next matching record.\n\n"
            "In a note editor, the search starts at the cursor (or at the start "
            "of the note when another field is selected).",
        ),
        p(0x211FF, 30, "Enter text to find."),
        p(0x21248, 16, "Enter Password"),
        p(0x21259, 4, "OK"),
        p(0x2125E, 4, "Esc"),
        p(0x21263, 11, "Password:"),
        p(0x2132E, 16, "Enter Password"),
        p(
            0x2133F,
            161,
            "Enter the password and choose OK. Secret mode remains locked "
            "unless it matches the password set in Personal Information.",
        ),
        p(0x21466, 44, "This program requires DOS PM."),
        p(0x21493, 48, "The loaded DOS PM version is incompatible."),
    ],
    "METPML.EXE": [
        p(0x1FEFA, 15, "=== Inbox No."),
        p(0x1FF68, 8, "From"),
        p(0x1FF72, 5, "Subj:"),
        p(0x21DB0, 16, "Session began at"),
        p(0x21DCA, 47, "- End of notice. Press Enter. -"),
        p(0x21E02, 26, "Enter for top menu >"),
        p(0x21E26, 24, "- More (. to stop) -"),
        p(0x21E48, 6, "No. >"),
        p(0x21E64, 8, "Number >"),
        p(0x21E76, 6, "No. >"),
        p(0x21EA4, 15, "=== Inbox No."),
        p(0x21EBC, 24, "=== Email / Fax"),
        p(0x21EDE, 36, "... No matching mail."),
        p(0x21F0C, 24, " is binary data."),
        p(0x21F2E, 38, "... No matching contact."),
        p(0x21F5E, 6, "Subj:"),
        p(0x21F7C, 37, "*** Add signature? (1 Yes  2 No):"),
        p(0x21FAA, 34, "1 Run  2 Settings  3 Cancel >"),
        p(0x21FD6, 16, "*** Protocol"),
        p(0x21FFC, 16, "Receive file:"),
        p(0x22016, 35, "*** Start XMODEM receive now"),
        p(0x22042, 35, "*** Start ZMODEM receive now"),
        p(0x2206E, 38, "1 Delete all  2 Review  3 Cancel:"),
        p(0x2209E, 34, "*** Confirm (1 Yes  2 No):"),
    ],
    "METSCHD.EXE": [
        p(0x316A0, 89, "Save Data?\nFile write failed. Choose Cancel to discard unsaved changes."),
        p(
            0x31729,
            133,
            "Repeating Event\nDelete only this occurrence? Choose No to delete "
            "the entire series.",
        ),
        p(
            0x317AF,
            88,
            "Deleting this event will end its repeat series. Continue?",
        ),
        p(0x31857, 75, "Too many events.\nNot all events for this day can be shown."),
        p(0x318CF, 48, "Delete all events for this day?"),
        p(
            0x31924,
            1040,
            "DAY VIEW\n"
            "Left/Right: Previous/next date\n"
            "Up/Down: Move by time interval\n"
            "Tab: Move to an untimed event\n"
            "PgUp/PgDn: Previous/next page\n"
            "W/M/H/L: Week, month, six-month, or list view\n"
            "Ctrl+S: Toggle secret mode\n"
            "Enter: Edit event   Del: Delete event   Esc: Exit\n\n"
            "COPY, CUT, AND PASTE\n"
            "Ctrl+Ins or Ctrl+C copies the selected event. Shift+Del or Ctrl+X "
            "cuts it. Shift+Ins or Ctrl+V pastes at the selected date/time. "
            "Copy works in day, week, and list views; paste is unavailable in "
            "list view.",
        ),
        p(
            0x31D43,
            1036,
            "WEEK VIEW\n"
            "Left/Right: Previous/next date\n"
            "Up/Down: Move by time interval\n"
            "Tab: Move to an untimed event\n"
            "PgUp/PgDn: Previous/next page\n"
            "P/N: Previous/next week\n"
            "D/M/H/L: Day, month, six-month, or list view\n"
            "Ctrl+S: Toggle secret mode\n"
            "Enter: Edit event   Del: Delete event   Esc: Exit\n\n"
            "COPY, CUT, AND PASTE\n"
            "Ctrl+Ins or Ctrl+C copies. Shift+Del or Ctrl+X cuts. Shift+Ins or "
            "Ctrl+V pastes. Copy works in day, week, and list views; paste is "
            "unavailable in list view.",
        ),
        p(
            0x3215F,
            1039,
            "MONTH VIEW\n"
            "Arrow keys: Move to another date\n"
            "PgUp/PgDn: Previous/next month\n"
            "D/W/H/L: Day, week, six-month, or list view\n"
            "Ctrl+S: Toggle secret mode\n"
            "Enter: Open day view   Del: Delete event   Esc: Exit\n\n"
            "To hide Rokuyo calendar labels, add Rokuyo=OFF to METSCHD.INI.\n\n"
            "COPY, CUT, AND PASTE\n"
            "Ctrl+Ins or Ctrl+C copies. Shift+Del or Ctrl+X cuts. Shift+Ins or "
            "Ctrl+V pastes. Copy works in day, week, and list views; paste is "
            "unavailable in list view.",
        ),
        p(
            0x32582,
            839,
            "SIX-MONTH VIEW\n"
            "Arrow keys: Move to another date\n"
            "PgUp/P: Previous six months\n"
            "PgDn/N: Next six months\n"
            "D/W/M/L: Day, week, month, or list view\n"
            "Ctrl+S: Toggle secret mode\n"
            "Enter: Open day view   Esc: Exit\n\n"
            "COPY, CUT, AND PASTE\n"
            "Ctrl+Ins or Ctrl+C copies. Shift+Del or Ctrl+X cuts. Shift+Ins or "
            "Ctrl+V pastes. Copy works in day, week, and list views; paste is "
            "unavailable in list view.",
        ),
        p(0x32C8E, 9, "*Vernal"),
        p(0x32C98, 9, "*Autumn"),
        p(0x32CA2, 9, "*Vernal"),
        p(0x32CAC, 9, "*Autumn"),
        p(0x33F92, 4, "Prev"),
        p(0x33F98, 4, "Next"),
        p(0x3450D, 4, "Prev"),
        p(0x34513, 4, "Next"),
        p(
            0x34D69,
            175,
            "Set the day/week time interval to 60, 30, or 15 minutes. In day "
            "view, you can also show only times that contain events.",
        ),
        p(
            0x34E28,
            395,
            "File (F)       : Open, save, or delete data files\n"
            "Secret (S)     : Toggle secret mode\n"
            "Print (P)      : Print day or month view\n"
            "Print Setup (R): Select a printer\n"
            "Time Unit (T)  : Change day/week time interval\n"
            "Holiday (H)    : Add or delete holidays\n"
            "Era (Y)        : Add, change, or delete eras",
        ),
        p(
            0x34FD6,
            84,
            "Add, change, or delete eras. Select an era from the list.",
        ),
        p(
            0x3504C,
            293,
            "Enter an era name, one-letter abbreviation, and Gregorian date "
            "range. Date ranges cannot overlap. The abbreviation may be used "
            "instead of the era name in date fields.",
        ),
        p(0x35172, 24, "Enter an era name."),
        p(0x3518B, 30, "Enter a valid date range."),
        p(0x351AA, 34, "Enter one ASCII letter."),
        p(0x351CD, 22, "Era ranges overlap."),
        p(
            0x351FA,
            293,
            "Enter an era name, one-letter abbreviation, and Gregorian date "
            "range. Date ranges cannot overlap. The abbreviation may be used "
            "instead of the era name in date fields.",
        ),
        p(0x35320, 24, "Enter an era name."),
        p(0x35339, 30, "Enter a valid date range."),
        p(0x35358, 34, "Enter one ASCII letter."),
        p(0x3537B, 22, "Era ranges overlap."),
        p(
            0x356FE,
            163,
            "Add or delete holidays.\n"
            "Add (A): Enter a date and name, then choose Add.\n"
            "Delete (E): Select a holiday, then choose Delete.",
        ),
        p(0x357A2, 24, "No more can be added."),
        p(0x3581E, 2, "Y"),
        p(0x35823, 2, "M"),
        p(0x35828, 2, "D"),
        p(0x3583B, 4, "Year"),
        p(0x35842, 2, "M"),
        p(0x35848, 4, "Year"),
        *[
            p(offset, length, text)
            for offset, (text, length) in zip(
                range(0x3585A, 0x35963, 0x16), COMMON_HOLIDAYS
            )
        ],
        p(0x35B74, 30, "Not enough free disk space."),
        p(0x35B96, 70, "Record limit reached; some records were not added."),
        p(0x35BFC, 5, " plan", validate_japanese=False),
        p(0x35C05, 4, "Prnt"),
        p(0x35C49, 4, "Prnt"),
        p(0x35C8B, 4, "Prnt"),
        p(0x35F80, 4, "none"),
        p(0x3605B, 46, "Edit\nNot enough memory to add the event."),
        p(0x3609E, 34, "Save changes?"),
        p(0x36202, 34, "Discard changes?"),
        p(0x362B0, 2, "S"),
        p(0x362B3, 2, "M"),
        p(0x362B6, 2, "T"),
        p(0x362B9, 2, "W"),
        p(0x362BC, 2, "T"),
        p(0x362BF, 2, "F"),
        p(0x362C2, 2, "S"),
        p(0x3635D, 36, "Turn secret mode off?"),
        p(0x36382, 20, "Incorrect password."),
        p(0x36397, 32, "Turn secret mode on?"),
        p(
            0x363FC,
            359,
            "Choose a date in the two-month calendar on the right, or type a "
            "date in the field above. PgUp/PgDn scrolls by two months.\n"
            "Press Enter to close the calendar and go to the selected date. "
            "Press Esc to return to the original date.",
        ),
        p(0x365CA, 4, "Mei"),
        p(0x365DA, 4, "Tai"),
        p(0x365EA, 4, "Sho"),
        p(0x365FA, 4, "Hei"),
        p(0x3665E, 4, "none"),
        p(0x36663, 4, "none"),
        p(0x36668, 4, "Next"),
        p(
            0x367C0,
            870,
            "1995-3-21,0:0:0,1995-3-21,0:0:0,*Spring Eq,,1,5,0,0,1995-3-21,1995-3-21,\n"
            "1995-9-23,0:0:0,1995-9-23,0:0:0,*Fall Eq,,1,5,0,0,1995-9-23,1995-9-23,\n"
            "1996-3-20,0:0:0,1996-3-20,0:0:0,*Spring Eq,,1,5,0,0,1996-3-20,1996-3-20,\n"
            "1996-9-23,0:0:0,1996-9-23,0:0:0,*Fall Eq,,1,5,0,0,1996-9-23,1996-9-23,\n"
            "1997-3-20,0:0:0,1997-3-20,0:0:0,*Spring Eq,,1,5,0,0,1997-3-20,1997-3-20,\n"
            "1997-9-23,0:0:0,1997-9-23,0:0:0,*Fall Eq,,1,5,0,0,1997-9-23,1997-9-23,\n"
            "1998-3-21,0:0:0,1998-3-21,0:0:0,*Spring Eq,,1,5,0,0,1998-3-21,1998-3-21,\n"
            "1998-9-23,0:0:0,1998-9-23,0:0:0,*Fall Eq,,1,5,0,0,1998-9-23,1998-9-23,\n"
            "1999-3-22,0:0:0,1999-3-22,0:0:0,*Spring Eq Obs,,1,5,0,0,1999-3-22,1999-3-22,\n"
            "1999-9-23,0:0:0,1999-9-23,0:0:0,*Fall Eq,,1,5,0,0,1999-9-23,1999-9-23,\n"
            "2000-3-20,0:0:0,2000-3-20,0:0:0,*Spring Eq,,1,5,0,0,2000-3-20,2000-3-20,\n"
            "2000-9-23,0:0:0,2000-9-23,0:0:0,*Fall Eq,,1,5,0,0,2000-9-23,2000-9-23,",
        ),
        p(0x36B3E, 67, "File(1) Could not save the current data."),
        p(0x36B82, 43, "File(2) Create a new data file."),
        p(0x36BAE, 41, "File(3) Invalid file format."),
        p(0x36BD8, 41, "File(4) Could not read the file."),
        p(0x36C02, 45, "File(5) Too many records. Maximum: %d."),
        p(0x36C41, 29, "File(6) Incorrect password."),
        p(0x36C61, 49, "File(7) File exists. Overwrite it?"),
        p(0x36C93, 41, "File(8) Could not write the file."),
        p(0x36CBD, 63, "File(9) Use the saved file as the active data file?"),
        p(0x37047, 30, "The printer reported an error."),
        p(0x37246, 4, "AM+"),
        p(0x3724B, 4, "AM+"),
        p(0x37250, 4, "Even"),
        p(0x37255, 4, "Even"),
        p(0x3725A, 4, "PM+"),
        p(0x3725F, 4, "PM+"),
        p(0x37264, 4, "Bad"),
        p(0x37269, 4, "Bad"),
        p(0x3726E, 4, "Good"),
        p(0x37273, 4, "Good"),
        p(0x37278, 4, "Noon"),
        p(0x3727D, 4, "Noon"),
        p(0x3729A, 16, "Enter Password"),
        p(0x372AB, 4, "OK"),
        p(0x372B0, 4, "Esc"),
        p(0x372B5, 11, "Password:"),
        p(0x37380, 16, "Enter Password"),
        p(
            0x37391,
            161,
            "Enter the password and choose OK. Secret mode remains locked "
            "unless it matches the password set in Personal Information.",
        ),
        p(0x374B8, 44, "This program requires DOS PM."),
        p(0x374E5, 48, "The loaded DOS PM version is incompatible."),
    ],
    "METTODO.EXE": [
        p(0x19D18, 6, "(none)"),
        p(0x19FCA, 4, "Mei"),
        p(0x19FDA, 4, "Tai"),
        p(0x19FEA, 4, "Sho"),
        p(0x19FFA, 4, "Hei"),
        p(0x1A05E, 4, "Next"),
        p(0x1A185, 67, "File(1) Could not save the current data."),
        p(0x1A1C9, 43, "File(2) Create a new data file."),
        p(0x1A1F5, 41, "File(3) Invalid file format."),
        p(0x1A21F, 41, "File(4) Could not read the file."),
        p(0x1A249, 45, "File(5) Too many records. Maximum: %d."),
        p(0x1A288, 29, "File(6) Incorrect password."),
        p(0x1A2A8, 49, "File(7) File exists. Overwrite it?"),
        p(0x1A2DA, 41, "File(8) Could not write the file."),
        p(0x1A304, 63, "File(9) Use the saved file as the active data file?"),
        p(0x1A4C8, 36, "[1] 2099-12-31 23:59:59 1\r\n[No name]"),
        *[
            p(offset, length, text)
            for offset, (text, length) in zip(
                range(0x1A4F8, 0x1A601, 0x16), COMMON_HOLIDAYS
            )
        ],
        p(0x1A818, 2, "Y"),
        p(0x1A81D, 2, "M"),
        p(0x1A822, 3, "D"),
        p(0x1AB42, 6, "(none)"),
        p(0x1ABFB, 2, "Y"),
        p(0x1AC02, 2, "M"),
        p(0x1AC09, 2, "D"),
        p(0x1AC0D, 6, "(none)"),
        p(0x1B435, 30, "The printer reported an error."),
        p(0x1B46A, 16, "Enter Password"),
        p(0x1B47B, 4, "OK"),
        p(0x1B480, 4, "Esc"),
        p(0x1B485, 11, "Password:"),
        p(0x1B550, 16, "Enter Password"),
        p(
            0x1B561,
            161,
            "Enter the password and choose OK. Secret mode remains locked "
            "unless it matches the password set in Personal Information.",
        ),
        p(0x1B688, 44, "This program requires DOS PM."),
        p(0x1B6B5, 48, "The loaded DOS PM version is incompatible."),
    ],
    "METVIEW.EXE": [
        p(0xAFF5, 43, "Could not open Fax file %s."),
        p(0xB22F, 26, "RTC found."),
        p(0xB291, 19, "Finished."),
        p(0xB345, 44, "Not StrFax format version 1.0."),
        p(0xB372, 28, "Could not allocate XMS: %d"),
    ],
    "DOSPM.EXE": [
        p(0x77BE, 6, "Help"),
        p(0x77C5, 20, "No help available."),
        p(0x77DA, 18, "Open File"),
        p(0x77EE, 14, "File name (~I)"),
        p(0x77FE, 12, "Files (~F)"),
        p(0x780C, 18, "Directory (~D)"),
        p(0x7820, 4, "OK"),
        p(0x7825, 4, "Esc"),
        p(0x782A, 6, "Help"),
        p(0x7837, 14, "Next drv (~N)"),
        p(0x7A6E, 30, "Help file not found."),
        p(0x7A8D, 22, "Not enough memory."),
        p(0x7AA4, 16, "Save As Help"),
        p(0x7AB5, 16, "Open Help"),
        p(0x7ACF, 48, "The selected drive is unavailable."),
        p(0x7B05, 34, "Invalid file name."),
        p(0x7B28, 18, "Path not found."),
        p(0x7BFA, 4, "OK"),
        p(0x7BFF, 4, "OK"),
        p(0x7C04, 4, "Esc"),
        p(0x7C09, 4, "Esc"),
        p(0x7C0E, 8, "Abort~A"),
        p(0x7C17, 8, "Abort~A"),
        p(0x7C20, 10, "Retry (~R)"),
        p(0x7C2B, 10, "Retry (~R)"),
        p(0x7C36, 8, "Ignore~I"),
        p(0x7C3F, 8, "Ignore~I"),
        p(0x7C48, 8, "Yes (~Y)"),
        p(0x7C51, 8, "Yes (~Y)"),
        p(0x7C5A, 10, "No (~N)"),
        p(0x7C65, 10, "No (~N)"),
        p(0x7C70, 6, "Help"),
        p(0x7C77, 6, "Help"),
        p(0x7C8C, 10, "Zoom (~Z)"),
        p(0x7C97, 12, "Prev page~P"),
        p(0x7CA4, 12, "Next page~N"),
        p(0x7CB1, 4, "Esc"),
        p(0xED8F, 50, "Cannot write: drive X: is write-protected."),
        p(0xEDC2, 25, "Device X: was not found."),
        p(0xEDDC, 31, "Device X: is not ready."),
        p(0xEDFC, 50, "Requested sector not found on drive X:."),
        p(0xEE2F, 50, "Cannot seek the requested area on drive X:."),
        p(0xEE62, 48, "Insert a diskette in drive X:."),
        p(0xF163, 57, "Return the error to the program", b" "),
        p(0xF19D, 57, "Retry the command or operation", b" "),
        p(0xF1D7, 57, "Display help", b" "),
        p(0xF734, 70, "Display the error message again", b" "),
        p(0xF855, 70, "The destination diskette is write-protected.", b" "),
        p(0xF92A, 70, "Check that the correct diskette is inserted and that it", b" "),
        p(0xF971, 70, "is writable, then run the command again.", b" "),
        p(0xFA46, 70, "An unrecognized device was specified.", b" "),
        p(0xFB1B, 70, "Try again using the correct device name.", b" "),
        p(0xFBF0, 70, "One of the following occurred:", b" "),
        p(0xFC7E, 70, "o The device is empty or not ready.", b" "),
        p(0xFCC5, 70, "o The COMx device driver is not installed, or", b" "),
        p(0xFD0C, 70, "  COMx is disabled and cannot be used.", b" "),
        p(0xFDE1, 70, "Do one of the following, then retry the command:", b" "),
        p(0xFE6F, 70, "o Insert a diskette, close the drive door,", b" "),
        p(0xFEB6, 70, "  or wait until the drive is available.", b" "),
        p(0xFEFD, 70, "o Check that COMx hardware is installed.", b" "),
        p(0xFFD2, 70, "The disk may be damaged, unformatted,", b" "),
        p(0x10019, 70, "or incompatible with this operating system.", b" "),
        p(0x10060, 70, "", b" "),
        p(0x10135, 70, "Do one of the following, then run the command again:", b" "),
        p(0x101C3, 70, "o Check that the diskette is inserted correctly.", b" "),
        p(0x1020A, 70, "o Check the disk or diskette for damage.", b" "),
        p(0x10251, 70, "o Format the disk or diskette for DOS.", b" "),
        p(0x10298, 70, "o Format a damaged optical disk using /L.", b" "),
        p(0x102DF, 70, "o Format the diskette at the correct density", b" "),
        p(0x10326, 70, "  for the disk drive.", b" "),
        p(0x103FB, 70, "No help is available for this message.", b" "),
    ],
}


DOSPM_CLI_REPLACEMENTS = {
    "DOS PM はすでにロードされています。\r\n$": "DOS PM is already loaded.\r\n$",
    "DOS PM はロードされていません。\r\n$": "DOS PM is not loaded.\r\n$",
    "DOS PM をメモリーにロードします。\r\n\r\n": "Loading DOS PM into memory.\r\n\r\n",
    "  /R   DOS PM をメモリーから削除します。\r\n$": (
        "  /R   Remove DOS PM from memory.\r\n$"
    ),
    "  /V   DOS PM のバージョンを取得します。\r\n": (
        "  /V   Display the DOS PM version.\r\n"
    ),
    "パラメーターが正しくありません。\r\n$": "Invalid parameter.\r\n$",
    "必要な環境変数が定義されていません。\r\n$": (
        "Required variable missing.\r\n$"
    ),
    "DOS PM の初期化に失敗しました。\r\n": "DOS PM initialization failed.\r\n",
}


def apply_patch(data: bytearray, patch: Patch, name: str) -> None:
    replacement = patch.text.encode("ascii")
    if len(replacement) > patch.length:
        raise ValueError(
            f"{name}: replacement at 0x{patch.offset:x} is "
            f"{len(replacement)} bytes for a {patch.length}-byte slot"
        )
    end = patch.offset + patch.length
    if end > len(data):
        raise ValueError(f"{name}: patch at 0x{patch.offset:x} exceeds file size")
    original = bytes(data[patch.offset:end])
    try:
        original_text = original.decode("cp932")
    except UnicodeDecodeError:
        original_text = ""
    if patch.validate_japanese and not any(
        "\u3040" <= char <= "\u30ff" or "\u3400" <= char <= "\u9fff"
        for char in original_text
    ):
        raise ValueError(
            f"{name}: expected Japanese text at 0x{patch.offset:x}, "
            f"found {original[:20]!r}"
        )
    data[patch.offset:end] = replacement + patch.pad * (
        patch.length - len(replacement)
    )


def replace_cli_strings(data: bytearray) -> None:
    for source, target in DOSPM_CLI_REPLACEMENTS.items():
        source_bytes = source.encode("cp932")
        target_bytes = target.encode("ascii")
        if len(target_bytes) > len(source_bytes):
            raise ValueError(f"DOSPM CLI replacement is too long: {target!r}")
        count = data.count(source_bytes)
        if count != 1:
            raise ValueError(
                f"DOSPM CLI source should occur once, found {count}: {source!r}"
            )
        data[:] = data.replace(
            source_bytes,
            target_bytes + b" " * (len(source_bytes) - len(target_bytes)),
        )


def patch_one(source: Path, destination: Path) -> None:
    name = source.name.upper()
    data = bytearray(source.read_bytes())
    for patch in PATCHES.get(name, []):
        apply_patch(data, patch, name)
    if name == "DOSPM.EXE":
        replace_cli_strings(data)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    print(f"{name}: {len(PATCHES.get(name, []))} fixed-slot translations")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("legacy_dir", type=Path)
    parser.add_argument("dospm", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    if args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True)

    for source in sorted(args.legacy_dir.glob("*.EXE")):
        patch_one(source, args.output_dir / source.name)
    patch_one(args.dospm, args.output_dir / "DOSPM.EXE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

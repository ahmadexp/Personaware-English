from __future__ import annotations

import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

from scripts.audit_japanese import iter_findings
from scripts.build_cf_installer import STATE_MARKER_CRC, build_cf_installer

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CFInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="pwenglish-test-cf-")
        root = Path(cls.temporary.name)
        cls.output = root / "output"
        cls.archive = root / "installer.zip"
        cls.package = build_cf_installer(
            PROJECT_ROOT / "dist" / "Personaware-English-2.0.img",
            cls.output,
            cls.archive,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_package_has_install_and_recovery_tools(self) -> None:
        for name in (
            "INSTALL.BAT",
            "RESTORE.BAT",
            "FORCERST.BAT",
            "RESTDATA.BAT",
            "STARTPW.BAT",
            "PWCOPY.COM",
            "PWIMAGE.COM",
            "STATE.OK",
            "README.TXT",
            "NOTICE.TXT",
            "SHA256.TXT",
        ):
            self.assertTrue((self.package / name).is_file(), name)
        for name in (
            "PAYLOAD/PWPHOTO.COM",
            "PAYLOAD/PWPHOTO.TXT",
            "PAYLOAD/PW/PHOTO/STOCK1.BMP",
            "PAYLOAD/PW/PHOTO/STOCK5.BMP",
        ):
            self.assertTrue((self.package / name).is_file(), name)

    def test_payload_boots_normally_as_c_and_cf_launcher_targets_d(self) -> None:
        pw_batch = (self.package / "PAYLOAD" / "PW" / "PW.BAT").read_bytes()
        self.assertIn(b"set METDIR=C:\\PW", pw_batch)
        self.assertFalse((self.package / "PAYLOAD" / "MODERN").exists())

        start = (self.package / "STARTPW.BAT").read_bytes()
        self.assertIn(b"SET METDIR=D:\\PW", start)
        self.assertIn(b"SET PATH=%METDIR%;%PATH%", start)
        self.assertNotIn(b"PWMODERN", start)

    def test_active_english_boot_files_are_packaged(self) -> None:
        payload = self.package / "PAYLOAD"
        autoexec = (payload / "AUTOEXEC.BAT").read_bytes()
        config = (payload / "CONFIG.SYS").read_bytes()
        ias = (payload / "DOS" / "$IAS.SUB").read_bytes()
        self.assertIn(b"PATH C:\\;C:\\DOS", autoexec)
        self.assertNotIn(b"PWMODERN", autoexec)
        self.assertIn(b"COUNTRY=001,437", config)
        self.assertIn(b"DEVICEHIGH=C:\\DOS\\$FONT.SYS", config)
        self.assertNotIn(b"REM DEVICEHIGH=C:\\DOS\\$FONT.SYS", config)
        self.assertIn(b"REM DEVICEHIGH=C:\\DOS\\$DISP.SYS", config)
        self.assertIn(b"REM DEVICEHIGH=C:\\DOS\\$IAS.SYS", config)
        self.assertIn(b"REM INSTALL=C:\\DOS\\IBMMKKV.EXE", config)
        self.assertIn(b"Specify /G=1 for $IAS.SYS. [Enter]", ias)
        self.assertIn(b"IME Control   Setup   Add Word", ias)

    def test_install_script_is_backup_first_and_non_overwriting(self) -> None:
        script = (self.package / "INSTALL.BAT").read_text(encoding="ascii")
        image_position = script.index("PWIMAGE.COM /B")
        install_position = script.index("CALL C:\\PWMINST\\FILES.BAT")
        self.assertLess(image_position, install_position)
        self.assertIn("IF EXIST C:\\PWMINST\\D-ORIG.IMG GOTO VERIFYBACKUP", script)
        self.assertIn("C:\\PWMINST\\PWIMAGE.COM /V", script)
        self.assertIn("IF NOT EXIST D:\\PW\\PW.BAT GOTO NOTARGET", script)
        self.assertIn(
            f"PWCOPY.COM /C C:\\PWMINST\\INSTALL.OK {STATE_MARKER_CRC:08X}",
            script,
        )
        self.assertIn(
            f"PWCOPY.COM /C C:\\PWMINST\\COPY.OK {STATE_MARKER_CRC:08X}",
            script,
        )
        self.assertNotIn("ECHO INSTALL COMPLETE>", script)
        self.assertNotIn("ECHO USER DATA COMPLETE>", script)
        file_script = (self.package / "FILES.BAT").read_text(encoding="ascii")
        self.assertIn(
            f"PWCOPY.COM C:\\PWMINST\\STATE.OK C:\\PWMINST\\COPY.OK "
            f"{STATE_MARKER_CRC:08X}",
            file_script,
        )

    def test_restore_still_works_after_an_interrupted_file_copy(self) -> None:
        script = (self.package / "RESTORE.BAT").read_text(encoding="ascii")
        self.assertNotIn("IF NOT EXIST D:\\PW\\PW.BAT", script)
        self.assertIn("C:\\PWMINST\\PWIMAGE.COM /R", script)
        self.assertIn("C:\n", script)
        self.assertIn(":WAIT\nGOTO WAIT", script)
        force = (self.package / "FORCERST.BAT").read_text(encoding="ascii")
        self.assertIn("C:\\PWMINST\\PWIMAGE.COM /F", force)
        self.assertIn(
            b"Type FORCE and press Enter to continue:",
            (self.package / "PWIMAGE.COM").read_bytes(),
        )

    def test_backup_is_read_back_before_installation(self) -> None:
        source = (PROJECT_ROOT / "installer" / "dos" / "pwimage.asm").read_text(
            encoding="ascii"
        )
        sequence = (
            "call close_manifest\n"
            "    jc backup_failed\n"
            "    mov dx, backup_verify_text\n"
            "    call print_string\n"
            "    call load_manifest\n"
            "    jc backup_failed\n"
            "    mov ax, [current_sectors]\n"
            "    cmp ax, [manifest_buffer + MAN_SECTORS]\n"
            "    jne backup_failed\n"
            "    mov eax, [current_serial]\n"
            "    cmp eax, [manifest_buffer + MAN_SERIAL]\n"
            "    jne backup_failed\n"
            "    call verify_backup_file\n"
            "    jc backup_failed"
        )
        self.assertIn(sequence, source)
        self.assertIn(
            b"Reading the saved image back from the CF for verification.",
            (self.package / "PWIMAGE.COM").read_bytes(),
        )

    def test_restore_writes_the_volume_boot_sector_last(self) -> None:
        source = (PROJECT_ROOT / "installer" / "dos" / "pwimage.asm").read_text(
            encoding="ascii"
        )
        data_loop = source.index(".restore_loop:")
        boot_write = source.index(".restore_boot_sector:")
        verification = source.index("call verify_target_crc")
        self.assertLess(data_loop, boot_write)
        self.assertLess(boot_write, verification)
        self.assertIn("xor ax, ax\n    call write_target_sector", source[boot_write:])

    def test_payload_crc_is_checked_and_boot_files_are_installed_last(self) -> None:
        script = (self.package / "FILES.BAT").read_text(encoding="ascii")
        copy_lines = [
            line
            for line in script.splitlines()
            if line.startswith("C:\\PWMINST\\PWCOPY.COM C:\\PWMINST\\PAYLOAD")
        ]
        self.assertTrue(copy_lines)
        for line in copy_lines:
            parts = line.split()
            self.assertEqual(4, len(parts), line)
            expected = parts[3]
            self.assertEqual(8, len(expected), line)
            source = parts[1].removeprefix("C:\\PWMINST\\").replace("\\", "/")
            actual = zlib.crc32((self.package / source).read_bytes()) & 0xFFFFFFFF
            self.assertEqual(actual, int(expected, 16), line)
            self.assertLessEqual(len(line), 127, line)
        autoexec = next(
            i for i, line in enumerate(copy_lines) if "AUTOEXEC.BAT" in line
        )
        config = next(i for i, line in enumerate(copy_lines) if "CONFIG.SYS" in line)
        self.assertGreater(autoexec, len(copy_lines) - 3)
        self.assertGreater(config, len(copy_lines) - 3)

    def test_backup_reserves_documented_cf_working_space(self) -> None:
        source = (PROJECT_ROOT / "installer" / "dos" / "pwimage.asm").read_text(
            encoding="ascii"
        )
        self.assertIn("add ebx, 3145728", source)
        self.assertIn("cmp byte [sector_buffer + 38], 0x29", source)
        force_dispatch = source.index(
            "cmp byte [force_mode], 1", source.index("restore_mode:")
        )
        target_inspection = source.index("call inspect_target", force_dispatch)
        self.assertLess(force_dispatch, target_inspection)

    def test_builder_refuses_dangerous_output_directories(self) -> None:
        with self.assertRaises(ValueError):
            build_cf_installer(
                PROJECT_ROOT / "dist" / "Personaware-English-2.0.img",
                Path.home(),
                self.archive,
            )
        unrecognized = Path(self.temporary.name) / "unrecognized"
        unrecognized.mkdir()
        (unrecognized / "keep.txt").write_text("keep\n", encoding="ascii")
        with self.assertRaises(ValueError):
            build_cf_installer(
                PROJECT_ROOT / "dist" / "Personaware-English-2.0.img",
                unrecognized,
                self.archive,
            )
        self.assertEqual(
            "keep\n", (unrecognized / "keep.txt").read_text(encoding="ascii")
        )

    def test_english_structured_data_has_no_natural_japanese(self) -> None:
        data_root = self.package / "PAYLOAD" / "PW" / "DATA"
        findings = [
            finding
            for path in sorted(data_root.iterdir())
            if path.is_file()
            for finding in iter_findings(path, path.name, 2, True)
        ]
        self.assertEqual([], findings)

    def test_japanese_postal_database_is_not_packaged(self) -> None:
        self.assertFalse(
            (self.package / "PAYLOAD" / "PW" / "SYSTEM" / "IBMZIPC2.ZB").exists()
        )
        file_script = (self.package / "FILES.BAT").read_text(encoding="ascii")
        self.assertIn("PWCOPY.COM /D D:\\PW\\SYSTEM\\IBMZIPC2.ZB", file_script)

    def test_zip_has_one_dos_friendly_top_level_folder(self) -> None:
        with zipfile.ZipFile(self.archive) as archive:
            names = archive.namelist()
        self.assertTrue(names)
        self.assertTrue(all(name.startswith("PWMINST/") for name in names))
        self.assertIn("PWMINST/INSTALL.BAT", names)
        self.assertIn("PWMINST/RESTORE.BAT", names)
        self.assertIn("PWMINST/FORCERST.BAT", names)


if __name__ == "__main__":
    unittest.main()
